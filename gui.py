#!/usr/bin/env python3
"""PrintReady desktop shell (tkinter). Pick a print PDF -> pre-check, repair & re-check."""
import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from print_ready import run_printready


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PrintReady — Print PDF Pre-Check, Repair & Re-Check")
        self.geometry("680x520")
        self.src = tk.StringVar()
        tk.Label(self, text="Print interior PDF file:").pack(anchor="w", padx=12, pady=(12, 2))
        row = tk.Frame(self)
        row.pack(fill="x", padx=12)
        tk.Entry(row, textvariable=self.src).pack(side="left", fill="x", expand=True)
        tk.Button(row, text="Browse…", command=self.pick).pack(side="left", padx=6)
        self.btn = tk.Button(self, text="Pre-Check, Fix & Re-Check", command=self.run, height=2)
        self.btn.pack(pady=12)
        self.log = scrolledtext.ScrolledText(self, wrap="word")
        self.log.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.write("PrintReady checks your print interior the way a KDP-style review\n"
                   "does, repairs the structural defects, then re-checks the file.\n"
                   "Everything runs locally — your manuscript never leaves this computer.\n")

    def write(self, s):
        self.log.insert("end", s)
        self.log.see("end")

    def pick(self):
        p = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")])
        if p:
            self.src.set(p)

    def run(self):
        src = self.src.get().strip()
        if not src or not os.path.isfile(src):
            messagebox.showerror("PrintReady", "Choose a PDF file first.")
            return
        self.btn.config(state="disabled")
        threading.Thread(target=self._work, args=(src,), daemon=True).start()

    def _work(self, src):
        try:
            outdir = os.path.join(os.path.dirname(src), "printready_output")
            s = run_printready(src, outdir)
            self.write(f"\nDone. Problems found: {s['found']} · auto-fixed: {s['fixed']} · "
                       f"remaining: {s['remaining']} ({s['errors_remaining']} blocking errors)\n"
                       f"Repaired PDF: {s['fixed_path']}\nReport: {s['report_path']}\n")
            self.write(f"Verdict: {s['verdict']}\n")
        except Exception as e:
            self.write(f"\nError: {e}\n")
        finally:
            self.btn.config(state="normal")


if __name__ == "__main__":
    App().mainloop()
