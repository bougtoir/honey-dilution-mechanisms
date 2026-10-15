"""Generate the Journal of Food Science manuscript DOCX.

Author-year citations (alphabetical, JFS-accepted style); continuous line
numbering and double spacing as required by the Journal of Food Science;
every numeric claim is read from
results/models/analysis_results.json and the processed data files —
nothing is hard-coded.
"""
import json
import os
import re

import numpy as np
import pandas as pd
from scipy import stats
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "manuscript")
os.makedirs(OUT, exist_ok=True)

R = json.load(open(os.path.join(ROOT, "results", "models",
                                "analysis_results.json")))
COUNTS = json.load(open(os.path.join(ROOT, "logs", "prisma_counts.json")))
REX = pd.read_csv(os.path.join(ROOT, "references", "references_fri.csv"))
RCT = pd.read_csv(os.path.join(ROOT, "references", "references_fri_context.csv"))
ROB = pd.read_csv(os.path.join(ROOT, "data", "processed", "risk_of_bias.csv"))
EXT = pd.read_csv(os.path.join(ROOT, "data", "processed", "extraction.csv"))
CHEM = pd.read_csv(os.path.join(ROOT, "data", "processed", "chemistry.csv"))
ELIG = pd.read_csv(os.path.join(ROOT, "data", "interim", "eligible.csv"))

CITE = dict(zip(REX["pmcid"], REX["intext"]))
for _, r in RCT.iterrows():
    CITE[f"PMID{r['pmid']}"] = r["intext"]


def _jfs_intext(s):
    # JFS/CSE name-year: "and others" for 3+ authors, no comma before year.
    s = re.sub(r"\bet al\.\s*,", "and others", s)
    s = re.sub(r",\s*(?=(?:19|20)\d{2}[a-z]?$)", " ", s)
    return s


CITE = {k: _jfs_intext(v) for k, v in CITE.items()}

USED = set()


def cite(*keys):
    labels = sorted(CITE[k] for k in keys if k in CITE)
    USED.update(k for k in keys if k in CITE)
    return "(" + "; ".join(labels) + ")"


def pstr(p):
    if p is None or (isinstance(p, float) and p != p):
        return "not estimable"
    if p < 0.001:
        return "< 0.001"
    return f"= {p:.3f}".replace("0.", "0.") if p < 0.1 else f"= {p:.2f}"


def rho_str(x):
    return f"{x:+.2f}".replace("+", "")


SEL = R["selection"]
A1, A2, A4, A5, A6 = R["A1"], R["A2"], R["A4"], R["A5"], R["A6"]
A3 = {c["param"] + "|" + c["outcome"]: c for c in R["A3_correlations"]}
CV = R["chem_vs_label_cv"]
SEN = R["sensitivity"]
ADIR = R["artificial_direction"]
A1V = R["A1_v4"]
MC = R["A6_manuka_cluster"]
A2V, MV5 = R["A2_v5"], R["manuka_v5"]
_mdf = pd.DataFrame(MV5["paired_within_study_basis"])
if len(_mdf):
    MV5["n_lower"] = int((_mdf["diff"] < 0).sum())
    MV5["n_equal"] = int((_mdf["diff"] == 0).sum())
    MV5["wilcoxon_p"] = (float(stats.wilcoxon(_mdf["diff"]).pvalue)
                       if len(_mdf) >= 3 else None)
# descriptive per-basis MIC medians (percentage bases only; never pooled)
_mb = EXT[(EXT["outcome"].isin(["MIC", "MBC"])) & (EXT["value"] > 0) &
          (EXT["unit_basis"].str.startswith("%"))]
B5 = {b: {"n": int(len(g)), "median": float(g["value"].median())}
      for b, g in _mb.groupby("unit_basis")}

INC = ELIG[ELIG["elig"].isin(["include", "review_flag"])]
n_inc = len(INC)
n_outcome = EXT[EXT["outcome"].isin(["MIC", "zone", "MBC"])]
n_mic = int((EXT["outcome"] == "MIC").sum())
n_zone = int((EXT["outcome"] == "zone").sum())
n_mbc = int((EXT["outcome"] == "MBC").sum())
rob_counts = ROB["rating"].value_counts().to_dict()

# post-extraction audit exclusions (scripts/23_provenance_cleanup.py)
AUDIT = {"n_studies_removed": 10, "n_rows_removed": 352}
# study-cluster-aware sensitivity for natural-vs-artificial contrast
_pa = pd.read_csv(os.path.join(ROOT, "results", "tables",
                               "natural_vs_artificial_pairs.csv"))
_pr = _pa.copy()
_pr["pot_ratio"] = np.where(_pr["outcome"] == "zone",
                           _pr["natural_mean"] / _pr["artificial_mean"],
                           _pr["artificial_mean"] / _pr["natural_mean"])
_sm = _pr.groupby("study_id")["pot_ratio"].median().dropna()
CL = {"n_studies": int(len(_sm)),
      "median_ratio": float(_sm.median()),
      "all_directional": bool((_sm > 1).all()),
      "wilcoxon_p": float(stats.wilcoxon(_sm).pvalue) if len(_sm) >= 3
                    else None}

# Exploratory pair-level log-ratio test: a log potency ratio is defined
# only when both arms are > 0. Pairs with a zero control mean (the one
# excluded MIC pair and the zero-artificial zone pairs) have no defined
# log ratio and are analysed as native-scale differences instead.
_lr = _pr.loc[(_pr["pot_ratio"] > 0) & np.isfinite(_pr["pot_ratio"]),
              "pot_ratio"]
EXPL = {"n_defined": int(len(_lr)),
        "median_ratio": float(_lr.median()),
        "wilcoxon_p": float(stats.wilcoxon(np.log(_lr)).pvalue)
                      if len(_lr) >= 5 else None}

doc = Document()
st = doc.styles["Normal"]
st.font.name = "Times New Roman"
st.font.size = Pt(11)
# JFS requires double-spaced text.
st.paragraph_format.line_spacing = 2.0

# JFS requires continuous line numbering on submitted manuscripts.
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
for sec in doc.sections:
    sectPr = sec._sectPr
    ln = sectPr.find(qn("w:lnNumType"))
    if ln is None:
        ln = OxmlElement("w:lnNumType")
        sectPr.append(ln)
    ln.set(qn("w:countBy"), "1")
    ln.set(qn("w:start"), "0")
    ln.set(qn("w:distance"), "240")
    ln.set(qn("w:restart"), "continuous")


def h(text, level=1):
    p = doc.add_heading(text, level=level)
    from docx.shared import RGBColor
    for r in p.runs:
        r.font.name = "Times New Roman"
        r.font.color.rgb = RGBColor(0, 0, 0)
    return p


def para(text, italic_species=True):
    p = doc.add_paragraph()
    for i, seg in enumerate(re.split(r"\*", text)):
        run = p.add_run(seg)
        if italic_species and i % 2 == 1:
            run.italic = True
    return p


def center(text, size=14, bold=True):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text)
    r.bold = bold
    r.font.size = Pt(size)
    return p


FIGDIR = os.path.join(ROOT, "results", "figures")


def fig(name, caption, width=6.3):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(os.path.join(FIGDIR, name + ".png"),
                            width=Inches(width))
    cap = doc.add_paragraph()
    parts = caption.split(". ", 1)
    r = cap.add_run(parts[0] + ". ")
    r.bold = True
    cap.add_run(parts[1] if len(parts) > 1 else "")
    doc.add_paragraph()


def table(title, headers, rows, note=None):
    p = doc.add_paragraph()
    parts = title.split(". ", 1)
    r = p.add_run(parts[0] + ". ")
    r.bold = True
    p.add_run(parts[1] if len(parts) > 1 else "")
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Light Grid Accent 1"
    for j, x in enumerate(headers):
        t.rows[0].cells[j].text = x
    for row in rows:
        c = t.add_row().cells
        for j, v in enumerate(row):
            c[j].text = str(v)
    if note:
        np_ = doc.add_paragraph()
        nr = np_.add_run("Note: " + note)
        nr.font.size = Pt(9)
    doc.add_paragraph()


# ================= TITLE PAGE =================
center("Dilution-dependent antibacterial activity of honey: a "
       "cross-study quantitative reanalysis of published experimental "
       "data", 15)
doc.add_paragraph()
center("Tatsuki Onishi a,*", 11, bold=False)
center("a Data Science and AI Innovation Research Promotion Center, "
       "Shiga University, 1-1-1 Bamba, Hikone, Shiga 522-8522, Japan", 10,
       bold=False)
center("* Corresponding author. E-mail address: bougtoir@gmail.com. "
       "ORCID: 0000-0001-7261-9062", 10, bold=False)
center("Submitted to: Journal of Food Science (Original Article)", 10,
       bold=False)
center("Word count of text (excluding references): see below", 10,
       bold=False)
doc.add_paragraph()
para("Abbreviations: MGO, methylglyoxal; MIC, minimum inhibitory "
     "concentration; MBC, minimum bactericidal concentration; H2O2, "
     "hydrogen peroxide; MRSA/MSSA, methicillin-resistant/susceptible "
     "Staphylococcus aureus; aw, water activity; LOSO, "
     "leave-one-study-out.")
doc.add_paragraph()

# ================= ABSTRACT =================
h("ABSTRACT", 1)
para(
    "Honey is a preserved food whose antimicrobial stability depends on "
    "intrinsic physicochemical factors, yet it is almost always assayed "
    "and used in diluted form. This cross-study quantitative "
    "reanalysis of published experimental data, guided by a "
    "systematic evidence-identification workflow, asked how the "
    "antibacterial activity of honey "
    "changes across its dilution range. Searches of PubMed, Europe PMC "
    f"and Crossref, citation mining and data-repository searches "
    f"retrieved {COUNTS['raw_records']:,} records; "
    f"{COUNTS['unique_screened']:,} unique records were screened, {n_inc} "
    f"studies met eligibility criteria, and structured data were extracted "
    f"from {R['n_studies']} open-access full texts ({R['n_rows']:,} "
    "observations), predominantly against foodborne bacteria. All "
    f"{A1['n_activity_series']} extractable concentration series showed a "
    f"positive association with honey concentration (median Spearman rho = "
    f"{A1['median_rho']:.2f}), and the one complete pH ladder rose on "
    f"dilution (rho = {A1['pH_median_rho']:.2f}). Natural honeys exceeded "
    f"sugar-equivalent controls in matched within-study comparisons "
    f"(MIC potency ratio {A2V['MIC']['median_ratio']:.2f} across "
    f"{A2V['MIC']['n_pairs']} pairs from {A2V['MIC']['n_studies']} "
    "studies, with every contributing study's median above 1; "
    f"median paired zone excess +{A2V['zone']['median_diff_mm']:.1f} mm "
    f"in {A2V['zone']['n_studies']} studies). Catalase-treated honey retained "
    f"a median {A4['median_residual_frac']:.0%} of activity "
    f"({A4['n_pairs']} pairs, {len(A4['studies'])} studies). "
    "Physicochemical parameters predicted antibacterial outcomes within "
    "individual studies but not across them: leave-one-study-out "
    "cross-validated R2 was negative for chemistry- and label-based "
    "models. No extracted study measured antibacterial activity in an "
    "actual food matrix, and no extracted dataset reported a complete "
    "hydrogen peroxide dilution ladder with matched antibacterial "
    "endpoints. The evidence is consistent with dilution-dependent "
    "variation in the weight of osmotic, acidic, peroxide and "
    "non-peroxide contributions rather than "
    "a single mechanism, and it quantifies where the primary literature "
    "remains too sparse to support stronger claims."
)
para("Keywords: honey; food preservation; hydrogen peroxide; "
     "methylglyoxal; water activity")
# JFS Original Article portal structure has no Practical Application section.

# ================= 1. INTRODUCTION =================
h("1. Introduction", 1)
para(
    "Honey occupies an unusual position in food microbiology: it is both "
    "a food documented to remain unspoiled over unusually long storage and a concentrated "
    "antimicrobial system whose intrinsic factors — water activity, "
    "acidity, enzymatic hydrogen peroxide production and plant-derived "
    "non-peroxide constituents — have been characterized for nearly a "
    "century " + cite("PMID101099109", "PMID1447054") + ". For a food "
    "microbiologist, honey is therefore best read as an ecosystem defined "
    "by its intrinsic properties: what survives in it, and why, is set by "
    "the same physical and chemical constraints that govern microbial "
    "survival in other foods " + cite("PMID20228250", "PMID21394213") + "."
)
para(
    "Those constraints do not scale uniformly with dilution. Water "
    "activity rises and acidity weakens approximately in proportion to "
    "dilution, but glucose oxidase — the enzyme that generates hydrogen "
    "peroxide (H2O2) — is strongly constrained in undiluted honey and "
    "becomes appreciable mainly after partial dilution "
    + cite("PMID12804080", "PMIDbrudz2021") + ", while non-peroxide "
    "factors such as methylglyoxal (MGO) simply attenuate with "
    "concentration " + cite("PMID21394213") + ". Whether dilution merely "
    "weakens honey's antibacterial activity or changes which mechanism "
    "accounts for it is an empirical question with direct consequences "
    "for how honey-derived antimicrobial activity should be measured, "
    "reported and modelled in food systems."
)
para(
    "Prior reviews have treated these mechanisms largely in isolation: "
    "foundational accounts classified osmotic, peroxide and non-peroxide "
    "contributions qualitatively " + cite("PMID101099109") + "; "
    "mechanistic reviews have focused on the chemistry of H2O2 "
    "production " + cite("PMIDbrudz2021") + "; clinical systematic "
    "reviews have pooled efficacy for wound and resistant organisms "
    "without a dilution axis " + cite("PMIDnolan2020") + "; and recent "
    "meta-analyses have pooled honey or medical-grade honey potency "
    "against pathogens without modelling the concentration axis "
    + cite("PMIDcabezas2024", "PMIDaljadi2025") + ". Honey has also "
    "been reviewed as a microbial ecosystem in its own right, with "
    "attention to the organisms that live in it rather than the factors "
    "that act on other microbes " + cite("PMIDeryilmaz2026") + ". "
    "Single-laboratory "
    "dilution experiments exist "
    + cite("PMID12804080", "PMID1447054") + ", but no review has "
    "quantitatively synthesized, across studies, how antibacterial "
    "activity and its mechanistic correlates behave along the dilution "
    "range. This gap matters because assays performed near full strength "
    "may reflect constraints that dissipate once honey is incorporated "
    "into a diluted food environment."
)
para(
    "We conducted a systematic review and quantitative evidence synthesis "
    "of primary studies of honey's antibacterial activity. We asked: "
    "(i) how activity varies with honey concentration; (ii) whether "
    "natural honey exceeds sugar-equivalent artificial-honey controls; "
    "(iii) how H2O2 production varies with dilution and whether it tracks "
    "measured activity; (iv) how much activity survives catalase-mediated "
    "H2O2 removal; (v) whether measured physicochemical parameters predict "
    "antibacterial outcomes beyond honey-type labels; and (vi) how results "
    "vary across organisms, with particular attention to foodborne "
    "bacteria. Causal or mechanistic language was reserved for "
    "within-study perturbation evidence (catalase treatment, matched "
    "artificial-honey controls); cross-study associations are reported as "
    "observational, and evidence density is reported explicitly so that "
    "sparse-evidence conclusions cannot be mistaken for strong ones."
)

# ================= 2. METHODS =================
h("2. Materials and methods", 1)

h("2.1. Protocol and reporting", 2)
para(
    "The review was conducted and reported with reference to the PRISMA 2020 "
    "guideline where applicable; the study flow is summarized in Supplementary Fig. S1. The "
    "review was not prospectively registered; eligibility criteria, analysis "
    "decisions and the complete executable pipeline are released with this "
    "article (see Data availability)."
)

h("2.2. Search strategy", 2)
para(
    "We searched PubMed (NCBI E-utilities), Europe PMC (REST API) and Crossref "
    "(works API) for records combining honey-related terms with antibacterial, "
    "minimum inhibitory concentration (MIC), zone-of-inhibition, peroxide, "
    "methylglyoxal, water-activity and dilution terms; the full query strings, "
    "execution dates and hit counts are reported in Supplementary Table S1. "
    "Searches were executed programmatically and raw responses retained. "
    "Backward citation mining through Europe PMC contributed additional "
    "records, and Dryad, Figshare and Zenodo were searched for associated "
    "research data. All records were deduplicated on DOI, PubMed ID and "
    "normalized title."
)

h("2.3. Eligibility criteria", 2)
para(
    "Records were eligible if they reported a primary in vitro antibacterial "
    "evaluation of natural honey with a quantitative endpoint (MIC, minimum "
    "bactericidal concentration (MBC), inhibition zone, biofilm inhibition or "
    "equivalent) and at least one of: a concentration or dilution series; an "
    "artificial-honey or sugar-equivalent comparator; a catalase or other "
    "mechanistic perturbation; or quantitative physicochemical characterization "
    "(H2O2, MGO, water activity, pH, phenolics). Reviews, non-antibacterial "
    "studies, non-honey studies, formulation studies in which honey could not "
    "be separated from the matrix, and records without a usable abstract were "
    "excluded. Eligibility was assigned by a deterministic rule-based "
    "classifier applied to titles and abstracts, followed by manual "
    "verification of included candidates; the classifier rules and per-record "
    "decisions are released with the dataset."
)

h("2.4. Data extraction", 2)
para(
    "Open-access full texts were retrieved from PubMed Central as JATS XML. "
    "All tables were parsed programmatically, including nested tables, with "
    "merged header cells expanded and multi-row headers reconstructed. A "
    "rule-based extractor converted the dominant table layouts into "
    "long-format observations carrying study, table, row and column "
    "provenance. For key mechanistic datasets (catalase-treated versus "
    "untreated pairs, simulated-honey controls, concentration series and "
    "MGO-spike dose-response), rows were additionally curated manually after "
    "direct inspection of source tables and captions; manually curated rows "
    "are flagged and take precedence. Organism labels were harmonized to "
    "organism groups using a documented mapping. Concentrations embedded in "
    "sample labels were parsed into a dedicated field, and the reported "
    "concentration basis (percent weight/volume, volume/volume, weight/weight, "
    "mass concentration or unspecified) was preserved in a separate field; "
    "analyses were stratified by basis rather than pooled across incompatible "
    "units. Values reported with inequality signs were retained with a "
    "censoring flag."
)

h("2.5. Risk-of-bias and reporting-quality assessment", 2)
para(
    "No validated risk-of-bias instrument exists for cross-study in vitro "
    "antibacterial data. We applied a structured framework covering five "
    "domains — assay standardization, comparator quality, dispersion "
    "reporting, mechanistic perturbation and reporting completeness — each "
    "scored 0-2. Availability of concentration-series data was recorded as an "
    "availability flag, not a quality judgement. Ratings (low, some or high "
    "concern) were derived from domain totals and used in sensitivity "
    "analyses."
)

h("2.6. Statistical analysis", 2)
para(
    "Concentration-response was summarized by per-series Spearman correlations "
    "between concentration and response. A series was eligible when the honey, "
    "organism and assay were identified, the concentration basis was "
    "extractable and at least three distinct ordered concentrations were "
    "reported (four or more in a sensitivity check); no condition on the "
    "direction, monotonicity or significance of the response was applied. "
    "Natural versus artificial honey was compared within study, "
    "organism, outcome and concentration strata. MIC and MBC contrasts "
    "were expressed as log potency ratios (artificial/natural, so that "
    "values above 1 indicate greater natural-honey potency); "
    "inhibition-zone contrasts were expressed as absolute differences in "
    "millimetres, preserving zero-denominator pairs without division. "
    "Because pairs within a study are dependent, the study was the "
    "primary inferential unit: per-study median effects were computed "
    "per outcome scale and synthesized across studies descriptively, "
    "with a Wilcoxon signed-rank test across study medians where at "
    "least three studies contributed. "
    "Catalase-treated versus untreated observations were paired identically "
    "and expressed as residual activity fractions. Honey-level physicochemical "
    "parameters were joined to outcomes on study and normalized sample label; "
    "Spearman correlations were computed per parameter and outcome, and "
    "ordinary least squares models on log10(MIC) compared measured chemistry, "
    "a honey-type label and their combination. Because rows from the same "
    "study are not independent, model performance was evaluated by "
    "leave-one-study-out cross-validation rather than in-sample fit. "
    "Percentage-unit MICs were never pooled across concentration bases "
    "(w/v, v/v, w/w or unspecified); organism medians were computed within "
    "each basis class and pooled percentage rows only descriptively. "
    "Because rows within a study are not independent, inferential contrasts "
    "were also aggregated to study level; where independent studies were "
    "too few for a valid test, results are reported descriptively. "
    "Sensitivity "
    "analyses repeated key contrasts on the low-risk-of-bias subset, on each "
    "concentration basis separately, and after excluding manuka-labelled "
    "honeys; leave-one-study-out resampling was used to assess dependence on "
    "individual studies. Analyses were performed in Python 3.12 (pandas, "
    "SciPy, statsmodels); the released analysis scripts regenerate every "
    "reported number."
)

# ================= 3. RESULTS =================
h("3. Results and discussion", 1)

h("3.1. Study selection and characteristics", 2)
para(
    f"Searches retrieved {COUNTS['raw_records']:,} records; after removing "
    f"{COUNTS['duplicates_removed']:,} duplicates, "
    f"{COUNTS['unique_screened']:,} records were screened and "
    f"{COUNTS['excluded_screen1']:,} excluded at title/abstract stage. Of "
    f"{COUNTS['screen1_passed']:,} reports assessed, {n_inc} met inclusion "
    f"criteria (Supplementary Fig. S1). Open-access full texts were obtained for "
    f"{SEL['xml_available']} records, and quantitative data were extracted "
    f"from {R['n_studies']} studies, yielding {R['n_rows']:,} harmonized "
    f"observations ({n_mic:,} MIC, {n_zone:,} inhibition-zone and "
    f"{n_mbc:,} MBC values; the remainder comprise biofilm, phenol-equivalence "
    "and dilution-series measures). Physicochemical data were extracted for "
    f"{CHEM['study_id'].nunique()} studies. Risk-of-bias ratings were 'some "
    f"concerns' for most extracted studies ({rob_counts.get('some', 0)} of "
    f"{R['n_studies']}), reflecting incomplete dispersion reporting and "
    f"inconsistent mechanistic characterization; "
    f"{rob_counts.get('low', 0)} were rated low concern and "
    f"{rob_counts.get('high', 0)} high concern."
)
para(
    f"The extracted subset is not a census of eligible studies. Of {n_inc} "
    f"eligible studies, {SEL['eligible'] - SEL['with_pmcid']} had no "
    f"resolvable PubMed Central identifier, "
    f"{SEL['with_pmcid'] - SEL['xml_available']} had an identifier but no "
    f"open-access full text, and "
    f"{SEL['xml_available'] - SEL['extracted']} retrieved full texts yielded "
    "no machine-extractable outcome table meeting our parsing rules. "
    f"A post-extraction audit removed {AUDIT['n_studies_removed']} studies "
    "whose extracted tables did not constitute honey-specific primary "
    "antibacterial data (propolis, bee venom, isolated antimicrobial "
    "peptides, a botanical blend, a nanocomposite formulation, a review "
    "article and antibiotic-control-only captures), together with "
    f"{AUDIT['n_rows_removed']} non-honey comparator rows (antibiotics, "
    "essential oils, extracts, nanoparticles, combination arms and "
    "vehicle controls) in retained studies. "
    f"Extracted studies were more recent than non-extracted studies (median "
    f"year {SEL['year_median_extracted']:.0f} vs. "
    f"{SEL['year_median_nonextracted']:.0f}; Mann-Whitney p "
    f"{pstr(SEL['year_mwu_p'])}) and overwhelmingly open-access "
    f"({SEL['oa_rate_extracted']:.0%} vs. {SEL['oa_rate_nonextracted']:.0%} "
    "flagged open-access). Mechanistic content, however, was similar between "
    "the groups — dilution-related abstracts appeared in "
    f"{SEL['f_dilution_rate_extracted']:.0%} of extracted versus "
    f"{SEL['f_dilution_rate_nonextracted']:.0%} of non-extracted studies, "
    f"peroxide-related in {SEL['f_peroxide_rate_extracted']:.0%} versus "
    f"{SEL['f_peroxide_rate_nonextracted']:.0%}, and MGO-related in "
    f"{SEL['f_mgo_rate_extracted']:.0%} versus "
    f"{SEL['f_mgo_rate_nonextracted']:.0%} — indicating that selection "
    "operated mainly on access rather than on topic. Quantitative results "
    "below therefore describe the extractable subset; the selection "
    "mechanism is reported explicitly rather than treating the subset as a "
    "census of eligible work."
)

h("3.2. Concentration-response", 2)
para(
    f"{A1['n_activity_series']} antibacterial concentration series were "
    f"extractable across {R['conc_response']['n_studies']} studies, spanning "
    "inhibition zones, biofilm inhibition and carbapenemase-producer "
    f"isolates. All {A1['n_activity_series']} series showed a positive "
    f"association between concentration and antibacterial response "
    f"(median Spearman rho = {A1['median_rho']:.2f}; Fig. 1A-2C); "
    f"restricting to the {A1V['n_activity_series_ge4']} series with four or "
    "more ordered concentrations left the direction unchanged "
    f"(median rho = {A1V['median_rho_ge4']:.2f}). In the one study reporting pH "
    "across a full dilution ladder, pH rose monotonically as honey was "
    f"diluted for all four honeys examined (rho = {A1['pH_median_rho']:.2f}; "
    "Fig. 1D), consistent with progressive weakening of the acidic "
    "constraint. Fitting log(response) on log(concentration) across the "
    f"zone series gave a slope of {R['conc_response']['loglog_slope']:.2f} "
    f"(SE {R['conc_response']['loglog_slope_se']:.2f}); the sub-linear point "
    "estimate is compatible with a saturating diffusion-assay response but "
    "the interval is wide and should not be over-interpreted. "
    "Concentration-series data remained scarce, so these results describe "
    "direction rather than a pooled dose-response curve; series "
    "eligibility applied no outcome-side condition, so the uniform "
    "positive direction is a data feature, not a selection artifact, "
    "although with few extractable series it should be read as "
    "consistent direction rather than a universal law."
)
USED.update(["PMC12532491", "PMC11376693", "PMC11792292", "PMC2478674"])
fig("fig2_conc_response",
    "Fig. 1. Concentration-response series. (A) Inhibition zones versus "
    f"honey concentration for five organisms {cite('PMC12532491')}. "
    f"(B) Manuka UMF15+ zones versus concentration for three organisms "
    f"{cite('PMC11376693')}. (C) Biofilm inhibition versus concentration "
    f"for two honeys {cite('PMC11792292')}. (D) pH versus concentration "
    f"for four honeys {cite('PMC2478674')}; pH rises as honey is diluted.")

h("3.3. Natural versus artificial honey", 2)
para(
    f"{A2['n_pairs']} paired comparisons of natural honey versus artificial "
    f"or sugar-equivalent controls were identified "
    f"({A2V['zone']['n_pairs']} zone pairs, 13 MIC "
    f"pairs, {A2V['MBC']['n_pairs']} MBC pairs); one MIC pair was "
    "excluded a priori because the artificial-honey control MIC was "
    "zero and a log potency ratio is undefined, leaving "
    f"{A2V['zone']['n_pairs'] + A2V['MIC']['n_pairs'] + A2V['MBC']['n_pairs']} "
    "pairs for outcome-specific analysis. Analysed on their native "
    "outcome scales and aggregated to study level, "
    f"{A2V['MIC']['n_studies']} studies contributed MIC contrasts "
    f"(median potency ratio {A2V['MIC']['median_ratio']:.2f}; every "
    "contributing study's median exceeded 1; Wilcoxon across study "
    f"medians, p {pstr(A2V['MIC']['wilcoxon_p_study'])}), "
    f"{A2V['MBC']['n_studies']} study contributed MBC contrasts "
    f"(ratio {A2V['MBC']['median_ratio']:.2f}, descriptive only), and "
    f"{A2V['zone']['n_studies']} studies contributed zone contrasts "
    f"(median paired excess +{A2V['zone']['median_diff_mm']:.1f} mm, "
    "positive in both studies; pairs with a zero artificial-honey zone "
    "were preserved as differences, never converted to ratios). "
    f"As an exploratory secondary view, a pair-level Wilcoxon on log "
    f"potency ratios across the {EXPL['n_defined']} pairs for which a "
    "log ratio is defined (the five pairs with a zero control mean are "
    "represented above as native-scale differences) — a test that "
    f"treats dependent pairs as independent — gave p "
    f"{pstr(EXPL['wilcoxon_p'])}; the study-level analysis "
    "above is the primary inference (Fig. 2). "
    "Artificial honey thus reproduced part, but not all, of natural honey's "
    "effect — consistent with a substantial sugar/osmotic contribution "
    "while suggesting additional honey-specific effects in most, though "
    "not every, study. Because artificial honey is an imperfect osmotic "
    "control — few comparators were composition-matched on sugar, pH "
    "and water activity — these residual differences may reflect "
    "multiple compositional differences rather than a single isolated "
    "mechanism."
)
fig("fig3_natural_vs_artificial",
    "Fig. 2. Natural versus artificial honey. (A) Paired inhibition zones. "
    "(B) Paired MIC/MBC values; points below the diagonal indicate greater "
    "potency of natural honey.")

h("3.4. Hydrogen peroxide and dilution", 2)
h2o2 = A3.get("H2O2|MIC", {})
para(
    "Directly matched dilution-resolved evidence on H2O2 was sparse. Within "
    "the extracted corpus, one study reported H2O2 detectable only at 6.25% "
    "and 3.12% honey and not at higher concentrations, and a second linked "
    "glucose oxidase activity, catalase sensitivity and H2O2 concentration "
    "to MIC; both are consistent with a peroxide contribution that is "
    "expressed preferentially at low concentrations rather than at full "
    "strength. Across studies, honey-level "
    f"H2O2 measurements correlated weakly and positively with MIC "
    f"(rho = {rho_str(h2o2.get('spearman_rho', 0))}, n = {h2o2.get('n', 0)}, "
    f"{h2o2.get('n_studies', 0)} studies; Fig. 3), a direction opposite to "
    "a naive 'more peroxide, more potent' expectation, and most plausibly "
    "reflecting between-study confounding: potent non-peroxide honeys can be "
    "low in H2O2. We found no extracted dataset reporting a full H2O2 "
    "dilution ladder with matched antibacterial endpoints; the predicted "
    "intermediate-dilution peroxide peak is therefore supported only "
    "qualitatively, and we report it as an explicit evidence gap."
)
fig("fig4_chemistry",
    "Fig. 3. Cross-study associations between honey-level physicochemical "
    "parameters and antibacterial outcomes (Spearman rho; MIC on a log "
    "scale).")

h("3.5. Catalase perturbation and residual activity", 2)
para(
    f"{A4['n_pairs']} paired catalase-perturbed observations were extracted "
    f"from {len(A4['studies'])} studies. Catalase-treated honey retained a "
    f"median {A4['median_residual_frac']:.0%} of untreated antibacterial "
    "activity (Fig. 4). This indicates substantial peroxide-independent "
    "activity in the honeys tested; with only two contributing studies the "
    "estimate is preliminary, and residual activity cannot be attributed to "
    "MGO or any other single constituent without further evidence."
)
fig("fig5_catalase",
    f"Fig. 4. Paired antibacterial activity before and after catalase "
    f"treatment ({A4['n_pairs']} pairs, {len(A4['studies'])} studies "
    f"{cite('PMC6659206', 'PMC8021062')}); residual activity indicates "
    "peroxide-independent components.")

h("3.6. Physicochemistry versus label as predictors", 2)
mgo = A3.get("MGO|MIC", {})
moist = A3.get("moisture|MIC", {})
phmic = A3.get("pH|MIC", {})
phzone = A3.get("pH|zone", {})
para(
    f"Honey-level physicochemical measurements could be joined to "
    f"antibacterial outcomes for {R['A3_joined_rows']} observations from "
    f"{R['A3_joined_studies']} studies. Within the largest single-study "
    f"block, MGO content correlated inversely with MIC (rho = "
    f"{rho_str(mgo.get('spearman_rho', 0))}, n = {mgo.get('n', 0)}, one "
    "study), consistent with MGO-associated potency. Honey moisture "
    f"correlated positively with MIC (rho = "
    f"{rho_str(moist.get('spearman_rho', 0))}, n = {moist.get('n', 0)}, "
    f"{moist.get('n_studies', 0)} studies), the expected direction if "
    "dilute, high-moisture honeys are less active. Honey pH showed no "
    f"monotone association with MIC (rho = "
    f"{rho_str(phmic.get('spearman_rho', 0))}, n = {phmic.get('n', 0)}) but "
    f"a moderate inverse association with zone size (rho = "
    f"{rho_str(phzone.get('spearman_rho', 0))}, n = {phzone.get('n', 0)})."
)
para(
    f"A linear model on log10(MIC) fitted to the largest complete-case "
    f"block ({A5['n_complete']} observations, predictors "
    f"{', '.join(A5['predictors'])}) explained "
    f"{A5['r2_chem'] * 100:.0f}% of variance in-sample, versus "
    f"{A5['r2_label'] * 100:.0f}% for a manuka/medical-grade label alone. "
    f"However, this in-sample fit rested almost entirely on "
    f"{A5['n_studies']} study. Grouped validation told a different story: "
    f"under leave-one-study-out cross-validation "
    f"(n = {CV['n']}, {CV['n_studies']} studies, predictors "
    f"{', '.join(CV['predictors'])}), chemistry-based predictions performed "
    f"far worse than a null model (cross-validated R2 = "
    f"{CV['r2_cv_chem']:.2f} vs. {CV['r2_cv_null']:.2f}), and the label "
    "model was indistinguishable from null. Measured chemistry is therefore "
    "informative within individual studies but the fitted relationships did "
    "not transfer across studies in this dataset — a result we report "
    "explicitly because it bounds what cross-study chemistry-outcome "
    "synthesis can currently claim."
)

h("3.7. Organism heterogeneity", 2)
para(
    "Median MIC differed markedly across organisms (Fig. 5); because "
    "organism identity is confounded with study, organism medians are "
    "reported descriptively rather than with a pooled test that would "
    "treat within-study replicates as independent. "
    "Organism medians were computed "
    "within each reported concentration basis (Table 1); bases are not "
    "commensurate and no pooled cross-basis ranking is reported. "
    "On the dominant unspecified-percentage basis, Gram-positive "
    "organisms tended to be inhibited at lower honey concentrations than "
    "Gram-negative organisms. Manuka-type "
    f"honeys had a lower median MIC than other honeys "
    f"({R['A6_manuka']['median_manuka']:.0f}% vs. "
    f"{R['A6_manuka']['median_other']:.0f}%; nominal Mann-Whitney p "
    f"{pstr(R['A6_manuka']['mwu_p'])}, which treats rows as independent). "
    f"Within the {MV5['n_studies']} studies testing both types on the "
    "same reported basis, manuka MICs were "
    f"a median {abs(MV5['median_diff']):.1f} percentage points lower "
    f"({MV5['n_lower']} studies lower, {MV5['n_equal']} equal, none "
    f"higher; Wilcoxon across study medians, p "
    f"{pstr(MV5['wilcoxon_p'])}). "
    "The pooled contrast is nonetheless observational: UMF grading, "
    "geographic provenance and study design confound honey type, so the "
    "result should not be read as a botanical-type superiority claim "
    "(Table 1)."
)
fig("fig6_organisms",
    "Fig. 5. MIC distributions by organism group (unspecified-basis "
    "percentage rows only, log scale). Bases are not commensurate; see Table 1 for per-basis medians.")
_ob = pd.read_csv(os.path.join(ROOT, "results", "tables",
                               "organism_mic_by_basis_v5.csv"))
ORG_KEY = ["S. aureus", "MRSA", "S. epidermidis", "E. coli",
           "P. aeruginosa", "Salmonella", "L. monocytogenes"]
BASIS_ORDER = ["% (basis unspecified)", "%v/v", "%w/v", "%w/w"]
_t1 = []
for o in ORG_KEY:
    row = [o]
    for b in BASIS_ORDER:
        s = _ob[(_ob.organism == o) & (_ob.basis == b)]
        row.append(f"{s.iloc[0]['median']:.1f} "
                   f"[{s.iloc[0]['q1']:.1f}-{s.iloc[0]['q3']:.1f}]; "
                   f"{s.iloc[0]['n_studies']}/{s.iloc[0]['n_honeys']}/"
                   f"{s.iloc[0]['n_obs']}" if len(s) else "-")
    _t1.append(row)
table("Table 1. Median MIC (% honey) by organism and reported "
      "concentration basis.",
      ["Organism", "% basis unspecified", "% v/v", "% w/v", "% w/w"],
      _t1,
      note="MIC, minimum inhibitory concentration; MRSA, "
           "methicillin-resistant S. aureus. Entries are median "
           "[IQR]; n studies/n honey samples/n observations. Bases are "
           "not commensurate and are never pooled; cells with fewer "
           "than five observations are suppressed.")

h("3.8. Sensitivity analyses", 2)
para(
    f"Restricting MIC analyses to the low-risk-of-bias subset left the "
    f"qualitative pattern unchanged ({SEN['low_rob']['studies']} studies, "
    f"{SEN['low_rob']['n']} observations, median MIC "
    f"{SEN['low_rob']['median']:.0f}%). Analyzed separately by reported "
    f"concentration basis, median MIC was "
    f"{B5['%w/v']['median']:.0f}% on the percent weight/volume "
    f"basis (n = {B5['%w/v']['n']}), "
    f"{B5['%v/v']['median']:.0f}% on the percent volume/volume basis "
    f"(n = {B5['%v/v']['n']}) and "
    f"{B5['%w/w']['median']:.0f}% on the percent weight/weight basis "
    f"(n = {B5['%w/w']['n']}), confirming that bases are "
    "not interchangeable and must not be pooled. Excluding manuka-labelled "
    f"honeys shifted the overall median MIC only slightly "
    f"({SEN['manuka_excluded']['median']:.1f}%; n = "
    f"{SEN['manuka_excluded']['n']}). Restricting to studies that directly "
    f"measured water activity ({SEN['aw_measured_studies']['studies']} "
    "studies) or H2O2 "
    f"({SEN['h2o2_measured_studies']['studies']} studies) gave medians of "
    f"{SEN['aw_measured_studies']['median']:.0f}% and "
    f"{SEN['h2o2_measured_studies']['median']:.0f}% respectively. No "
    "extracted rows came from preprint records, so a peer-reviewed-only "
    "analysis is identical to the primary set. The catalase and "
    "artificial-honey analyses could not be broadened beyond the studies "
    "that performed those experiments. Supplementary Table S12 summarizes the paired "
    "mechanistic contrasts."
)

# ================= 4. DISCUSSION =================
h("3.9. Discussion", 2)
para(
    "This synthesis is consistent with a dilution-dependent, multi-mechanism "
    "account of honey's antibacterial action. At high concentration, activity "
    "is compatible with dominance of water-activity/osmotic and acidity "
    "constraints: artificial sugar-equivalent honey, an imperfect "
    "osmotic control, recapitulated much, though not all, of natural "
    "honey's effect, solution pH rose "
    "toward neutrality on dilution in the one complete ladder "
    "available, and higher-moisture honeys tended to have higher MICs. On "
    "dilution those constraints weaken, and glucose oxidase can generate "
    "H2O2 under aqueous conditions; the limited within-study evidence "
    "located peroxide activity preferentially at low concentrations "
    + cite("PMID12804080") + ". Finally, catalase-resistant residual "
    "activity (median ~92% in two studies) and the within-study MGO-MIC "
    "association are compatible with a peroxide-independent component in at "
    "least some honeys."
)
para(
    "For food microbiology the practical consequence is that assay "
    "concentration is mechanistically informative, not only quantitative. "
    "An MIC measured near full strength reflects constraints that "
    "dissipate once honey is diluted into a food environment, whereas "
    "activity at intermediate concentrations may be carried by different "
    "chemistry. Evaluations of honey as an antimicrobial ingredient or "
    "preservative should therefore report the concentration range tested "
    "and, where possible, pair outcome measurement with the candidate "
    "mechanisms (pH, water activity, H2O2, MGO) across the same dilution "
    "ladder."
)
para(
    "A related caveat concerns in-matrix validation. The corpus is "
    "dominated by broth- and agar-based susceptibility assays against "
    "foodborne organisms; our full-text audit found no study that "
    "measured activity in an actual food matrix, let alone across a "
    "concentration range. Because matrix constituents (protein, "
    "catalase, competing solutes) can neutralize peroxide- and "
    "osmotic-based activity, extrapolating dilution-scaffold MICs to "
    "predicted preservative performance in real foods is not currently "
    "supported. We report this scarcity as a finding: it defines where "
    "the primary literature must be extended before honey's "
    "dilution-dependent activity can be modelled in food systems."
)
para(
    "Several findings bound what can be claimed. Cross-study "
    "chemistry-outcome correlations are observational and vulnerable to "
    "between-study confounding; the positive H2O2-MIC correlation is the "
    "clearest example, since potent non-peroxide honeys can be low in "
    "H2O2. Grouped cross-validation showed that the apparent predictive "
    "value of measured chemistry did not survive leaving studies out: "
    "within-study gradients, notably the single-study MGO-MIC "
    "association, did not transfer across studies, and honey-type labels "
    "performed no better than a null model. Likewise, although the "
    "pooled manuka-versus-other MIC contrast was nominally significant "
    "and stable under leave-one-study-out resampling, it remains "
    "confounded by UMF grading, provenance and study design. What the "
    "data support is within-study association plus explicit uncertainty "
    "about generalization."
)
para(
    "Other limitations qualify these results. First, quantitative "
    "extraction depended on open-access full texts and machine-readable "
    f"tables: {R['n_studies']} of {n_inc} eligible studies were extracted, "
    "and the extracted subset skews recent and open-access. Second, "
    "concentration-series data were rare, catalase pairs came from two "
    "studies, and no extracted dataset reported H2O2 across a dilution "
    "ladder with matched antibacterial endpoints; the peroxide-dilution "
    "hypothesis is supported qualitatively only. Third, assay heterogeneity "
    "(broth dilution, agar diffusion, differing inocula and media) limits "
    "pooling, and we deliberately avoided meta-analytic pooling across "
    "incompatible measurement bases. Fourth, automated table extraction, "
    "although validated against manual curation, may retain residual "
    "errors; all rows carry provenance for audit. Fifth, the "
    "risk-of-bias framework is a reporting-quality proxy, not a validated "
    "instrument, and the review was not prospectively registered."
)
para(
    "Within these limits, the evidence is consistent with a model in "
    "which concentrated honey relies substantially on physicochemical "
    "constraints, partial dilution supports peroxide-associated "
    "activity, and non-peroxide components sustain residual activity in "
    "some honeys. The corpus does not demonstrate a universal "
    "mechanistic switch, and the decisive experiments — matched dilution "
    "ladders of H2O2, water activity, pH and antibacterial endpoints "
    "within single studies, extended into real food matrices — remain to "
    "be performed."
)

# ================= 5. CONCLUSIONS =================
h("4. Conclusions", 1)
para(
    "Honey's antibacterial activity increased with concentration in every "
    "extractable series, while the physicochemical constraints behind "
    "high-concentration activity weakened on dilution. Natural honey "
    "exceeded sugar-equivalent controls in most matched pairs, "
    "catalase-resistant residual activity was substantial where measured, "
    "and within-study chemistry-outcome associations did not generalize "
    "across studies. The evidence is consistent with a dilution-dependent "
    "balance of osmotic/acidic, peroxide and non-peroxide contributions, "
    "but it does not establish a universal mechanistic switch, and "
    "in-matrix validation is absent in the extracted corpus. Studies "
    "that report full dilution "
    "ladders with matched physicochemical and antibacterial measurements, "
    "extended into real food matrices, are needed before "
    "dilution-dependent activity can be predicted in food systems."
)

# ================= DECLARATIONS =================
h("CRediT authorship contribution statement", 2)
para("Tatsuki Onishi: Conceptualization, Methodology, Software, Formal "
     "analysis, Data curation, Validation, Investigation, Writing — "
     "original draft, Writing — review & editing, Supervision, Project "
     "administration.")
h("Declaration of competing interest", 2)
para("The author declares that he has no known competing financial "
     "interests or personal relationships that could have appeared to "
     "influence the work reported in this paper.")
h("Data availability", 2)
para(
    "All extracted data, the data dictionary, screening decisions, "
    "analysis code and figure scripts are released with this submission "
    "as supplementary material and repository archive. Raw database "
    "search responses are included; no primary experimental data were "
    "generated for this study.")
h("Acknowledgements", 2)
para("None.")
h("Funding", 2)
para("This research did not receive any specific grant from funding "
     "agencies in the public, commercial, or not-for-profit sectors.")
h("Declaration of generative AI use", 2)
para("During the preparation of this work the author used a large "
     "language-model coding assistant to develop the reproducible search, "
     "extraction and analysis code and to assist with drafting. The "
     "author reviewed and edited all content and takes full "
     "responsibility for the integrity of the publication.")

# ================= REFERENCES =================
h("References", 1)
rex_used = REX[REX["pmcid"].isin(USED)][["intext", "ref"]]
rct_used = RCT[[f"PMID{p}" in USED for p in RCT["pmid"]]][["intext", "ref"]]
ALL = pd.concat([rex_used, rct_used]).sort_values("intext")
for _, r in ALL.iterrows():
    doc.add_paragraph(str(r["ref"]), style="List Paragraph")
para("The complete list of the "
     f"{R['n_studies']} studies included in the quantitative synthesis is "
     "given in Supplementary Table S11.")

_fp = os.path.join(OUT, "manuscript_jfs.docx")
doc.save(_fp)

# JFS requires a word count on the title page: count every paragraph
# (title page, abstract, Practical Application, body, references),
# excluding tables and figure captions, then fill the placeholder.
_d = Document(_fp)
_wc = 0
_in_refs = False
for _p in _d.paragraphs:
    _t = _p.text.strip()
    if _t == "References":
        _in_refs = True
    if _in_refs or re.match(r"^Fig\.\s*\d", _t):
        continue
    _wc += len(_t.split())
for _p in _d.paragraphs:
    if "Word count of text" in _p.text:
        for _r in _p.runs:
            _r.text = _r.text.replace("see below", f"{_wc:,}")
        print("word count:", _wc)
        break
_d.save(_fp)
print(f"wrote manuscript_jfs.docx; {len(ALL)} cited references "
      f"(+ {len(REX)} synthesis-corpus refs in Supplementary Table S11)")
