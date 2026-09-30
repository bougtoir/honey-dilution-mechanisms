# Completion Report — Dilution-Dependent Antibacterial Mechanisms of Honey

## Deliverable
- **Target journal:** Antibiotics (MDPI) — systematic review in research-article
  (IMRaD) format, numbered references, PRISMA-style flow.
- **Title:** Dilution-Dependent Antibacterial Mechanisms of Honey: A Systematic
  Review and Cross-Study Quantitative Evidence Synthesis
- **Manuscript:** `manuscript/manuscript.docx` (easy-access copy:
  `submission/manuscript_final.docx`)
- **Submission archive:** `submission/honey_dilution_review_submission.zip`
  (77 files, ~4.8 MB)

## Study and data counts
- Records identified: 4,042 (PubMed, Europe PMC, Crossref + citation mining)
- After deduplication: 2,236 screened; 1,371 excluded at title/abstract
- Assessed for eligibility: 865; included: 412 (388 + 24 flagged)
- Full texts retrieved (PMC OA XML): 376
- Studies with quantitative extraction: 103 (5,026 observations;
  MIC 2,616; zones 1,458; MBC 651)
- Physicochemical rows: 2,635 across 59 studies (pH 400, H2O2 272, MGO 74,
  water activity 74)
- Manually curated mechanistic rows: 545 across 11 studies

## Analyses completed
- A1 concentration-response: 10/10 extractable activity series positive
  (median Spearman rho = 1.00); pH dilution ladder rho = -1.00 (n = 4)
- A2 natural vs artificial honey: 21 pairs; zones +0.6 mm (p = 0.002);
  MIC ratio 0.81
- A3 chemistry-outcome associations (18 studies, 687 joined rows): MGO-MIC
  rho = -0.52 (n = 116); moisture-MIC rho = +0.17; pH-zone rho = -0.52;
  H2O2-MIC rho = +0.46 (confounded, interpreted cautiously)
- A4 catalase residual: median 92% activity retained (13 pairs, 2 studies)
- A5 chemistry vs label: chemistry R2 = 0.30 vs label R2 = 0.00 (n = 112)
- A6 organism heterogeneity: Kruskal-Wallis p = 2.2e-27; Gram-positive <
  Gram-negative MICs; manuka vs other 15% vs 18% (p = 0.065, NS)
- Sensitivity: low-RoB subset (6 studies, 185 rows) consistent

## Traceable findings
All quantitative claims trace to `results/models/analysis_results.json` and
`results/tables/*.csv`; every data row carries PMCID + table/row/column
provenance. Consistency audit: 8/8 manuscript claims verified.

## Limitations (documented in manuscript)
- Dilution-series data rare (8/103 studies); catalase pairs from 2 studies;
  no extracted study pairs H2O2 dilution ladder with antibacterial endpoints
  (RQ3 qualitative only).
- Cross-study correlations confounded; causal language reserved for
  perturbation contrasts.
- Extracted subset (103) is open-access subset of 412 eligible studies.
- Rule-based RoB is a reporting-quality proxy; no prospective registration.
- Screening/extraction automated with manual verification of mechanistic
  tables; residual extraction error possible.

## Reproducibility
- `make all` runs the full pipeline; `requirements.txt`/`environment.yml` pin
  dependencies; raw search JSON retained under `data/raw/search/`.
- Reproducibility file check: all required outputs present (qc report).

## QC status (qc/)
- fabrication_audit.txt — PASS (100% provenance, all source XML present)
- consistency_audit.txt — PASS (8/8)
- formatting_audit.txt — PASS (no LaTeX tokens, no Japanese text; non-ASCII
  limited to author-name accents in references)
- ip_firewall_scan.txt — PASS (one hit inside a cited reference title only)
- reproducibility_check.txt — PASS (all files present)
- reviewer_assessment.txt — honest strengths/weaknesses review

## Exact paths
- ZIP: `C:\Users\bougt\devin\honey-dilution-review\submission\honey_dilution_review_submission.zip`
- Manuscript: `C:\Users\bougt\devin\honey-dilution-review\manuscript\manuscript.docx`
- Easy-access copy: `C:\Users\bougt\devin\honey-dilution-review\submission\manuscript_final.docx`
- Supplement: `manuscript\supplement.docx`; Cover letter: `manuscript\cover_letter.docx`
