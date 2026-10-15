"""Quantitative evidence synthesis.

Analyses
--------
A1  Concentration-response: per-series sign/slope + pooled within-study trend.
A2  Natural honey vs artificial/sugar-equivalent controls (paired).
A3  Honey-level H2O2/chemistry vs antibacterial outcome (cross-study join).
A4  Catalase perturbation: residual activity fraction (paired).
A5  Chemistry predictors vs botanical/medical label (nested-model comparison).
A6  Organism-specific heterogeneity.
S   Sensitivity analyses.

Outputs: results/models/analysis_results.json, results/models/analysis_summary.txt,
         results/tables/*.csv
"""
import os
import json
import re
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAB = os.path.join(ROOT, "results", "tables")
MOD = os.path.join(ROOT, "results", "models")
os.makedirs(TAB, exist_ok=True)
os.makedirs(MOD, exist_ok=True)

R = {}  # results dict
SUM = []  # human-readable summary lines


def note(s):
    SUM.append(s)
    print(s)


def norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def wilcoxon_safe(d):
    d = np.asarray(d, float)
    d = d[~np.isnan(d)]
    d = d[d != 0]
    if len(d) < 5:
        return np.nan, len(d)
    return stats.wilcoxon(d).pvalue, len(d)


def main():
    df = pd.read_csv(os.path.join(ROOT, "data", "processed", "extraction.csv"))
    chem = pd.read_csv(os.path.join(ROOT, "data", "processed", "chemistry.csv"))
    rob = pd.read_csv(os.path.join(ROOT, "data", "processed", "risk_of_bias.csv"))
    df["hkey"] = df["honey_label"].map(norm)
    chem["hkey"] = chem["honey_label"].map(norm)

    note(f"Dataset: {len(df)} rows, {df.study_id.nunique()} studies")
    R["n_rows"] = int(len(df)); R["n_studies"] = int(df.study_id.nunique())

    # ---------------- A1: concentration-response ----------------
    ser = df[(df["outcome"] == "series") | df["concentration_pct"].notna()].copy()
    ser = ser.dropna(subset=["concentration_pct", "value"])
    slopes = []
    for (sid, honey, org, cond), g in ser.groupby(
            ["study_id", "hkey", "organism", "condition"]):
        g = g.dropna(subset=["concentration_pct", "value"])
        if g["concentration_pct"].nunique() >= 3 and len(g) >= 3:
            rho, p = stats.spearmanr(g["concentration_pct"], g["value"])
            slopes.append({"study_id": sid, "honey": g["honey_label"].iloc[0],
                           "organism": org, "condition": cond,
                           "n": len(g), "n_conc": g["concentration_pct"].nunique(),
                           "spearman_rho": rho, "p": p,
                           "measure": g["measure"].iloc[0] if "measure" in g else "value",
                           "outcome": g["outcome"].iloc[0]})
    S = pd.DataFrame(slopes)
    S.to_csv(os.path.join(TAB, "conc_response_slopes.csv"), index=False)
    if len(S):
        act = S[~S["measure"].isin(["pH"]) & ~S["outcome"].isin(["n_outperform_manuka"])]
        pos = (act["spearman_rho"] > 0.2).sum(); neg = (act["spearman_rho"] < -0.2).sum()
        flat = len(act) - pos - neg
        R["A1"] = {"n_series": int(len(S)), "n_activity_series": int(len(act)),
                   "positive": int(pos), "negative": int(neg), "flat": int(flat),
                   "median_rho": float(act["spearman_rho"].median()),
                   "pH_series_note": "pH series (PMC2478674) rise with dilution as expected"}
        note(f"A1: {len(act)} activity concentration-series; positive slope {pos}, "
             f"negative {neg}, flat {flat}; median rho={act['spearman_rho'].median():.2f}")
        ph = S[S["measure"] == "pH"]
        if len(ph):
            note(f"     pH-vs-dilution series: median rho={ph['spearman_rho'].median():.2f} "
                 f"(n={len(ph)}; pH rises as honey is diluted)")
            R["A1"]["pH_median_rho"] = float(ph["spearman_rho"].median())
    else:
        R["A1"] = {"n_series": 0}

    # ---------------- A2: natural vs artificial ----------------
    pairs = []
    nat = df[(~df["is_artificial"]) & df["outcome"].isin(["zone", "MIC", "MBC"])]
    art = df[(df["is_artificial"]) & df["outcome"].isin(["zone", "MIC", "MBC"])]
    for (sid, org, outc, conc), g in art.groupby(
            ["study_id", "organism", "outcome", "concentration_pct"], dropna=False):
        nn = nat[(nat["study_id"] == sid) & (nat["organism"] == org) &
                 (nat["outcome"] == outc)]
        if conc == conc:  # not NaN
            nn = nn[nn["concentration_pct"] == conc]
        if len(nn) == 0:
            continue
        pairs.append({"study_id": sid, "organism": org, "outcome": outc,
                      "concentration_pct": conc,
                      "natural_mean": nn["value"].mean(), "n_natural": len(nn),
                      "artificial_mean": g["value"].mean(), "n_artificial": len(g)})
    P = pd.DataFrame(pairs)
    if len(P):
        P["diff"] = P["natural_mean"] - P["artificial_mean"]
        P["ratio"] = P["natural_mean"] / P["artificial_mean"].replace(0, np.nan)
        P.to_csv(os.path.join(TAB, "natural_vs_artificial_pairs.csv"), index=False)
        z = P[P["outcome"] == "zone"]
        mic = P[P["outcome"].isin(["MIC", "MBC"])]
        p_zone, nz = wilcoxon_safe(z["diff"])
        R["A2"] = {"n_pairs": int(len(P)), "zone_pairs": int(len(z)),
                   "mic_pairs": int(len(mic)),
                   "zone_wilcoxon_p": (None if np.isnan(p_zone) else float(p_zone)),
                   "zone_median_diff_mm": float(z["diff"].median()) if len(z) else None,
                   "mic_median_ratio": float(mic["ratio"].median()) if len(mic) else None}
        note(f"A2: {len(P)} natural-vs-artificial pairs; zone pairs={len(z)} "
             f"median diff={z['diff'].median():.1f} mm (p={p_zone:.3g}); "
             f"MIC pairs={len(mic)} median ratio={mic['ratio'].median():.2f}")
    else:
        R["A2"] = {"n_pairs": 0}
        note("A2: no paired natural-vs-artificial observations")

    # ---------------- A3: chemistry vs outcome join ----------------
    chemw = chem.pivot_table(index=["study_id", "hkey"], columns="chem_param",
                             values="value", aggfunc="mean").reset_index()
    mic = df[df["outcome"].isin(["MIC", "zone", "MBC"])].copy()
    J = mic.merge(chemw, on=["study_id", "hkey"], how="inner")
    J.to_csv(os.path.join(TAB, "outcome_chem_joined.csv"), index=False)
    note(f"A3 join: {len(J)} outcome rows with chemistry, {J.study_id.nunique()} studies")
    R["A3_joined_rows"] = int(len(J)); R["A3_joined_studies"] = int(J.study_id.nunique())

    corr_rows = []
    for par in ["H2O2", "MGO", "aw", "pH", "TPC", "phenol_equiv", "moisture"]:
        for outc in ["MIC", "zone"]:
            jj = J[(J["outcome"] == outc) & J[par].notna() & J["value"].notna()] \
                if par in J.columns else pd.DataFrame()
            if outc == "MIC":  # only comparable %-unit MICs
                jj = jj[jj["unit"] == "%"]
            if len(jj) >= 12:
                rho, p = stats.spearmanr(jj[par], jj["value"])
                corr_rows.append({"param": par, "outcome": outc, "n": len(jj),
                                  "n_studies": jj.study_id.nunique(),
                                  "spearman_rho": rho, "p": p})
    C = pd.DataFrame(corr_rows)
    C.to_csv(os.path.join(TAB, "chem_outcome_correlations.csv"), index=False)
    R["A3_correlations"] = corr_rows
    for r in corr_rows:
        note(f"A3: {r['param']} vs {r['outcome']}: rho={r['spearman_rho']:.2f} "
             f"(n={r['n']}, {r['n_studies']} studies, p={r['p']:.3g})")

    # ---------------- A4: catalase residual ----------------
    cat = df[df["condition"].str.contains("catalase", case=False, na=False)]
    cat_rows = []
    for (sid, hkey, org, outc, conc), g in cat.groupby(
            ["study_id", "hkey", "organism", "outcome", "concentration_pct"],
            dropna=False):
        base = df[(df["study_id"] == sid) & (df["hkey"] == hkey) &
                  (df["organism"] == org) & (df["outcome"] == outc) &
                  (df["condition"] == "untreated")]
        if conc == conc:
            base = base[base["concentration_pct"] == conc]
        if len(base):
            for _, r in g.iterrows():
                cat_rows.append({"study_id": sid, "honey": r["honey_label"],
                                 "organism": org, "outcome": outc,
                                 "concentration_pct": conc,
                                 "untreated": base["value"].mean(),
                                 "catalase": r["value"],
                                 "residual_frac": r["value"] / base["value"].mean()
                                 if base["value"].mean() else np.nan})
    K = pd.DataFrame(cat_rows)
    if len(K):
        K.to_csv(os.path.join(TAB, "catalase_pairs.csv"), index=False)
        R["A4"] = {"n_pairs": int(len(K)), "studies": sorted(K.study_id.unique()),
                   "median_residual_frac": float(K["residual_frac"].median()),
                   "frac_gt50": float((K["residual_frac"] > 0.5).mean())}
        note(f"A4: {len(K)} catalase pairs from {K.study_id.nunique()} studies; "
             f"median residual fraction={K['residual_frac'].median():.2f}")
    else:
        R["A4"] = {"n_pairs": 0}
        note("A4: no catalase pairs")

    # ---------------- A5: chemistry vs label ----------------
    try:
        import statsmodels.api as sm
        jj = J[(J["outcome"] == "MIC") & J["unit"].isin(["%", "% v/v", "% w/v"])].copy()
        jj = jj.dropna(subset=["value"])
        jj["logmic"] = np.log10(jj["value"].clip(lower=0.5))
        # choose predictor set maximizing complete-case coverage (>=30 rows, >=2 preds)
        import itertools
        cand = [p for p in ["H2O2", "MGO", "aw", "pH", "TPC", "moisture",
                            "phenol_equiv", "free_acidity"] if p in jj.columns]
        best, keep = [], pd.DataFrame()
        for k in range(min(4, len(cand)), 1, -1):
            for combo in itertools.combinations(cand, k):
                kk = jj.dropna(subset=list(combo) + ["logmic"])
                if len(kk) >= 30 and len(kk) > len(keep):
                    best, keep = list(combo), kk
            if len(keep):
                break
        preds = best
        R["A5"] = {"n_complete": int(len(keep)), "predictors": preds,
                   "n_studies": int(keep.study_id.nunique()) if len(keep) else 0}
        if len(keep) >= 30:
            X = sm.add_constant(keep[preds])
            m_chem = sm.OLS(keep["logmic"], X).fit()
            lab = pd.get_dummies(keep["is_manuka"].astype(int).rename("manuka"))
            Xl = sm.add_constant(lab.astype(float))
            m_lab = sm.OLS(keep["logmic"], Xl).fit()
            Xb = sm.add_constant(pd.concat([keep[preds], lab], axis=1).astype(float))
            m_both = sm.OLS(keep["logmic"], Xb).fit()
            R["A5"].update({
                "r2_chem": float(m_chem.rsquared),
                "r2_label": float(m_lab.rsquared),
                "r2_both": float(m_both.rsquared),
                "f_p_label_added": float(m_both.compare_f_test(m_chem)[1])})
            note(f"A5: log10(MIC%) ~ chemistry R2={m_chem.rsquared:.3f}; "
                 f"label-only R2={m_lab.rsquared:.3f}; combined R2={m_both.rsquared:.3f}")
            keep.to_csv(os.path.join(TAB, "a5_model_data.csv"), index=False)
        else:
            note(f"A5: insufficient complete-case rows ({len(keep)})")
    except Exception as e:
        R["A5_error"] = str(e)
        note(f"A5 failed: {e}")

    # ---------------- A6: organism heterogeneity ----------------
    micp = df[(df["outcome"] == "MIC") & (df["unit"].isin(["%", "% v/v", "% w/v"])) &
              (df["value"] > 0)]
    grp = micp.groupby("organism")["value"].median().sort_values()
    kw = stats.kruskal(*[g["value"].values for _, g in micp.groupby("organism")
                         if len(g) >= 5])
    top = grp[grp.index.isin(micp.groupby("organism").size()
                             [lambda s: s >= 30].index)]
    R["A6"] = {"kruskal_H": float(kw.statistic), "kruskal_p": float(kw.pvalue),
               "median_MIC_by_organism": grp.head(15).round(2).to_dict()}
    note(f"A6: MIC% differs across organisms (Kruskal H={kw.statistic:.1f}, "
         f"p={kw.pvalue:.3g})")
    for o, v in top.items():
        note(f"      {o}: median MIC {v}%")

    # manuka vs non-manuka MIC
    mk = micp.groupby(["is_manuka"])["value"].median()
    u = stats.mannwhitneyu(micp[micp["is_manuka"]]["value"],
                           micp[~micp["is_manuka"]]["value"])
    R["A6_manuka"] = {"median_manuka": float(mk.get(True, np.nan)),
                      "median_other": float(mk.get(False, np.nan)),
                      "mwu_p": float(u.pvalue)}
    note(f"A6: manuka median MIC {mk.get(True):.1f}% vs other {mk.get(False):.1f}% "
         f"(MWU p={u.pvalue:.3g})")

    # ---------------- Sensitivity ----------------
    lo = rob[rob["rating"] == "low"]["study_id"]
    mic_lo = micp[micp["study_id"].isin(lo)]
    R["S1_lowRoB"] = {"n_rows": int(len(mic_lo)), "n_studies": int(mic_lo.study_id.nunique()),
                      "median_MIC": float(mic_lo["value"].median()) if len(mic_lo) else None}
    note(f"S1: low-RoB subset {mic_lo.study_id.nunique()} studies, "
         f"{len(mic_lo)} MIC rows, median {mic_lo['value'].median() if len(mic_lo) else float('nan'):.1f}%")

    # ---------------- write ----------------
    with open(os.path.join(MOD, "analysis_results.json"), "w") as f:
        json.dump(R, f, indent=2, default=str)
    with open(os.path.join(MOD, "analysis_summary.txt"), "w") as f:
        f.write("\n".join(SUM))
    note("wrote analysis_results.json, analysis_summary.txt")


if __name__ == "__main__":
    main()
