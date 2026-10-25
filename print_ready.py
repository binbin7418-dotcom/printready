#!/usr/bin/env python3
"""
PrintReady — KDP-style print interior PDF pre-check, repair & re-check.

Checks (per page, deterministic, via PyMuPDF):
  - Page size consistency across the book
  - Content too close to the trim edge (inside the 0.25in minimum margin)
  - Fonts: not embedded (standard Base-14 fonts reported separately —
    most printers accept them; anything else unembedded is an error)
  - Image effective DPI (placed size vs pixel size; under 200 flagged,
    print target is 300)
  - Fully blank pages; rotated pages; CropBox/MediaBox mismatches

Repairs (the ones with exactly one correct form):
  - Bake page rotation into the content (rotation reset to 0)
  - Unify CropBox to MediaBox where they disagree

Everything else is reported per page with the fix the author must make —
resolution and margins cannot be invented after the fact.
Local only.
"""
import os
import sys

import pymupdf

BASE14 = {"courier", "helvetica", "times", "symbol", "zapfdingbats",
          "courier-bold", "courier-oblique", "courier-boldoblique",
          "helvetica-bold", "helvetica-oblique", "helvetica-boldoblique",
          "times-roman", "times-bold", "times-italic", "times-bolditalic"}
MIN_MARGIN_PT = 0.25 * 72
MIN_DPI = 200


def is_base14(name):
    n = (name or "").lower().replace(" ", "").replace("-", "")
    return any(b.replace("-", "") in n or n in b.replace("-", "") for b in BASE14)


def audit(path):
    doc = pymupdf.open(path)
    issues, fixes = [], []

    def issue(sev, page, msg):
        issues.append({"sev": sev, "page": page, "msg": msg})

    sizes = {}
    for pno, page in enumerate(doc, 1):
        r = page.rect
        sizes.setdefault((round(r.width), round(r.height)), []).append(pno)
    if len(sizes) > 1:
        detail = "; ".join(f"{w}×{h}pt on pages {ps[:4]}{'…' if len(ps) > 4 else ''}"
                           for (w, h), ps in sizes.items())
        issue("ERROR", 0, f"page sizes are not consistent ({detail}) — a print interior must use one trim size")

    for pno, page in enumerate(doc, 1):
        if page.rotation != 0:
            fixes.append({"page": pno, "msg": f"page {pno}: rotation of {page.rotation}° baked into the content and reset to 0"})
        if page.cropbox != page.mediabox:
            fixes.append({"page": pno, "msg": f"page {pno}: CropBox differed from MediaBox — unified (some printers read one, some the other)"})

        blocks = page.get_text("blocks")
        imgs = page.get_images(full=True)
        if not blocks and not imgs:
            issue("WARN", pno, f"page {pno} is completely blank — intentional section breaks are fine, accidental blanks get flagged in review")
        r = page.rect
        for b in blocks:
            x0, y0, x1, y1 = b[:4]
            if x0 < MIN_MARGIN_PT or y0 < MIN_MARGIN_PT or \
               x1 > r.width - MIN_MARGIN_PT or y1 > r.height - MIN_MARGIN_PT:
                issue("ERROR", pno, f"page {pno}: text runs inside the 0.25in minimum margin — KDP-style review will bounce this page")
                break
        seen_xref = set()
        for img in imgs:
            xref = img[0]
            if xref in seen_xref:
                continue
            seen_xref.add(xref)
            pix = pymupdf.Pixmap(doc, xref)
            rects = page.get_image_rects(xref)
            for rc in rects:
                w_in = rc.width / 72.0
                if w_in > 0:
                    dpi = pix.width / w_in
                    if dpi < MIN_DPI:
                        issue("ERROR", pno, f"page {pno}: an image prints at about {dpi:.0f} DPI (placed {rc.width/72:.1f}in wide from a {pix.width}px file) — print target is 300 DPI, minimum ~200; replace it with a higher-resolution original")
            pix = None

    font_refs = set()
    for pno, page in enumerate(doc, 1):
        for f in page.get_fonts(full=True):
            font_refs.add((f[0], f[3]))
    for xref, name in sorted(font_refs):
        try:
            buf = doc.extract_font(xref)
            embedded = bool(buf and buf[1])
        except Exception:
            embedded = False
        if not embedded:
            if is_base14(name):
                issue("WARN", 0, f"font '{name}' is a standard Base-14 font and not embedded — most print services accept these, but embedding everything is the safer export setting")
            else:
                issue("ERROR", 0, f"font '{name}' is NOT embedded — the print service may substitute it and reflow your book; re-export with 'embed all fonts'")
    doc.close()
    return issues, fixes


def apply_fixes(path, out_path, fixes):
    doc = pymupdf.open(path)
    for fx in fixes:
        page = doc[fx["page"] - 1]
        if "rotation" in fx["msg"]:
            page.remove_rotation()
        if "CropBox" in fx["msg"]:
            page.set_cropbox(page.mediabox)
    doc.save(out_path, garbage=3, deflate=True)
    doc.close()


def run_printready(src_path, outdir):
    os.makedirs(outdir, exist_ok=True)
    base = os.path.splitext(os.path.basename(src_path))[0]
    before, fixable = audit(src_path)
    fixed_path = os.path.join(outdir, base + "_printready.pdf")
    if fixable:
        apply_fixes(src_path, fixed_path, fixable)
    else:
        import shutil
        shutil.copyfile(src_path, fixed_path)
    after, _ = audit(fixed_path)

    def cnt(lst, sev):
        return sum(1 for i in lst if i["sev"] == sev)

    errs = cnt(after, "ERROR")
    verdict = "PASS with warnings" if errs == 0 else "NOT READY"
    lines = ["# PrintReady — print pre-check, repair & re-check report", "",
             f"Source file: {os.path.basename(src_path)}", "",
             "## Summary",
             f"- Problems found: {len(before)} ({cnt(before,'ERROR')} errors, {cnt(before,'WARN')} warnings)",
             f"- Auto-fixed: {len(fixable)}",
             f"- Remaining after re-check: {len(after)} ({errs} errors, {cnt(after,'WARN')} warnings)", "",
             "## What was fixed automatically"]
    lines += [f"- {f['msg']}" for f in fixable] or ["- nothing structural to fix"]
    lines += ["", "## What still needs your input (cannot be auto-fixed)"]
    lines += [f"- [{i['sev']}] {i['msg']}" for i in after] or \
             ["- nothing — the file passes every check in this audit set"]
    lines += ["", "## Re-check verdict",
              f"- {verdict}: {errs} blocking errors remain. Scope note: checks follow the common "
              "KDP-style interior rules (consistent trim size, 0.25in minimum margins, embedded fonts, "
              "~300 DPI images). Your printer's house rules win where they differ."]
    report_path = os.path.join(outdir, "fix_report.md")
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return {"found": len(before), "fixed": len(fixable), "remaining": len(after),
            "errors_remaining": errs, "verdict": verdict,
            "fixed_path": fixed_path, "report_path": report_path}


def main(argv):
    if len(argv) != 3:
        print("usage: print_ready.py <interior.pdf> <outdir>")
        return 2
    s = run_printready(argv[1], argv[2])
    print(f"found={s['found']} fixed={s['fixed']} remaining={s['remaining']} errors_remaining={s['errors_remaining']} verdict={s['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
