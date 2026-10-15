"""Generate the JFS supplementary materials DOCX:
S1 search strategy, S2 eligibility rules, S3 extraction/provenance,
S4 extraction-selection characterization, S5 RoB framework + ratings,
S6 extended analysis/sensitivity tables.
"""
import json
import os

import pandas as pd
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIGDIR = os.path.join(ROOT, "results", "figures")
OUT = os.path.join(ROOT, "manuscript")
os.makedirs(OUT, exist_ok=True)

R = json.load(open(os.path.join(ROOT, "results", "models",
                                "analysis_results.json")))
COUNTS = json.load(open(os.path.join(ROOT, "logs", "prisma_counts.json")))
LOG = pd.read_csv(os.path.join(ROOT, "logs", "search_log.csv"))
ELIG = pd.read_csv(os.path.join(ROOT, "data", "interim", "eligible.csv"))
ROB = pd.read_csv(os.path.join(ROOT, "data", "processed", "risk_of_bias.csv"))
EXT = pd.read_csv(os.path.join(ROOT, "data", "processed", "extraction.csv"))
ST = pd.read_csv(os.path.join(ROOT, "data", "processed", "studies.csv"))

def pstr(p):
    if p is None or (isinstance(p, float) and p != p):
        return "not estimable"
    if p < 0.001:
        return "< 0.001"
    return f"= {p:.3f}" if p < 0.1 else f"= {p:.2f}"


def rho_str(x):
    return f"{x:+.2f}".replace("+", "")


A3 = {c["param"] + "|" + c["outcome"]: c for c in R["A3_correlations"]}


doc = Document()
st = doc.styles["Normal"]
st.font.name = "Times New Roman"
st.font.size = Pt(10)


def h(t, lvl=1):
    return doc.add_heading(t, level=lvl)


def para(t):
    return doc.add_paragraph(t)


def table(headers, rows, title=None):
    if title:
        p = doc.add_paragraph()
        r = p.add_run(title)
        r.bold = True
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Light Grid Accent 1"
    for j, x in enumerate(headers):
        t.rows[0].cells[j].text = x
    for row in rows:
        c = t.add_row().cells
        for j, v in enumerate(row):
            c[j].text = str(v)
    doc.add_paragraph()
    return t


h("Supplementary material", 1)
para("Dilution-dependent antibacterial activity of honey: a "
     "cross-study quantitative reanalysis of published experimental data")
para("For submission to Journal of Food Science.")
doc.add_paragraph()

# ---- S1 search strategy ----
h("S1. Search strategy and yields", 2)
para("All searches were executed programmatically on the dates shown; raw "
     "API responses are retained in the repository archive. Europe PMC "
     "queries were capped at 500 retrieved records per query and Crossref "
     "at 100, ranked by relevance.")
table(["Database", "Query", "Date", "Hits", "Retrieved"],
      [(r["db"], r["query"], r["date"], r["hits"], r["retrieved"])
       for _, r in LOG.iterrows()],
      title="Table S1. Full search queries, dates and yields.")

# ---- S2 eligibility rules ----
h("S2. Eligibility decision rules", 2)
para("A deterministic rule-based classifier assigned each screened record "
     "to include / exclude / review_flag using title-and-abstract patterns. "
     "The complete rules are implemented in scripts/04_eligibility.py in "
     "the released code. Decision counts:")
vc = ELIG["elig_reason"].value_counts()
table(["Decision rule outcome", "n records"],
      [(k, v) for k, v in vc.items()],
      title="Table S2. Eligibility decisions by rule outcome.")

# ---- S3 extraction & provenance ----
h("S3. Extraction and provenance", 2)
para(
    "Each extracted row carries study_id, source table identifier, row and "
    "column position, raw cell text, normalized outcome, unit, unit basis "
    "and an auto/manual flag. Manually curated mechanistic rows "
    f"(n = {(EXT['source'] == 'manual').sum() if 'source' in EXT.columns else 'flagged'}) "
    "take precedence over automatically extracted rows for the same cell. "
    "Outcome categories in the harmonized dataset:")
table(["Outcome", "n rows"], [(k, v) for k, v in
      EXT["outcome"].value_counts().items()],
      title="Table S3. Harmonized outcome categories.")
para("Reported concentration bases were preserved and analyzed separately:")
table(["Unit basis", "n rows"], [(k, v) for k, v in
      EXT["unit_basis"].value_counts().items()],
      title="Table S4. Concentration unit bases (not pooled).")

# ---- S4 selection mechanism ----
h("S4. Extraction-selection characterization", 2)
SEL = R["selection"]
para(
    f"Of {SEL['eligible']} eligible studies, {SEL['with_pmcid']} had a "
    f"resolvable PubMed Central identifier, {SEL['xml_available']} had an "
    f"open-access JATS XML full text, and {SEL['extracted']} yielded "
    f"machine-extractable outcome data. Extracted studies were more recent "
    f"(median year {SEL['year_median_extracted']:.0f} vs. "
    f"{SEL['year_median_nonextracted']:.0f}; Mann-Whitney p = "
    f"{SEL['year_mwu_p']:.2e}). The most frequent journals among "
    "non-extracted eligible studies:")
table(["Journal (non-extracted eligible)", "n studies"],
      [(k, v) for k, v in SEL["top_journals_nonextracted"].items()],
      title="Table S5. Journals most represented among non-extracted "
            "eligible studies.")
para(
    "Reasons for non-extraction fall into three classes: (i) no resolvable "
    "PMC identifier (typically journals not deposited in PMC or "
    "closed-access publisher versions); (ii) PMC identifier present but no "
    "open-access full text; (iii) full text retrieved but containing no "
    "outcome table matching the documented parsing layouts (data reported "
    "only in figures, in prose, or in non-tabular supplements). Counts are "
    "reconciled in Fig. 1 of the main text.")

# ---- S5 risk of bias ----
h("S5. Reporting-quality / risk-of-bias framework", 2)
para(
    "Five domains, each scored 0-2: D1 assay standardization; D2 comparator "
    "quality; D3 dispersion reporting; D5 mechanistic perturbation; D6 "
    "reporting completeness. Concentration-series availability is an "
    "availability flag, not a quality score. Ratings: low (total >= 8), "
    "some (5-7), high (<= 4).")
table(["study_id"] + [c for c in ROB.columns if c != "study_id"],
      [tuple(r) for _, r in ROB.iterrows()],
      title="Table S6. Per-study reporting-quality scores.")

# ---- S6 extended analyses ----
h("S6. Extended analyses and sensitivity results", 2)
para("Spearman associations between honey-level physicochemical parameters "
     "and antibacterial outcomes (joined on study and normalized sample "
     "label):")
table(["Parameter", "Outcome", "n", "n studies", "rho", "p"],
      [(c["param"], c["outcome"], c["n"], c["n_studies"],
        f"{c['spearman_rho']:.3f}", f"{c['p']:.3g}")
       for c in R["A3_correlations"]],
      title="Table S7. Chemistry-outcome Spearman correlations.")
para("Leave-one-study-out cross-validation of outcome models "
     "(log10(MIC)):")
CV = R["chem_vs_label_cv"]
table(["Model", "Predictors", "CV R2", "CV RMSE"],
      [("Null", "-", f"{CV['r2_cv_null']:.3f}", f"{CV['rmse_cv_null']:.3f}"),
       ("Chemistry", ", ".join(CV["predictors"]),
        f"{CV['r2_cv_chem']:.3f}", f"{CV['rmse_cv_chem']:.3f}"),
       ("Label only", "manuka/medical-grade flag",
        f"{CV['r2_cv_label']:.3f}", f"{CV['rmse_cv_label']:.3f}"),
       ("Combined", "chemistry + label",
        f"{CV['r2_cv_both']:.3f}", f"{CV['rmse_cv_both']:.3f}")],
      title=f"Table S8. Leave-one-study-out cross-validation "
            f"(n = {CV['n']}, {CV['n_studies']} studies). Negative R2 "
            "indicates worse-than-null out-of-study performance.")
para("Sensitivity analyses:")
SEN = R["sensitivity"]
table(["Subset", "n rows", "n studies", "Median MIC (%)"],
      [("Low reporting-concern studies", SEN["low_rob"]["n"],
        SEN["low_rob"]["studies"], SEN["low_rob"]["median"]),
       ("Manuka-labelled excluded", SEN["manuka_excluded"]["n"], "-",
        SEN["manuka_excluded"]["median"]),
       ("Manuka-labelled only", SEN["manuka_only"]["n"], "-",
        SEN["manuka_only"]["median"]),
       ("% w/v basis only", SEN["w_v_basis_only"]["n"], "-",
        SEN["w_v_basis_only"]["median"]),
       ("% v/v basis only", SEN["v_v_basis_only"]["n"], "-",
        SEN["v_v_basis_only"]["median"]),
       ("Studies measuring water activity", SEN["aw_measured_studies"]["n"],
        SEN["aw_measured_studies"]["studies"],
        SEN["aw_measured_studies"]["median"]),
       ("Studies measuring H2O2", SEN["h2o2_measured_studies"]["n"],
        SEN["h2o2_measured_studies"]["studies"],
        SEN["h2o2_measured_studies"]["median"]),
       ("Peer-reviewed only", SEN["peer_reviewed_only"]["n"], "-",
        SEN["peer_reviewed_only"]["median"])],
      title="Table S9. Sensitivity analyses on MIC subsets.")
para(
    f"Leave-one-study-out resampling of the manuka-vs-other MIC contrast "
    f"returned non-significant results (p > 0.05) in "
    f"{SEN['loo_manuka_ns_frac']:.0%} of iterations.")
para("Natural-vs-artificial pairs by study (direction-normalized potency "
     "ratio; >1 indicates greater natural-honey activity):")
table(["Study", "Outcome", "n pairs", "Median potency ratio"],
      [(r["study_id"], r["outcome"], r["n"],
        f"{r['med_ratio']:.2f}" if pd.notna(r["med_ratio"]) else "n/a")
       for r in R["artificial_by_study"]],
      title="Table S10. Natural-vs-artificial potency ratios by study.")

# ---- S7 included studies corpus ----
h("S7. Studies included in the quantitative synthesis", 2)
REXF = pd.read_csv(os.path.join(ROOT, "references", "references_fri.csv"))
para(
    f"Full author-year references for the {len(REXF)} studies from which "
    "quantitative data were extracted. PMCID identifiers are retained in "
    "the released dataset (data/extraction.csv) for row-level provenance.")
table(["#", "Reference"],
      [(i + 1, r["ref"]) for i, r in REXF.iterrows()],
      title="Table S11. References of studies included in the quantitative "
            "synthesis (alphabetical).")



# ---- S8 study flow and paired-contrast summary ----
h("S8. Study selection flow and paired-contrast summary", 2)
_p = doc.add_paragraph()
_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
_p.add_run().add_picture(os.path.join(FIGDIR, "fig1_prisma.png"),
                        width=Inches(6.3))
_cap = doc.add_paragraph()
_cr = _cap.add_run("Supplementary Fig. S1. ")
_cr.bold = True
_cap.add_run("PRISMA 2020-style flow of study identification, screening, "
             "eligibility and quantitative extraction.")
para("")
A2V = R["A2_v5"]
A1, A4 = R["A1"], R["A4"]
mgo = A3.get("MGO|MIC", {})
phzone = A3.get("pH|zone", {})
PAIRS = pd.read_csv(os.path.join(ROOT, "results", "tables",
                               "natural_vs_artificial_pairs.csv"))
table(["Contrast", "n pairs/obs", "n studies", "Effect", "p value"],
      [
       ("Natural vs artificial honey, MIC potency ratio "
        "(study level)",
        str(A2V["MIC"]["n_pairs"]), str(A2V["MIC"]["n_studies"]),
        f"median ratio {A2V['MIC']['median_ratio']:.2f}; all study "
        "medians > 1",
        pstr(A2V["MIC"]["wilcoxon_p_study"]).lstrip("= ")),
       ("Natural vs artificial honey, zone difference (mm)",
        str(A2V["zone"]["n_pairs"]), str(A2V["zone"]["n_studies"]),
        f"median +{A2V['zone']['median_diff_mm']:.1f} mm; positive in "
        "both studies", "-"),
       ("Catalase residual activity", str(A4["n_pairs"]),
        str(len(A4["studies"])),
        f"median {A4['median_residual_frac']:.0%} retained", "-"),
       ("Activity vs concentration (series)",
        str(A1["n_activity_series"]), str(R["conc_response"]["n_studies"]),
        f"{A1['positive']}/{A1['n_activity_series']} positive; "
        f"median rho = {A1['median_rho']:.2f}", "-"),
       ("MGO vs MIC (within-study)", str(mgo.get("n", 0)),
        str(mgo.get("n_studies", 0)),
        f"rho = {rho_str(mgo.get('spearman_rho', 0))}",
        pstr(mgo.get("p")).lstrip("= ")),
       ("pH vs inhibition zone", str(phzone.get("n", 0)),
        str(phzone.get("n_studies", 0)),
        f"rho = {rho_str(phzone.get('spearman_rho', 0))}",
        pstr(phzone.get("p")).lstrip("= ")),
      ],
      title="Table S12. Paired evidence for mechanistic contrasts. "
            "Potency ratio > 1 indicates greater natural-honey activity "
            "(zone: natural/artificial; MIC: artificial/natural). MGO, "
            "methylglyoxal; MIC, minimum inhibitory concentration.")

para("")

doc.save(os.path.join(OUT, "supplement_jfs.docx"))
print("wrote supplement_jfs.docx")
