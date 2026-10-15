"""Apply three-line formatting to the JFS manuscript, supplement and
standalone-tables DOCX files (in place), with a cell-text identity check.
"""
import os

from docx import Document

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# reuse the verified formatting helpers from 22_three_line_tables.py
# (its JOBS block is IJFM-specific and is not executed here)
_src = open(os.path.join(ROOT, "scripts", "22_three_line_tables.py")).read()
_ns = {"__file__": os.path.join(ROOT, "scripts", "22_three_line_tables.py")}
exec(_src.split("JOBS = [")[0], _ns)
three_line, cell_texts = _ns["three_line"], _ns["cell_texts"]

for name in ("manuscript_jfs.docx", "supplement_jfs.docx",
             "tables_jfs.docx"):
    path = os.path.join(ROOT, "manuscript", name)
    d = Document(path)
    before = cell_texts(d)
    three_line(d)
    assert cell_texts(d) == before, name
    d.save(path)
    print(f"three-lined {name} ({len(d.tables)} tables)")
