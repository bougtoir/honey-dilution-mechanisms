# Dilution-Dependent Antibacterial Mechanisms of Honey

A systematic review and cross-study quantitative evidence synthesis of published
in vitro data on how honey's antibacterial mechanisms vary with dilution.

## Reproduction

Requires Python 3.12+ with the packages in `requirements.txt`
(`pip install -r requirements.txt`) or the conda spec in `environment.yml`.

Run in order (or `make all`):

| script | purpose |
|---|---|
| script | purpose |
|---|---|
| `scripts/00_search.py` | reproducible searches of PubMed, Europe PMC, Crossref; raw JSON kept in `data/raw/search/` |
| `scripts/00b_citation_mining.py` | backward citation mining via Europe PMC |
| `scripts/00c_repo_search.py` | Dryad/Figshare/Zenodo research-data search |
| `scripts/01_screen.py` | deduplication + stage-1 title/abstract screening |
| `scripts/02_rank_candidates.py` | mechanistic-candidate ranking |
| `scripts/03b_resolve_pmcid.py` | DOI/PMID-to-PMCID resolution for eligible records (run before fetch) |
| `scripts/03_fetch_pmc.py` | PMC open-access full-text (JATS XML) retrieval |
| `scripts/04_eligibility.py` | rule-based eligibility classification |
| `scripts/05_parse_tables.py` | table extraction from XML (colspan expansion, nested tables) |
| `scripts/06_autoextract.py` | rule-based extraction of outcome, chemistry and dilution-series tables |
| `scripts/07_manual_extraction.py` | manually curated mechanistic extractions |
| `scripts/08_build_dataset.py` | harmonized analysis dataset + chemistry + studies tables (dedup + unit-basis preservation) |
| `scripts/09_dictionary_rob.py` | data dictionary + structured risk-of-bias assessment |
| `scripts/10_analyze.py` | core quantitative analyses; writes `results/models/` and `results/tables/` |
| `scripts/10b_analyze_fri.py` | FRI extensions: selection-mechanism characterization, grouped LOSO cross-validation, sensitivity suite |
| `scripts/11_figures.py` | figures (PNG + TIFF, 300 dpi), PRISMA computed live from pipeline outputs |
| `scripts/12b_references_fri.py` | author-year references verified against Crossref (+ context refs) |
| `scripts/13b_manuscript_fri.py` | FRI manuscript DOCX (author-year citations; all numbers from JSON) |
| `scripts/14b_supplement_fri.py` | FRI supplementary DOCX (search appendix, selection, RoB, sensitivity) |
| `scripts/15b_fri_extras.py` | graphical abstract, highlights, FRI cover letter |
| `scripts/16b_qc_fri.py` | FRI QC audits (10 reports in `qc/fri/`) |
| `scripts/17b_package_fri.py` | FRI submission package assembly |

Legacy scripts (`12_references.py`, `13_manuscript.py`, `14_supplement.py`,
`15_cover_letter.py`, `16_qc.py`, `17_package.py`) produced the earlier
journal-formatted package and are retained for provenance.

## Outputs

FRI package (current target: Food Research International):

- `manuscript/manuscript_fri.docx`, `manuscript/supplement_fri.docx`,
  `manuscript/cover_letter_fri.docx`, `manuscript/highlights.docx`
- `results/figures/graphical_abstract.png/.tiff` + 6 main figures (PNG+TIFF)
- `submission/fri_final/Fri_main_manuscript.docx`,
  `submission/fri_final/Fri_submission_package.zip`

Shared data outputs:

- `data/processed/extraction.csv` — observation-level dataset with
  table/row/column provenance and extraction-method flags
- `data/processed/chemistry.csv` — honey-level physicochemical data
- `data/processed/risk_of_bias.csv`, `data/processed/data_dictionary.md`
- `results/models/analysis_results.json`, `analysis_summary.txt`,
  `analysis_summary_fri.txt`
- `results/tables/` — per-analysis result tables
- `qc/fri/` — FRI audit reports
- `submission/` — final ZIP archives

## Evidence scope

All data derive from previously published public sources retrieved through
public APIs. No new experiments were performed. Where planned analyses were not
estimable from public data (e.g., dilution-resolved H2O2 paired with
antibacterial endpoints), the limitation is documented rather than filled with
fabricated values.
