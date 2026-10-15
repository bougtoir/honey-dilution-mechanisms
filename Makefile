PYTHON ?= python3

# Canonical entry point: regenerates every submission artifact from the
# versioned datasets under data/ (works in the distributed bundle).
all: dirs analyze figures documents package

# Safe rebuild only from the frozen processed datasets:
rebuild: dirs analyze figures documents package

dirs:
	@mkdir -p qc/fri manuscript logs results/tables results/models 	         results/figures submission/jfs_final data/processed data/interim

# Source-acquisition stages (require live PubMed/PMC/Crossref access and
# write raw snapshots under data/raw/; NOT part of `make all`):
acquire: search screen fetch extract

search:
	$(PYTHON) scripts/00_search.py
	$(PYTHON) scripts/00b_citation_mining.py
	$(PYTHON) scripts/00c_repo_search.py

screen:
	$(PYTHON) scripts/01_screen.py
	$(PYTHON) scripts/02_rank_candidates.py
	$(PYTHON) scripts/04_eligibility.py

fetch:
	$(PYTHON) scripts/03b_resolve_pmcid.py
	$(PYTHON) scripts/03_fetch_pmc.py
	$(PYTHON) scripts/05_parse_tables.py

# NOTE: order matters: 21 appends rescued rows to the interim manual
# table (input of 08); 23 cleans the PROCESSED dataset (output of 08).
# `make rebuild` skips this stage entirely and reuses the versioned
# data/processed/ files.
extract:
	$(PYTHON) scripts/06_autoextract.py
	$(PYTHON) scripts/07_manual_extraction.py
	$(PYTHON) scripts/21_gate2_rescue.py
	$(PYTHON) scripts/08_build_dataset.py
	$(PYTHON) scripts/23_provenance_cleanup.py
	$(PYTHON) scripts/27_jfs_cleanup.py
	$(PYTHON) scripts/09_dictionary_rob.py

analyze:
	$(PYTHON) scripts/10_analyze.py
	$(PYTHON) scripts/10b_analyze_fri.py
	$(PYTHON) scripts/18_extraction_bias.py
	$(PYTHON) scripts/24_v4_gates.py
	$(PYTHON) scripts/25_v5_gates.py

figures:
	$(PYTHON) scripts/11_figures.py
	$(PYTHON) scripts/12b_references_fri.py

documents:
	$(PYTHON) scripts/27_jfs_cleanup.py
	$(PYTHON) scripts/28_manuscript_jfs.py
	$(PYTHON) scripts/29_supplement_jfs.py
	$(PYTHON) scripts/30_jfs_extras.py
	$(PYTHON) scripts/31_tables_standalone_jfs.py
	$(PYTHON) scripts/33_three_line_jfs.py

qc:
	$(PYTHON) scripts/16b_qc_fri.py

package:
	$(PYTHON) scripts/32_package_jfs.py

# FRI-era documents (kept for provenance; superseded by JFS documents)
fri-docs:
	$(PYTHON) scripts/13b_manuscript_fri.py
	$(PYTHON) scripts/14b_supplement_fri.py
	$(PYTHON) scripts/15b_fri_extras.py

# Legacy Antibiotics-journal pipeline (kept for provenance)
legacy-docs:
	$(PYTHON) scripts/12_references.py
	$(PYTHON) scripts/13_manuscript.py
	$(PYTHON) scripts/14_supplement.py
	$(PYTHON) scripts/15_cover_letter.py
	$(PYTHON) scripts/16_qc.py
	$(PYTHON) scripts/17_package.py

.PHONY: all search screen fetch extract analyze figures documents qc package fri-docs legacy-docs
