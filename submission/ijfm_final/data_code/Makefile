PYTHON ?= python3

# FRI (Food Research International) pipeline — single reproducible entry point
all: search screen fetch extract analyze figures documents qc package

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

extract:
	$(PYTHON) scripts/06_autoextract.py
	$(PYTHON) scripts/07_manual_extraction.py
	$(PYTHON) scripts/08_build_dataset.py
	$(PYTHON) scripts/09_dictionary_rob.py

analyze:
	$(PYTHON) scripts/10_analyze.py
	$(PYTHON) scripts/10b_analyze_fri.py
	$(PYTHON) scripts/18_extraction_bias.py

figures:
	$(PYTHON) scripts/11_figures.py
	$(PYTHON) scripts/12b_references_fri.py

documents:
	$(PYTHON) scripts/13b_manuscript_fri.py
	$(PYTHON) scripts/14b_supplement_fri.py
	$(PYTHON) scripts/15b_fri_extras.py

qc:
	$(PYTHON) scripts/16b_qc_fri.py

package:
	$(PYTHON) scripts/17b_package_fri.py

# Legacy Antibiotics-journal pipeline (kept for provenance)
legacy-docs:
	$(PYTHON) scripts/12_references.py
	$(PYTHON) scripts/13_manuscript.py
	$(PYTHON) scripts/14_supplement.py
	$(PYTHON) scripts/15_cover_letter.py
	$(PYTHON) scripts/16_qc.py
	$(PYTHON) scripts/17_package.py

.PHONY: all search screen fetch extract analyze figures documents qc package legacy-docs
