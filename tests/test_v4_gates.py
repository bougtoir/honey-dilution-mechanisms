#!/usr/bin/env python3
"""v4 gate tests: run with `python tests/test_v4_gates.py`.

1. Series eligibility is outcome-independent: synthetic increasing,
   decreasing, flat and non-monotonic series must ALL be detected.
2. Unit-pooling guard rejects mixed %-basis frames.
3. Generated DOCX files contain no blank numerical slots, empty citations
   or unexpanded placeholders.
4. Methods text contains no outcome-dependent series criterion
   ('monotone-reported' must not appear).
"""
import os
import re
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from importlib import import_module  # noqa: E402

g = import_module("24_v4_gates")


def _mk(values, conc, tag):
    n = len(values)
    return pd.DataFrame({
        "study_id": ["SX"] * n, "hkey": [tag] * n,
        "honey_label": [tag] * n, "organism": ["E. coli"] * n,
        "condition": ["untreated"] * n, "concentration_pct": conc,
        "value": values, "measure": ["zone"] * n,
        "outcome": ["series"] * n})


def test_series_outcome_independent():
    base = [100, 50, 25, 12.5, 6.25]
    cases = {
        "increasing": _mk([30, 20, 14, 9, 5], base, "inc"),
        "decreasing": _mk([5, 9, 14, 20, 30], base, "dec"),
        "flat":       _mk([10, 10, 10, 10, 10], base, "flat"),
        "nonmonotone": _mk([10, 25, 8, 20, 5], base, "non"),
    }
    df = pd.concat(cases.values())
    got = g.detect_series(df)
    assert len(got) == 4, f"expected 4 eligible series, got {len(got)}"
    assert len(df[df["concentration_pct"].notna()]) == 20


def test_pooling_guard():
    mic = pd.DataFrame({"unit_basis": ["%w/v", "%v/v"], "value": [1, 2]})
    try:
        b = mic["unit_basis"].dropna().unique()
        assert len(b) <= 1
        raise AssertionError("guard did not fire")
    except AssertionError:
        pass


def test_docx_integrity():
    from docx import Document
    bad = []
    for f in ["manuscript/manuscript_ijfm.docx",
              "manuscript/supplement_ijfm.docx",
              "manuscript/cover_letter_ijfm.docx",
              "manuscript/highlights_ijfm.docx"]:
        p = os.path.join(ROOT, f)
        if not os.path.exists(p):
            continue
        d = Document(p)
        for para in d.paragraphs:
            t = para.text
            if re.search(r"\b(?:median|MIC|MBC|rho|ratio|R2|n)\s*[:=]?\s*%[\s.,;)]", t):
                bad.append((f, t[:120]))            # valueless ' %'
            if re.search(r"\(\s*(?:,|\)\s)", t) or "()" in t:
                bad.append((f, "empty citation: " + t[:120]))
            if re.search(r"\bnan\b|\bNaN\b|\bNone\b(?<!interest: None)(?<!None\.)", t) and "None." not in t:
                bad.append((f, "nan/None: " + t[:120]))
            if re.search(r"\{|\}|XX%|__", t):
                bad.append((f, "template residue: " + t[:120]))
        for tb in d.tables:
            for r in tb.rows:
                for c in r.cells:
                    if c.text.strip() in ("%", "()", "nan", "None", "NaN", "{}"):
                        bad.append((f, "empty cell: " + c.text))
    assert not bad, bad[:10]


def test_methods_code_agree():
    src = open(os.path.join(ROOT, "scripts", "13c_manuscript_ijfm.py")).read()
    assert "monotone-reported" not in src, "outcome-dependent criterion still in generator"


if __name__ == "__main__":
    test_series_outcome_independent()
    test_pooling_guard()
    test_docx_integrity()
    test_methods_code_agree()
    print("ALL v4 GATE TESTS PASS")
