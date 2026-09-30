"""Write the data dictionary and compute a structured risk-of-bias / reporting-quality
assessment for each extracted study.

RoB framework (custom, documented): no validated tool exists for cross-study
antibacterial bench data. Domains:
  D1 assay standardization (recognized method keywords in title/abstract or table ctx)
  D2 comparator quality (artificial honey / sugar-equivalent / vehicle control used)
  D3 replication & dispersion reporting (SD/SE/n reported in extracted table)
  D5 mechanistic perturbation present (catalase / H2O2 / MGO measured)
  D6 selective-reporting risk (both MIC and MBC, or zone with stated endpoint)
Concentration-series availability is recorded as a separate flag (not a quality
domain): a study reporting only endpoint MICs is not lower quality for that reason.
Each domain scored 0 (high concern), 1 (some concern), 2 (low concern).
Overall rating: low if all domains >=1 and total >=8; some if total >=6; else high.
"""
import os
import json

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    df = pd.read_csv(os.path.join(ROOT, "data", "processed", "extraction.csv"))
    chem = pd.read_csv(os.path.join(ROOT, "data", "processed", "chemistry.csv"))
    st = pd.read_csv(os.path.join(ROOT, "data", "processed", "studies.csv"))

    rob_rows = []
    for sid, g in df.groupby("study_id"):
        meta = st[st["pmcid"] == sid].iloc[0] if (st["pmcid"] == sid).any() else None
        title = str(meta["title"]).lower() if meta is not None else ""
        gchem = chem[chem["study_id"] == sid]

        # D1 assay standardization
        std_kw = ["clsi", "eucast", "broth microdilution", "agar dilution",
                  "mic ", "microdilution", "standard", "iso "]
        d1 = 2 if any(k in title for k in std_kw) else 1
        if g["outcome"].isin(["MIC", "MBC"]).any():
            d1 = 2

        # D2 comparator
        d2 = 2 if g["is_artificial"].any() or g["condition"].str.contains(
            "control|vehicle|artificial|simulated", case=False, na=False).any() else 1

        # D3 dispersion reporting
        d3 = 2 if g["sd"].notna().any() else 1

        # D4 concentration-response data availability (flag, not a quality score)
        nconc = g["concentration_pct"].dropna().nunique()
        nser = (g["outcome"] == "series").sum()
        conc_flag = int(nconc >= 3 or nser >= 6)

        # D5 mechanistic perturbation
        mech = g["condition"].str.contains("catalase", case=False, na=False).any() or \
            g["outcome"].isin(["H2O2"]).any() or \
            gchem["chem_param"].isin(["H2O2", "MGO", "aw", "GOx"]).any()
        d5 = 2 if mech else 1

        # D6 reporting completeness
        outs = set(g["outcome"])
        d6 = 2 if ({"MIC", "MBC"} <= outs or "zone" in outs) else 1

        score = d1 + d2 + d3 + d5 + d6
        if min(d1, d2, d3, d5, d6) >= 1 and score >= 8:
            rating = "low"
        elif score >= 6:
            rating = "some"
        else:
            rating = "high"
        rob_rows.append({"study_id": sid, "D1_assay_std": d1, "D2_comparator": d2,
                         "D3_dispersion": d3, "conc_series_available": conc_flag,
                         "D5_mechanism": d5, "D6_reporting": d6,
                         "total": score, "rating": rating})

    rob = pd.DataFrame(rob_rows)
    rob.to_csv(os.path.join(ROOT, "data", "processed", "risk_of_bias.csv"), index=False)
    print(rob["rating"].value_counts())
    print(rob.describe().loc[["mean"]].to_string())

    # ---- data dictionary ----
    dd = """# Data dictionary — extraction.csv

| column | description |
|---|---|
| pmcid | PubMed Central ID of the source article (provenance key) |
| study_id | same as pmcid; grouping key for analyses |
| source | table identifier within the article (t<index>) or curated label |
| honey_label | honey/sample label as printed in the source table |
| organism_label | organism label as printed (abbreviation or binomial) |
| organism | harmonized organism group |
| outcome | measured endpoint: MIC, MBC, zone (mm), zone_area, pct_inhib_biofilm, pct_viable, MIC50, phenol_equiv, series (dilution-series measure), or a chemistry value mislabeled by the source table |
| measure | for outcome=series, the measured quantity (e.g. pH); otherwise equals outcome |
| concentration_pct | honey concentration (% v/v or w/v as reported) at which the observation was made; NA for endpoint-only rows (MIC/MBC already encode a threshold concentration) |
| condition | experimental condition: untreated, catalase, MGO-spike, untreated (retested), etc. |
| value | numeric result in `unit` |
| sd | standard deviation if reported |
| unit | measurement unit (%, mm, mm2, µg/mL, mg/mL, log10 CFU, phenol %) |
| censor | censoring indicator extracted from inequality signs (gt/lt), empty if exact |
| extract_method | auto_A, auto_C, or manual_curated |
| context | header/caption context string used for unit detection |
| is_manuka / is_artificial / is_medical | label-derived honey family flags |
| title, year, doi, pmid, journal | study-level bibliographic metadata |

# chemistry.csv
Honey-level physicochemical rows: chem_param (pH, H2O2, MGO, DHA, aw, TPC, TFC, HMF,
moisture, free_acidity, electrical_cond, sugar_total, Brix, diastase, GOx, color,
phenol_equiv, density, proline), value, unit, plus provenance columns.

# Harmonization notes
- Organism labels were harmonized by a documented regex map (see scripts/08_build_dataset.py).
- MIC/MBC values are in the unit reported; % v/v and % w/v are kept as reported and
  flagged in `unit`; mass units (µg/mL, mg/mL) are not converted to % to avoid
  assuming density. Sensitivity analyses restrict to %-unit rows.
- Rows flagged `extract_method=manual_curated` were extracted by hand from the
  source tables after direct inspection and take precedence over auto rows.
"""
    with open(os.path.join(ROOT, "data", "processed", "data_dictionary.md"), "w",
              encoding="utf-8") as f:
        f.write(dd)
    print("wrote data_dictionary.md and risk_of_bias.csv")


if __name__ == "__main__":
    main()
