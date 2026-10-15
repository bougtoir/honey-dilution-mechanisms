#!/usr/bin/env python3
"""Build the standalone tables docx by cloning Tables 1 and 2 (and their
captions/footnotes) directly from manuscript_ijfm.docx so that inline
and standalone representations can never diverge."""
import copy
import os

from docx import Document

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "manuscript", "manuscript_ijfm.docx")
DST = os.path.join(ROOT, "manuscript", "tables_ijfm.docx")

src = Document(SRC)
out = Document()
out.styles["Normal"].font.name = "Times New Roman"
from docx.shared import Pt
out.styles["Normal"].font.size = Pt(11)
out.add_paragraph("Tables")
out.add_paragraph(
    "Dilution-dependent antibacterial activity of honey: a systematic "
    "review and quantitative synthesis of physicochemical and "
    "microbiological evidence")

# Walk body elements; clone paragraphs that are table captions,
# the tables themselves, and their footnote paragraphs.
body = src.element.body
tables_seen = 0
keep_next_para = False
for el in body:
    tag = el.tag.split("}")[-1]
    if tag == "p":
        # check if paragraph text is a table caption or a Note
        texts = [n.text or "" for n in el.iter() if n.tag.endswith("}t")]
        txt = "".join(texts)
        if txt.startswith("Table 1.") or txt.startswith("Table 2.") \
                or keep_next_para:
            out.element.body.append(copy.deepcopy(el))
            keep_next_para = txt.startswith("Note:")
            continue
        keep_next_para = False
    elif tag == "tbl":
        tables_seen += 1
        out.element.body.append(copy.deepcopy(el))
        keep_next_para = True  # capture following Note paragraph
    else:
        keep_next_para = False
out.save(DST)
print("wrote tables_ijfm.docx; tables cloned:", tables_seen)
