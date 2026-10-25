# PrintReady — Print Interior PDF Pre-Check, Repair & Re-Check

Print-on-demand review bounces book interiors for mechanical reasons:
margins, fonts, image resolution, inconsistent page sizes. PrintReady
checks a print PDF the way a KDP-style review does, repairs the structural
defects, then **re-checks the repaired file** page by page. 100% local.

## What it checks
- One consistent trim size across the whole book
- Text inside the 0.25in minimum margin (per page)
- Fonts not embedded (standard Base-14 reported separately — usually accepted)
- Image effective DPI at placed size (300 target, under 200 flagged)
- Blank pages, rotated pages, CropBox/MediaBox mismatches

## What it fixes on its own
- Page rotation baked into the content (rotation reset to 0)
- CropBox unified to MediaBox where they disagree
The re-check then reports the repaired file's true state — if baking a
rotation leaves a page at a different size, you see it flagged, not hidden.

## What it reports, but never silently changes
Low-resolution images, margin violations, unembedded non-standard fonts —
fixing those means new source assets or layout changes, so you get the
exact page and measurement instead.

## Verified behaviour
On a seeded 5-page 6×9in interior (a margin violator, a 33-DPI image,
a 90°-rotated page, a CropBox mismatch, a blank page): the 2 structural
defects were repaired and the re-check confirmed the remaining 3 blocking
errors per page with 0 invented fixes.

## Run from source
```
python print_ready.py interior.pdf output_folder
```
Writes `<name>_printready.pdf` and `fix_report.md`. Requires PyMuPDF.
The Windows package bundles everything.
