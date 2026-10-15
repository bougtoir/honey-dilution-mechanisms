# Data dictionary — extraction.csv

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
