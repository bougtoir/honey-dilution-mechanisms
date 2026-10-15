#!/usr/bin/env python3
"""IJFM v5 gates 1-2: concentration-basis provenance audit and
study-aware natural-vs-artificial inference.

Gate 1: re-derive every %-row's unit basis from explicit evidence
(unit_raw first, then concentration-header binding in context). Rows
without explicit evidence stay 'basis unspecified'; they are never
treated as commensurate with known bases. Provenance is recorded per row.

Gate 2: natural-vs-artificial contrast at study level per outcome scale
(MIC/MBC -> log potency ratio; zone -> absolute mm difference; no
infinite ratios; zeros preserved).
"""
import json
import os
import re

import numpy as np
import pandas as pd
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def P(*a):
    return os.path.join(ROOT, *a)


EX = pd.read_csv(P("data", "processed", "extraction.csv"))
OUT = {}

# ----------------------------------------------------------------- G1 basis
BASIS_FROM_RAW = {"%v/v": "%v/v", "%w/v": "%w/v", "%w/w": "%w/w",
                  "%w/v phenol": "%w/v phenol"}
HDR = re.compile(
    r"\(%\s*,?\s*(w/v|v/v|w/w)\)|%\s*\((w/v|v/v|w/w)\)"
    r"|concentrations?\s*\((w/v|v/v|w/w)\)|\b(w/v|v/v|w/w)\s*%",
    re.I)


def hdr_basis(ctx):
    m = HDR.search(ctx or "")
    if not m:
        return None
    tok = next(g for g in m.groups() if g).lower().replace(" ", "")
    return "%" + tok


prov_rows = []
basis_new = []
for i, r in EX.iterrows():
    ur = str(r["unit_raw"])
    old = r["unit_basis_v4"] if "unit_basis_v4" in EX.columns \
        else r["unit_basis"]
    if ur in BASIS_FROM_RAW:
        new, src = BASIS_FROM_RAW[ur], "unit_raw"
    elif ur == "%":
        hb = hdr_basis(str(r["context"]))
        new = hb or "% (basis unspecified)"
        src = "context_header" if hb else "none"
    else:
        new, src = old, "nonpercent"
    basis_new.append(new)
    if new != old:
        prov_rows.append({"row": i, "pmcid": r["pmcid"],
                          "study_id": r["study_id"], "measure": r["measure"],
                          "value": r["concentration_pct"],
                          "unit_raw": ur, "basis_old": old, "basis_new": new,
                          "basis_source": src})
if "unit_basis_v4" not in EX.columns:
    EX["unit_basis_v4"] = old_basis = EX["unit_basis"].copy()
EX["unit_basis"] = basis_new
EX["basis_provenance"] = [
    ("unit_raw" if str(u) in BASIS_FROM_RAW else
     ("context_header" if u == "%" and hdr_basis(str(c)) else
      ("none" if u == "%" else "nonpercent")))
    for u, c in zip(EX["unit_raw"], EX["context"])]
EX.to_csv(P("data", "processed", "extraction.csv"), index=False)
pd.DataFrame(prov_rows).to_csv(P("results", "tables",
                                 "basis_audit_v5.csv"), index=False)
OUT["basis_audit"] = {
    "rows_upgraded": len(prov_rows),
    "by_target": pd.DataFrame(prov_rows)["basis_new"].value_counts().to_dict()
    if prov_rows else {},
    "basis_counts": EX["unit_basis"].value_counts().to_dict(),
}

# organism medians per basis (MIC rows, percentage bases only)
mic = EX[(EX["outcome"].isin(["MIC", "MBC"])) &
         (EX["value"] > 0) &
         (EX["unit_basis"].str.startswith("%"))].copy()
mic["concentration_pct"] = mic["value"]
tab = []
for (basis, org), g in mic.groupby(["unit_basis", "organism"]):
    if len(g) < 5:
        continue
    tab.append({"basis": basis, "organism": org,
                "n_studies": int(g["study_id"].nunique()),
                "n_honeys": int(g[["study_id", "honey_label"]]
                                .drop_duplicates().shape[0]),
                "n_obs": int(len(g)),
                "median": float(g["concentration_pct"].median()),
                "q1": float(g["concentration_pct"].quantile(.25)),
                "q3": float(g["concentration_pct"].quantile(.75))})
pd.DataFrame(tab).to_csv(P("results", "tables",
                           "organism_mic_by_basis_v5.csv"), index=False)
OUT["A6_basis_v5"] = {"table": tab}

# Manuka vs non-manuka within compatible bases, within-study only
mrows = []
for (sid, basis), g in mic.groupby(["study_id", "unit_basis"]):
    man = g[g["is_manuka"] == True]["concentration_pct"]
    oth = g[g["is_manuka"] == False]["concentration_pct"]
    if len(man) and len(oth):
        mrows.append({"study_id": sid, "basis": basis,
                      "manuka_med": float(man.median()),
                      "other_med": float(oth.median()),
                      "diff": float(man.median() - oth.median()),
                      "n_manuka": int(len(man)), "n_other": int(len(oth))})
mdf = pd.DataFrame(mrows)
OUT["manuka_v5"] = {
    "paired_within_study_basis": mrows,
    "n_studies": int(mdf["study_id"].nunique()) if len(mdf) else 0,
    "median_diff": float(mdf["diff"].median()) if len(mdf) else None,
}
# descriptive per-basis medians (no pooling across bases)
desc = {}
for basis, g in mic.groupby("unit_basis"):
    desc[basis] = {
        "manuka": {"n": int(len(g[g.is_manuka == True])),
                   "median": float(g.loc[g.is_manuka == True,
                                        "concentration_pct"].median())
                   if (g.is_manuka == True).any() else None},
        "other": {"n": int(len(g[g.is_manuka == False])),
                  "median": float(g.loc[g.is_manuka == False,
                                       "concentration_pct"].median())
                  if (g.is_manuka == False).any() else None}}
OUT["manuka_v5"]["by_basis_descriptive"] = desc

# ----------------------------------------------------------------- G2 pairs
pa = pd.read_csv(P("results", "tables", "natural_vs_artificial_pairs.csv"))

# comparator quality from artificial honey labels in extraction
art = EX[EX["is_artificial"] == True].groupby("study_id")["honey_label"].unique()
QUAL = {}
for sid, labels in art.items():
    lab = " | ".join(map(str, labels)).lower()
    if "matched" in lab or "82%" in lab or "simulated honey" in lab:
        q = "composition_matched_or_partial"
    elif "artificial" in lab:
        q = "sugar_equivalent_unspecified"
    else:
        q = "partial_or_unspecified"
    QUAL[sid] = q
OUT["comparator_quality"] = {k: {"quality": v, "labels": list(map(str, art[k]))}
                             for k, v in QUAL.items()}

res = {}
for outcome, cmp_col in [("MIC", "mic"), ("MBC", "mbc"), ("zone", "zone")]:
    sub = pa[pa["outcome"] == outcome].copy()
    if outcome == "zone":
        sub = sub.dropna(subset=["diff"])
        stud = sub.groupby("study_id")["diff"].median()
        res[outcome] = {
            "n_pairs": int(len(sub)), "n_studies": int(len(stud)),
            "median_diff_mm": float(sub["diff"].median()),
            "study_medians_mm": {k: float(v) for k, v in stud.items()},
            "all_positive": bool((stud > 0).all()),
            "wilcoxon_p_study": float(stats.wilcoxon(stud).pvalue)
            if len(stud) >= 3 else None,
            "zero_denominator_pairs": int((pa.loc[pa["outcome"] == "zone",
                                                "artificial_mean"] == 0).sum()),
        }
    else:
        sub = sub[(sub["natural_mean"] > 0) & (sub["artificial_mean"] > 0)]
        # potency ratio: artificial / natural for MIC/MBC (>1 = natural stronger)
        sub["log_ratio"] = np.log(sub["artificial_mean"] / sub["natural_mean"])
        stud = sub.groupby("study_id")["log_ratio"].median()
        res[outcome] = {
            "n_pairs": int(len(sub)), "n_studies": int(len(stud)),
            "median_log_ratio": float(sub["log_ratio"].median()),
            "median_ratio": float(np.exp(sub["log_ratio"].median())),
            "study_median_ratios": {k: float(np.exp(v)) for k, v in stud.items()},
            "all_studies_gt1": bool((np.exp(stud) > 1).all())
            if len(stud) else None,
            "wilcoxon_p_study": float(stats.wilcoxon(stud).pvalue)
            if len(stud) >= 3 else None,
        }
        res[outcome]["ci95_log_ratio"] = (
            [float(np.percentile(sub["log_ratio"], 2.5)),
             float(np.percentile(sub["log_ratio"], 97.5))]
            if len(sub) >= 8 else None)
OUT["A2_v5"] = res

with open(P("results", "models", "v5_analysis.json"), "w") as f:
    json.dump(OUT, f, indent=1)
ar = json.load(open(P("results", "models", "analysis_results.json")))
ar.update(OUT)
json.dump(ar, open(P("results", "models", "analysis_results.json"), "w"),
          indent=1)
print(json.dumps({k: v for k, v in OUT.items()
                  if k in ("basis_audit", "A2_v5")}, indent=1)[:3000])
print("manuka paired studies:", OUT["manuka_v5"]["n_studies"],
      "median diff:", OUT["manuka_v5"]["median_diff"])
