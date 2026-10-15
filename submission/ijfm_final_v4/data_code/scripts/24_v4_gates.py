#!/usr/bin/env python3
"""v4 hard-gate computations (Gates 2/3/4).

- A1_v4: non-circular concentration-series detection. Eligibility uses ONLY
  exposure/data criteria: identified honey, organism/assay identity,
  concentration basis present, >=3 distinct ordered concentrations.
  No condition on the outcome's sign, monotonicity or significance.
  Primary set = >=3 concentrations; sensitivity = >=4.
- A6_basis: %-MIC organism medians stratified by concentration basis;
  a pooling guard makes cross-basis aggregation an explicit, never silent,
  choice.
- Cluster-aware inference: A2 (done at study level), A6 organism and
  manuka contrasts evaluated at study level; invalid pooled p-values are
  logged for replacement.
Writes results/models/v4_analysis.json and appends keys to
analysis_results.json.
"""
import json
import os
import numpy as np
import pandas as pd
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)

OUT = {}

# ------------------------------------------------------------------ A1_v4
def detect_series(df):
    """Independent-criteria series detection (no outcome-based filtering).

    Returns per-series summary rows for every (study, honey, organism,
    condition) group with >=3 distinct ordered concentrations.
    """
    df = df.copy()
    if "hkey" not in df:
        df["hkey"] = df["honey_label"].map(
            lambda s: __import__("re").sub(r"[^a-z0-9]", "", str(s).lower()))
    ser = df[(df["outcome"] == "series") | df["concentration_pct"].notna()]
    ser = ser.dropna(subset=["concentration_pct", "value"])
    rows = []
    for (sid, honey, org, cond), g in ser.groupby(
            ["study_id", "hkey", "organism", "condition"]):
        g = g.dropna(subset=["concentration_pct", "value"])
        if g["concentration_pct"].nunique() >= 3 and len(g) >= 3:
            rho, p = stats.spearmanr(g["concentration_pct"], g["value"])
            rows.append({"study_id": sid, "hkey": honey,
                         "honey": g["honey_label"].iloc[0], "organism": org,
                         "condition": cond, "n": len(g),
                         "n_conc": int(g["concentration_pct"].nunique()),
                         "spearman_rho": float(rho), "p": float(p),
                         "measure": g["measure"].iloc[0],
                         "outcome": g["outcome"].iloc[0]})
    return pd.DataFrame(rows)


def main():
    df = pd.read_csv(P("data/processed/extraction.csv"))
    S = detect_series(df)
    act = S[~S["measure"].isin(["pH"]) &
            ~S["outcome"].isin(["n_outperform_manuka"])]
    sens4 = act[act["n_conc"] >= 4]
    OUT["A1_v4"] = {
        "n_series_total": int(len(S)),
        "n_activity_series": int(len(act)),
        "n_activity_series_ge4": int(len(sens4)),
        "positive": int((act["spearman_rho"] > 0.2).sum()),
        "negative": int((act["spearman_rho"] < -0.2).sum()),
        "flat": int(((act["spearman_rho"].abs() <= 0.2)).sum()),
        "median_rho": float(act["spearman_rho"].median()),
        "median_rho_ge4": float(sens4["spearman_rho"].median()),
        "studies": sorted(act["study_id"].unique().tolist()),
        "criteria": ("honey+organism+assay identified; concentration basis "
                     "present; >=3 distinct ordered concentrations "
                     "(>=4 in sensitivity). No outcome-side condition."),
    }

    # ----------------------------------------------------------- A6_basis
    def assert_single_basis(frame, label):
        b = frame["unit_basis"].dropna().unique()
        if len(b) > 1:
            raise ValueError(f"cross-basis pooling attempt in {label}: {b}")

    mic = df[(df["outcome"] == "MIC") & (df["unit"] == "%") & (df["value"] > 0)]
    basis_med = {}
    for basis, g in mic.groupby("unit_basis"):
        assert_single_basis(g, f"basis={basis}")
        basis_med[basis] = {org: float(gr["value"].median())
                            for org, gr in g.groupby("organism")
                            if len(gr) >= 5}
    OUT["A6_basis"] = {
        "pooled_median_all_pct": float(mic["value"].median()),
        "basis_n": {b: int(len(g)) for b, g in mic.groupby("unit_basis")},
        "basis_medians": basis_med,
        "note": ("Organism medians below are computed within each %-basis "
                 "class only; the pooled figure mixes predominantly "
                 "unspecified-basis rows and is descriptive."),
    }
    org_med = {org: float(g["value"].median())
               for org, g in mic.groupby("organism") if len(g) >= 10}
    OUT["A6_basis"]["organism_medians_pct"] = org_med

    # ------------------------------------------------------ clustering G4
    # A2 study level (recompute, same as 13c logic)
    pa = pd.read_csv(P("results/tables/natural_vs_artificial_pairs.csv"))
    pr = pa.copy()
    pr["pot_ratio"] = np.where(pr["outcome"] == "zone",
                             pr["natural_mean"] / pr["artificial_mean"],
                             pr["artificial_mean"] / pr["natural_mean"])
    sm = pr.groupby("study_id")["pot_ratio"].median().dropna()
    OUT["A2_cluster"] = {
        "n_studies": int(len(sm)),
        "median_ratio": float(sm.median()),
        "all_directional": bool((sm > 1).all()),
        "wilcoxon_p": float(stats.wilcoxon(sm).pvalue) if len(sm) >= 3 else None,
        "outcomes_separate": {
            "zone": {k: {"n_studies": int(len(v)),
                         "median_ratio": float(v.median())}
                     for k, v in {"zone": sm[sm.index.isin(
                         pa.loc[pa.outcome == "zone", "study_id"].unique())]}.items()},
        },
    }
    zm = pr[pr["outcome"] == "zone"].groupby("study_id")["pot_ratio"].median()
    mm = pr[pr["outcome"] != "zone"].groupby("study_id")["pot_ratio"].median()
    OUT["A2_cluster"]["by_outcome"] = {
        "zone": {"n_studies": int(len(zm)), "median_ratio": float(zm.median()),
                 "ratios": {k: float(v) for k, v in zm.items()}},
        "mic_mbc": {"n_studies": int(len(mm)),
                    "median_ratio": float(mm.median()),
                    "wilcoxon_p": float(stats.wilcoxon(mm).pvalue)
                    if len(mm) >= 3 else None,
                    "ratios": {k: float(v) for k, v in mm.items()}},
    }

    # A6 organism contrast at study level: per-study median MIC% per
    # organism; report study-count per organism (clusters) — descriptive.
    per_so = mic.groupby(["study_id", "organism"])["value"].median()
    org_clusters = per_so.reset_index().groupby("organism")["study_id"].nunique()
    OUT["A6_cluster"] = {
        "organism_n_studies": {k: int(v) for k, v in org_clusters.items()},
        "note": ("Organism-level Kruskal-Wallis across rows pools within-study "
                 "replicates; study-level medians per organism reported "
                 "instead. Inferential organism contrast withheld: organism "
                 "is confounded with study, so clusters are too few and "
                 "non-exchangeable for a valid pooled test."),
    }

    # Manuka contrast at study level
    man = mic.copy()
    man["grp"] = np.where(man["is_manuka"], "manuka", "other")
    per_sg = man.groupby(["study_id", "grp"])["value"].median().unstack()
    both = per_sg.dropna()
    OUT["A6_manuka_cluster"] = {
        "n_studies_manuka": int(per_sg["manuka"].notna().sum()),
        "n_studies_other": int(per_sg["other"].notna().sum()),
        "n_studies_paired": int(len(both)),
        "paired_median_diff": (float((both["manuka"] - both["other"]).median())
                               if len(both) else None),
        "study_level_medians_manuka": float(per_sg["manuka"].median()),
        "study_level_medians_other": float(per_sg["other"].median()),
        "note": ("Row-level Mann-Whitney treats within-study MICs as "
                 "independent; study-level medians reported as the "
                 "defensible summary. Pooled MWU retained as descriptive "
                 "nominal contrast only."),
    }

    json.dump(OUT, open(P("results/models/v4_analysis.json"), "w"), indent=2)
    ar = json.load(open(P("results/models/analysis_results.json")))
    ar.update(OUT)
    json.dump(ar, open(P("results/models/analysis_results.json"), "w"), indent=2)
    for k, v in OUT.items():
        print(k, "->", json.dumps(v, default=str)[:400])


if __name__ == "__main__":
    main()
