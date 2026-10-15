"""Assemble the submission ZIP archive."""
import os
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "submission")
os.makedirs(OUT, exist_ok=True)

INCLUDE_DIRS = ["scripts", "data/processed", "results", "references",
                "manuscript", "qc", "logs"]
INCLUDE_FILES = ["README.md", "Makefile", "environment.yml",
                 "requirements.txt", "data/interim/screened.csv",
                 "data/interim/eligible.csv",
                 "data/interim/manual_extraction.csv",
                 "data/interim/auto_outcomes_A.csv",
                 "data/interim/auto_chem_B.csv",
                 "data/interim/auto_series_C.csv",
                 "data/interim/table_catalog.csv"]

zpath = os.path.join(OUT, "honey_dilution_review_submission.zip")
with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
    for d in INCLUDE_DIRS:
        for dirpath, _, files in os.walk(os.path.join(ROOT, d)):
            for fn in files:
                fp = os.path.join(dirpath, fn)
                z.write(fp, os.path.relpath(fp, ROOT))
    for f in INCLUDE_FILES:
        fp = os.path.join(ROOT, f)
        if os.path.exists(fp):
            z.write(fp, f)

n = len(zipfile.ZipFile(zpath).namelist())
sz = os.path.getsize(zpath) / 1e6
print(f"wrote {zpath} ({n} files, {sz:.1f} MB)")
