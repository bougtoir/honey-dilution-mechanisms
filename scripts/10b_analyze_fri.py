"""FRI-targeted analyses: selection-bias characterization, grouped CV
(chemistry vs label), flexible concentration-response fits, and the
extended sensitivity suite. Reads outputs of 08/09 and 10_analyze.py.
"""
import os
import json
import re
import warnings

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAB = os.path.join(ROOT, "results", "tables")
MOD = os.path.join(ROOT, "results", "models")
R = {}
LINES = []


def note(s):
    LINES.append(s); print(s)


def norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def main():
    df = pd.read_csv(os.path.join(ROOT, "data", "processed", "extraction.csv"))
    chem = pd.read_csv(os.path.join(ROOT, "data", "processed", "chemistry.csv"))
    rob = pd.read_csv(os.path.join(ROOT, "data", "processed", "risk_of_bias.csv"))
    el = pd.read_csv(os.path.join(ROOT, "data", "interim", "eligible.csv"))
    sc = pd.read_csv(os.path.join(ROOT, "data", "interim", "screened.csv"),
                     low_memory=False)
    base = json.load(open(os.path.join(MOD, "analysis_results.json")))

    # ============ B1: extraction-selection mechanism ============
    inc = el[el["elig"].isin(["include", "review_flag"])].copy()
    extracted = set(df["study_id"].unique())
    inc["has_pmcid"] = inc["pmcid"].notna()
    xmls = {os.path.basename(f)[:-4]
            for f in __import__("glob").glob(
                os.path.join(ROOT, "data", "raw", "fulltext", "*.xml"))}
    inc["xml_available"] = inc["pmcid"].isin(xmls)
    inc["extracted"] = inc["pmcid"].isin(extracted)
    sel = {
        "eligible": int(len(inc)),
        "with_pmcid": int(inc["has_pmcid"].sum()),
        "xml_available": int(inc["xml_available"].sum()),
        "extracted": int(inc["extracted"].sum()),
    }
    # compare extracted vs non-extracted on year
    ex_y = inc[inc["extracted"]]["year"].dropna().astype(float)
    nx_y = inc[~inc["extracted"]]["year"].dropna().astype(float)
    sel["year_median_extracted"] = float(ex_y.median())
    sel["year_median_nonextracted"] = float(nx_y.median())
    if len(ex_y) > 5 and len(nx_y) > 5:
        sel["year_mwu_p"] = float(stats.mannwhitneyu(ex_y, nx_y).pvalue)
    # journal distribution top non-extracted
    sel["top_journals_nonextracted"] = (inc[~inc["extracted"]]["journal"]
                                      .value_counts().head(5).to_dict())
    # open-access + mechanistic-flag comparison, extracted vs non-extracted
    def rate(col, mask):
        s = inc.loc[mask, col]
        s = s.dropna().astype(str).str.lower()
        return float(s.isin(["true", "y", "yes", "1"]).mean()) if len(s) else None
    sel["oa_rate_extracted"] = rate("isOpenAccess", inc["extracted"])
    sel["oa_rate_nonextracted"] = rate("isOpenAccess", ~inc["extracted"])
    for f_ in ["f_dilution", "f_peroxide", "f_mgo", "f_chem", "f_zone"]:
        sel[f"{f_}_rate_extracted"] = float(
            inc.loc[inc["extracted"], f_].astype(float).mean())
        sel[f"{f_}_rate_nonextracted"] = float(
            inc.loc[~inc["extracted"], f_].astype(float).mean())
    inc.to_csv(os.path.join(TAB, "eligibility_extraction_map.csv"), index=False)
    R["selection"] = sel
    note(f"B1: eligible {sel['eligible']}; PMCID {sel['with_pmcid']}; "
         f"OA-XML {sel['xml_available']}; extracted {sel['extracted']}. "
         f"Median year ex vs non-ex: {sel['year_median_extracted']:.0f} vs "
         f"{sel['year_median_nonextracted']:.0f} (p={sel.get('year_mwu_p', float('nan')):.3g})")

    # ============ concentration-response with flexible fits ============
    S = pd.read_csv(os.path.join(TAB, "conc_response_slopes.csv"))
    act = S[~S["measure"].isin(["pH"]) & ~S["outcome"].isin(["n_outperform_manuka"])]
    R["conc_response"] = {
        "n_series": int(len(act)), "n_studies": int(act.study_id.nunique()),
        "n_positive": int((act.spearman_rho > 0.2).sum()),
        "n_negative": int((act.spearman_rho < -0.2).sum()),
        "median_rho": float(act.spearman_rho.median()),
        "rho_iqr": [float(act.spearman_rho.quantile(0.25)),
                    float(act.spearman_rho.quantile(0.75))]}
    # nonlinear fit on the largest series (PMC12532491 zones): log-log slope
    g = df[(df.study_id == "PMC12532491") & df.concentration_pct.notna() &
           (df.outcome == "zone") & (df.value > 0) & (df.concentration_pct > 0)]
    if len(g) >= 8:
        X = np.log10(g.concentration_pct); y = np.log10(g.value)
        sl, ic, r, p, se = stats.linregress(X, y)
        R["conc_response"]["loglog_slope"] = float(sl)
        R["conc_response"]["loglog_slope_se"] = float(se)
        note(f"A1b: log-log slope zone~conc = {sl:.2f} +/- {se:.2f} "
             f"(sub-linear if <1)")

    # ============ chemistry vs label: leave-one-study-out CV ============
    chem["hkey"] = chem["honey_label"].map(norm)
    chemw = chem.pivot_table(index=["study_id", "hkey"], columns="chem_param",
                             values="value", aggfunc="mean").reset_index()
    mic = df[df.outcome.isin(["MIC", "zone"])].copy()
    mic["hkey"] = mic.honey_label.map(norm)
    J = mic.merge(chemw, on=["study_id", "hkey"], how="inner")
    jj = J[(J.outcome == "MIC") & (J.unit_basis.isin(
        ["%w/v", "%v/v", "%w/w", "% (basis unspecified)"]))].copy()
    jj["logmic"] = np.log10(jj["value"].clip(lower=0.5))
    preds_all = [p for p in ["pH", "moisture", "MGO", "TPC", "H2O2", "aw"]
                 if p in jj.columns]
    # choose predictor set maximizing complete rows
    import itertools
    best, keep = [], pd.DataFrame()
    for k in range(min(4, len(preds_all)), 1, -1):
        for combo in itertools.combinations(preds_all, k):
            kk = jj.dropna(subset=list(combo) + ["logmic"])
            if len(kk) >= 30 and kk.study_id.nunique() >= 3 and len(kk) > len(keep):
                best, keep = list(combo), kk
        if len(keep):
            break
    cv = {"predictors": best, "n": int(len(keep)),
          "n_studies": int(keep.study_id.nunique()) if len(keep) else 0}
    if len(keep) >= 30:
        studies = keep.study_id.unique()
        def cv_r2(feat_fn):
            preds_y, true_y = [], []
            for s in studies:
                tr, te = keep[keep.study_id != s], keep[keep.study_id == s]
                if len(tr) < 10:
                    continue
                Xtr = sm.add_constant(feat_fn(tr), has_constant="add")
                m = sm.OLS(tr.logmic, Xtr).fit()
                Xte = sm.add_constant(feat_fn(te), has_constant="add")
                preds_y.extend(m.predict(Xte).values)
                true_y.extend(te.logmic.values)
            preds_y, true_y = np.array(preds_y), np.array(true_y)
            sse = ((true_y - preds_y) ** 2).sum()
            sst = ((true_y - true_y.mean()) ** 2).sum()
            rmse = float(np.sqrt(sse / len(true_y)))
            return float(1 - sse / sst), rmse
        chem_cv = cv_r2(lambda d: d[best].astype(float))
        lab_cv = cv_r2(lambda d: pd.DataFrame(
            {"manuka": d.is_manuka.astype(float)}))
        both_cv = cv_r2(lambda d: pd.concat(
            [d[best].astype(float), d.is_manuka.astype(float).rename("manuka")],
            axis=1))
        null_cv = cv_r2(lambda d: pd.DataFrame(index=d.index))
        cv.update({"r2_cv_chem": chem_cv[0], "rmse_cv_chem": chem_cv[1],
                   "r2_cv_label": lab_cv[0], "rmse_cv_label": lab_cv[1],
                   "r2_cv_both": both_cv[0], "rmse_cv_both": both_cv[1],
                   "r2_cv_null": null_cv[0], "rmse_cv_null": null_cv[1]})
        note(f"A5-CV: LOSO-CV R2 chem={chem_cv[0]:.3f} label={lab_cv[0]:.3f} "
             f"both={both_cv[0]:.3f} null={null_cv[0]:.3f}")
    R["chem_vs_label_cv"] = cv
    keep.to_csv(os.path.join(TAB, "a5_cv_model_data.csv"), index=False)

    # ============ extended sensitivity suite ============
    micp = df[(df.outcome == "MIC") & (df.unit_basis.notna()) &
              (df.unit_basis != "mass") & (df.value > 0)]
    sens = {}
    lo = rob[rob.rating == "low"].study_id
    sens["low_rob"] = {"n": int(micp[micp.study_id.isin(lo)].shape[0]),
                       "studies": int(micp[micp.study_id.isin(lo)].study_id.nunique()),
                       "median": float(micp[micp.study_id.isin(lo)].value.median() or np.nan)}
    sens["manuka_excluded"] = {
        "n": int((~micp.is_manuka).sum()),
        "median": float(micp[~micp.is_manuka].value.median())}
    sens["manuka_only"] = {
        "n": int(micp.is_manuka.sum()),
        "median": float(micp[micp.is_manuka].value.median())}
    sens["w_v_basis_only"] = {
        "n": int((micp.unit_basis == "%w/v").sum()),
        "median": float(micp[micp.unit_basis == "%w/v"].value.median())}
    sens["v_v_basis_only"] = {
        "n": int((micp.unit_basis == "%v/v").sum()),
        "median": float(micp[micp.unit_basis == "%v/v"].value.median())}
    # studies that directly measured water activity / H2O2
    aw_st = chem[chem["chem_param"] == "aw"]["study_id"].unique()
    h2_st = chem[chem["chem_param"] == "H2O2"]["study_id"].unique()
    sens["aw_measured_studies"] = {
        "n": int(micp.study_id.isin(aw_st).sum()),
        "studies": int(micp[micp.study_id.isin(aw_st)].study_id.nunique()),
        "median": float(micp[micp.study_id.isin(aw_st)].value.median())
        if micp.study_id.isin(aw_st).any() else None}
    sens["h2o2_measured_studies"] = {
        "n": int(micp.study_id.isin(h2_st).sum()),
        "studies": int(micp[micp.study_id.isin(h2_st)].study_id.nunique()),
        "median": float(micp[micp.study_id.isin(h2_st)].value.median())
        if micp.study_id.isin(h2_st).any() else None}
    # peer-reviewed-only check: preprint DOI prefixes excluded
    preprint = df["doi"].fillna("").str.match(r"10\.(1101|21203|20944)")
    sens["peer_reviewed_only"] = {
        "n": int((~micp.doi.fillna("").str.match(
            r"10\.(1101|21203|20944)")).sum()),
        "median": float(micp[~micp.doi.fillna("").str.match(
            r"10\.(1101|21203|20944)")].value.median()),
        "note": "extracted corpus contains no preprint-DOI rows"
        if not preprint.any() else "preprint rows excluded"}
    # leave-one-study-out on the manuka-vs-other MWU
    loo = []
    for s in micp.study_id.unique():
        sub = micp[micp.study_id != s]
        a, b = sub[sub.is_manuka].value, sub[~sub.is_manuka].value
        if len(a) >= 5 and len(b) >= 5:
            loo.append({"dropped": s, "p": float(stats.mannwhitneyu(a, b).pvalue),
                        "med_mk": float(a.median()), "med_oth": float(b.median())})
    LOO = pd.DataFrame(loo)
    LOO.to_csv(os.path.join(TAB, "loo_manuka.csv"), index=False)
    sens["loo_manuka_ns_frac"] = float((LOO.p > 0.05).mean()) if len(LOO) else None
    R["sensitivity"] = sens
    for k, v in sens.items():
        note(f"S-{k}: {v}")

    # ============ natural-vs-artificial: per-study breakdown ============
    P = pd.read_csv(os.path.join(TAB, "natural_vs_artificial_pairs.csv"))
    if len(P):
        # direction-normalized effect: >1 means natural honey more potent
        # (zone: natural/artificial; MIC: artificial/natural)
        P["potency_ratio"] = np.where(
            P["outcome"] == "zone",
            P["natural_mean"] / P["artificial_mean"].replace(0, np.nan),
            P["artificial_mean"] / P["natural_mean"].replace(0, np.nan))
        P.to_csv(os.path.join(TAB, "natural_vs_artificial_pairs.csv"),
                 index=False)
        bys = P.groupby(["study_id", "outcome"]).agg(
            n=("potency_ratio", "size"),
            med_ratio=("potency_ratio", "median")).reset_index()
        R["artificial_by_study"] = bys.to_dict("records")
        note("A2 by-study (ratio>1 = natural more potent): " + "; ".join(
            f"{r.study_id}/{r.outcome}:n={int(r.n)},r={r.med_ratio:.2f}"
            for r in bys.itertuples()))
        gt1 = (P["potency_ratio"] > 1).sum()
        R["artificial_direction"] = {
            "n_pairs": int(len(P)), "n_natural_stronger": int(gt1),
            "n_artificial_ge": int(len(P) - gt1),
            "median_ratio": float(P["potency_ratio"].median()),
            "wilcoxon_p_logratio": float(stats.wilcoxon(
                np.log(P["potency_ratio"].dropna())).pvalue)
            if P["potency_ratio"].notna().sum() >= 5 else None}
        note(f"A2 direction: {gt1}/{len(P)} pairs natural more potent "
             f"(median ratio {P['potency_ratio'].median():.2f})")

    out = dict(base); out.update(R)
    with open(os.path.join(MOD, "analysis_results.json"), "w") as f:
        json.dump(out, f, indent=2, default=str)
    with open(os.path.join(MOD, "analysis_summary_fri.txt"), "w") as f:
        f.write("\n".join(LINES))
    note("wrote analysis_results.json (extended) + analysis_summary_fri.txt")


if __name__ == "__main__":
    main()
