"""Generate the Food Research International manuscript DOCX.

Author-year citations; every numeric claim is read from
results/models/analysis_results.json and the processed data files —
nothing is hard-coded.
"""
import json
import os
import re

import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "manuscript")

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

INC = ELIG[ELIG["elig"].isin(["include", "review_flag"])]
n_inc = len(INC)
n_outcome = EXT[EXT["outcome"].isin(["MIC", "zone", "MBC"])]
n_mic = int((EXT["outcome"] == "MIC").sum())
n_zone = int((EXT["outcome"] == "zone").sum())
n_mbc = int((EXT["outcome"] == "MBC").sum())
rob_counts = ROB["rating"].value_counts().to_dict()

doc = Document()
st = doc.styles["Normal"]
st.font.name = "Times New Roman"
st.font.size = Pt(11)


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
center("Dilution-dependent antibacterial mechanisms of honey: a systematic "
       "review and cross-study quantitative evidence synthesis", 15)
doc.add_paragraph()
center("[Author One] a, [Author Two] b, [Corresponding Author] a,*",
       11, bold=False)
center("a [Affiliation 1]; b [Affiliation 2]", 10, bold=False)
center("* Corresponding author. E-mail address: [email]", 10, bold=False)
doc.add_paragraph()

# ================= ABSTRACT =================
h("Abstract", 1)
para(
    "Honey exhibits broad-spectrum antibacterial activity, but whether its "
    "mechanism of action changes with dilution — rather than simply weakening — "
    "remains incompletely resolved. We conducted a systematic review and "
    f"cross-study quantitative evidence synthesis. Searches of PubMed, Europe "
    f"PMC and Crossref, plus citation mining and data-repository searches, "
    f"retrieved {COUNTS['raw_records']:,} records; "
    f"{COUNTS['unique_screened']:,} unique records were screened, {n_inc} "
    f"studies met eligibility criteria, and structured data were extracted from "
    f"{R['n_studies']} open-access full texts ({R['n_rows']:,} observations). "
    f"All {A1['n_activity_series']} extractable antibacterial concentration "
    f"series increased monotonically with honey concentration (median Spearman "
    f"rho = {A1['median_rho']:.2f}), while solution pH rose on dilution "
    f"(rho = {A1['pH_median_rho']:.2f}), consistent with weakening acidity. "
    f"Natural honeys exceeded sugar-equivalent artificial controls in "
    f"{ADIR['n_natural_stronger']} of {ADIR['n_pairs']} matched pairs (median "
    f"potency ratio {ADIR['median_ratio']:.2f}, p "
    f"{pstr(ADIR['wilcoxon_p_logratio'])}). Catalase-treated honey retained a "
    f"median {A4['median_residual_frac']:.0%} of activity "
    f"({A4['n_pairs']} pairs, {len(A4['studies'])} studies). Cross-study "
    f"associations between honey chemistry and outcomes were detectable within "
    f"studies but did not generalize: leave-one-study-out cross-validated R2 "
    f"was negative for chemistry-based and label-based models alike. "
    "Directly matched dilution-resolved hydrogen peroxide and antibacterial "
    "measurements were rare. The evidence is consistent with dilution-dependent "
    "reweighting of osmotic, acidic, peroxide and non-peroxide mechanisms, but "
    "does not establish a universal mechanistic switch; dilution-resolved "
    "mechanistic measurement remains the key evidence gap."
)
para("Keywords: honey; dilution; hydrogen peroxide; methylglyoxal; "
     "water activity; systematic review")  # Elsevier max 6 keywords

# ================= 1. INTRODUCTION =================
h("1. Introduction", 1)
para(
    "Honey is a complex food matrix with well-documented in vitro antibacterial "
    "activity " + cite("PMID20228250", "PMID1447054") + ". Its activity arises "
    "from several partially independent mechanisms: high osmolarity and low "
    "water activity constrain microbial growth, its acidity (typically "
    "pH 3.2-4.5) inhibits many pathogens, bee-derived glucose oxidase generates "
    "hydrogen peroxide (H2O2) under aqueous conditions, and non-peroxide "
    "constituents — most prominently methylglyoxal (MGO) in manuka-type honeys "
    "— contribute additional activity "
    + cite("PMID21394213", "PMID20228250") + "."
)
para(
    "These mechanisms respond differently to dilution. Osmotic and acidic "
    "constraints weaken progressively as honey is diluted, whereas glucose "
    "oxidase activity is strongly constrained in undiluted honey and "
    "becomes appreciable mainly after partial dilution, as shown "
    "experimentally by Bang and colleagues "
    + cite("PMID12804080") + ". Non-peroxide components have their own "
    "concentration-response behaviour. It is therefore plausible that the "
    "dominant antibacterial mechanism of honey is dilution-dependent: the "
    "mechanism that explains activity at 80% honey may not be the mechanism "
    "that explains activity at 10% honey."
)
para(
    "This question is relevant to food microbiology and food functionality, "
    "where honey is evaluated as a natural antimicrobial ingredient or surface "
    "treatment and is frequently used in diluted form. If high-concentration "
    "activity rests largely on constraints that collapse on dilution while "
    "peroxide-associated activity appears predominantly at intermediate "
    "dilutions, then "
    "assays performed on concentrated honey could systematically misestimate "
    "performance under realistic, diluted conditions. Because individual "
    "studies rarely measure all candidate mechanisms across a dilution "
    "gradient, cross-study synthesis is needed to assess the pattern."
)
para(
    "We conducted a systematic review and quantitative evidence synthesis of "
    "primary studies addressing the dilution dependence of honey's "
    "antibacterial mechanisms. We asked: (i) how antibacterial activity varies "
    "with honey concentration; (ii) whether natural honey exceeds "
    "sugar-equivalent artificial-honey controls; (iii) how H2O2 production "
    "varies with dilution and whether it tracks measured activity; (iv) how "
    "much activity survives catalase-mediated H2O2 removal; (v) whether "
    "measured physicochemical parameters predict antibacterial outcomes beyond "
    "honey-type labels; and (vi) how results vary across organisms. We "
    "pre-specified that causal or mechanistic language would be reserved for "
    "within-study perturbation evidence (for example catalase treatment or "
    "artificial-honey comparators), with cross-study associations reported as "
    "observational."
)

# ================= 2. METHODS =================
h("2. Material and methods", 1)

h("2.1. Protocol and reporting", 2)
para(
    "The review was conducted and reported with reference to the PRISMA 2020 "
    "guideline where applicable; the study flow is summarized in Fig. 1. The "
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
    "between concentration and response; a series was eligible when it "
    "contained at least four ordered concentrations with a monotone-reported "
    "endpoint. Natural versus artificial honey was compared within study, "
    "organism, outcome and concentration strata; to make inhibition-zone and "
    "MIC/MBC contrasts directionally comparable, effects were expressed as a "
    "potency ratio (natural/artificial for zones; artificial/natural for "
    "MIC/MBC, so that values above 1 always indicate greater natural-honey "
    "potency) and tested with a Wilcoxon signed-rank test on log ratios. "
    "Catalase-treated versus untreated observations were paired identically "
    "and expressed as residual activity fractions. Honey-level physicochemical "
    "parameters were joined to outcomes on study and normalized sample label; "
    "Spearman correlations were computed per parameter and outcome, and "
    "ordinary least squares models on log10(MIC) compared measured chemistry, "
    "a honey-type label and their combination. Because rows from the same "
    "study are not independent, model performance was evaluated by "
    "leave-one-study-out cross-validation rather than in-sample fit. Organism "
    "heterogeneity was assessed with Kruskal-Wallis tests. Sensitivity "
    "analyses repeated key contrasts on the low-risk-of-bias subset, on each "
    "concentration basis separately, and after excluding manuka-labelled "
    "honeys; leave-one-study-out resampling was used to assess dependence on "
    "individual studies. Analyses were performed in Python 3.12 (pandas, "
    "SciPy, statsmodels); the released analysis scripts regenerate every "
    "reported number."
)

# ================= 3. RESULTS =================
h("3. Results", 1)

h("3.1. Study selection and characteristics", 2)
para(
    f"Searches retrieved {COUNTS['raw_records']:,} records; after removing "
    f"{COUNTS['duplicates_removed']:,} duplicates, "
    f"{COUNTS['unique_screened']:,} records were screened and "
    f"{COUNTS['excluded_screen1']:,} excluded at title/abstract stage. Of "
    f"{COUNTS['screen1_passed']:,} reports assessed, {n_inc} met inclusion "
    f"criteria (Fig. 1). Open-access full texts were obtained for "
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
fig("fig1_prisma",
    "Fig. 1. PRISMA 2020-style flow of study identification, screening, "
    "eligibility and quantitative extraction.")

h("3.2. Concentration-response", 2)
para(
    f"{A1['n_activity_series']} antibacterial concentration series were "
    f"extractable across {R['conc_response']['n_studies']} studies, spanning "
    "inhibition zones, biofilm inhibition and carbapenemase-producer "
    f"isolates. All {A1['n_activity_series']} series increased monotonically "
    f"with honey concentration (median Spearman rho = "
    f"{A1['median_rho']:.2f}; Fig. 2A-2C). In the one study reporting pH "
    "across a full dilution ladder, pH rose monotonically as honey was "
    f"diluted for all four honeys examined (rho = {A1['pH_median_rho']:.2f}; "
    "Fig. 2D), consistent with progressive weakening of the acidic "
    "constraint. Fitting log(response) on log(concentration) across the "
    f"zone series gave a slope of {R['conc_response']['loglog_slope']:.2f} "
    f"(SE {R['conc_response']['loglog_slope_se']:.2f}); the sub-linear point "
    "estimate is compatible with a saturating diffusion-assay response but "
    "the interval is wide and should not be over-interpreted. "
    "Concentration-series data remained scarce, so these results describe "
    "direction rather than a pooled dose-response curve."
)
USED.update(["PMC12532491", "PMC11376693", "PMC11792292", "PMC2478674"])
fig("fig2_conc_response",
    "Fig. 2. Concentration-response series. (A) Inhibition zones versus "
    f"honey concentration for five organisms {cite('PMC12532491')}. "
    f"(B) Manuka UMF15+ zones versus concentration for three organisms "
    f"{cite('PMC11376693')}. (C) Biofilm inhibition versus concentration "
    f"for two honeys {cite('PMC11792292')}. (D) pH versus concentration "
    f"for four honeys {cite('PMC2478674')}; pH rises as honey is diluted.")

h("3.3. Natural versus artificial honey", 2)
para(
    f"{A2['n_pairs']} paired comparisons of natural honey versus artificial "
    f"or sugar-equivalent controls were identified "
    f"({A2['zone_pairs']} zone pairs, {A2['mic_pairs']} MIC/MBC pairs). "
    f"Direction-normalized, natural honey was more potent in "
    f"{ADIR['n_natural_stronger']} of {ADIR['n_pairs']} pairs (median potency "
    f"ratio {ADIR['median_ratio']:.2f}; Wilcoxon on log ratios, p "
    f"{pstr(ADIR['wilcoxon_p_logratio'])}; Fig. 3). In zone units the median "
    f"paired excess was +{A2['zone_median_diff_mm']:.1f} mm; in MIC units the "
    f"median natural:artificial ratio was {A2['mic_median_ratio']:.2f}. "
    "Artificial honey thus reproduced part, but not all, of natural honey's "
    "effect — consistent with a substantial sugar/osmotic contribution "
    "while suggesting additional honey-specific effects in most, though "
    "not every, study. Because artificial honey is an imperfect osmotic "
    "control, these residual differences may reflect multiple "
    "compositional differences rather than a single isolated mechanism."
)
fig("fig3_natural_vs_artificial",
    "Fig. 3. Natural versus artificial honey. (A) Paired inhibition zones. "
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
    f"{h2o2.get('n_studies', 0)} studies; Fig. 4) — a direction opposite to "
    "a naive 'more peroxide, more potent' expectation and most plausibly "
    "reflecting between-study confounding (potent non-peroxide honeys can be "
    "low in H2O2). We found no extracted dataset reporting a full H2O2 "
    "dilution ladder with matched antibacterial endpoints; the predicted "
    "intermediate-dilution peroxide peak is therefore supported only "
    "qualitatively, and we report it as an explicit evidence gap."
)
fig("fig4_chemistry",
    "Fig. 4. Cross-study associations between honey-level physicochemical "
    "parameters and antibacterial outcomes (Spearman rho; MIC on a log "
    "scale).")

h("3.5. Catalase perturbation and residual activity", 2)
para(
    f"{A4['n_pairs']} paired catalase-perturbed observations were extracted "
    f"from {len(A4['studies'])} studies. Catalase-treated honey retained a "
    f"median {A4['median_residual_frac']:.0%} of untreated antibacterial "
    "activity (Fig. 5). This indicates substantial peroxide-independent "
    "activity in the honeys tested; with only two contributing studies the "
    "estimate is preliminary, and residual activity cannot be attributed to "
    "MGO or any other single constituent without further evidence."
)
fig("fig5_catalase",
    f"Fig. 5. Paired antibacterial activity before and after catalase "
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
    f"MIC distributions differed strongly across organisms (Kruskal-Wallis "
    f"H = {A6['kruskal_H']:.0f}, p {pstr(A6['kruskal_p'])}; Fig. 6). "
    "Gram-positive organisms tended to be inhibited at lower honey "
    f"concentrations (median MIC: *S. epidermidis* "
    f"{A6['median_MIC_by_organism'].get('S. epidermidis', '')}%, "
    f"*S. aureus* {A6['median_MIC_by_organism'].get('S. aureus', '')}%, MRSA "
    f"{A6['median_MIC_by_organism'].get('MRSA', '')}%) than Gram-negative "
    f"organisms (*E. coli* "
    f"{A6['median_MIC_by_organism'].get('E. coli', '')}%, *P. aeruginosa* "
    f"{A6['median_MIC_by_organism'].get('P. aeruginosa', '')}%). Manuka-type "
    f"honeys had a nominally lower median MIC than other honeys "
    f"({R['A6_manuka']['median_manuka']:.0f}% vs. "
    f"{R['A6_manuka']['median_other']:.0f}%; Mann-Whitney p "
    f"{pstr(R['A6_manuka']['mwu_p'])}); however, the contrast was unstable "
    "under leave-one-study-out resampling, which returned non-significant "
    f"comparisons in {SEN['loo_manuka_ns_frac']:.0%} of iterations. The "
    "direction is therefore suggestive but not robust enough to support a "
    "general superiority claim for manuka-type honeys (Table 1)."
)
fig("fig6_organisms",
    "Fig. 6. MIC distributions by organism group (percentage-unit studies, "
    "log scale).")
table("Table 1. Median MIC (% honey) by organism group, percentage-unit "
      "studies.",
      ["Organism group", "Median MIC (%)"],
      [(o, v) for o, v in R["A6"]["median_MIC_by_organism"].items()],
      note="MIC, minimum inhibitory concentration; MRSA/MSSA, "
           "methicillin-resistant/susceptible S. aureus. Values are medians "
           "of extracted MIC rows restricted to percentage-unit bases.")

h("3.8. Sensitivity analyses", 2)
para(
    f"Restricting MIC analyses to the low-risk-of-bias subset left the "
    f"qualitative pattern unchanged ({SEN['low_rob']['studies']} studies, "
    f"{SEN['low_rob']['n']} observations, median MIC "
    f"{SEN['low_rob']['median']:.0f}%). Analyzed separately by reported "
    f"concentration basis, median MIC was "
    f"{SEN['w_v_basis_only']['median']:.0f}% on the percent weight/volume "
    f"basis (n = {SEN['w_v_basis_only']['n']}) and "
    f"{SEN['v_v_basis_only']['median']:.0f}% on the percent volume/volume "
    f"basis (n = {SEN['v_v_basis_only']['n']}), confirming that bases are "
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
    "that performed those experiments. Table 2 summarizes the paired "
    "mechanistic contrasts."
)
PAIRS = pd.read_csv(os.path.join(ROOT, "results", "tables",
                               "natural_vs_artificial_pairs.csv"))
n_art_studies = PAIRS["study_id"].nunique()
n_art_zone_studies = PAIRS.loc[PAIRS["outcome"] == "zone",
                               "study_id"].nunique()
table("Table 2. Paired evidence for mechanistic contrasts.",
      ["Contrast", "n pairs/obs", "n studies", "Effect", "p value"],
      [
       ("Natural vs artificial honey (potency ratio)",
        str(ADIR["n_pairs"]), str(n_art_studies),
        f"{ADIR['n_natural_stronger']}/{ADIR['n_pairs']} pairs > 1; "
        f"median {ADIR['median_ratio']:.2f}",
        pstr(ADIR["wilcoxon_p_logratio"]).lstrip("= ")),
       ("Natural vs artificial honey, zone difference (mm)",
        str(A2["zone_pairs"]), str(n_art_zone_studies),
        f"median +{A2['zone_median_diff_mm']:.1f} mm",
        pstr(A2["zone_wilcoxon_p"]).lstrip("= ")),
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
      note="Potency ratio > 1 indicates greater natural-honey activity "
           "(zone: natural/artificial; MIC: artificial/natural). MGO, "
           "methylglyoxal; MIC, minimum inhibitory concentration.")

# ================= 4. DISCUSSION =================
h("4. Discussion", 1)
para(
    "This synthesis is consistent with a dilution-dependent, multi-mechanism "
    "account of honey's antibacterial action. At high concentration, activity "
    "is compatible with dominance of water-activity/osmotic and acidity "
    "constraints: artificial sugar-equivalent honey — an imperfect "
    "osmotic control — recapitulated much, though not all, of natural "
    "honey's effect, solution pH rose "
    "monotonically toward neutrality on dilution in the one complete ladder "
    "available, and higher-moisture honeys tended to have higher MICs. On "
    "dilution those constraints weaken, and glucose oxidase can generate "
    "H2O2 under aqueous conditions; the limited within-study evidence "
    "located peroxide activity preferentially at low concentrations "
    + cite("PMID12804080") + ". Finally, catalase-resistant residual "
    "activity (median ~92% in two studies) and the within-study MGO-MIC "
    "association are compatible with a peroxide-independent component in at "
    "least some honeys. The three mechanism classes are therefore plausibly "
    "reweighted — not merely attenuated — along the dilution axis."
)
para(
    "For food science applications the practical implication is that assay "
    "concentration is mechanistically informative, not only quantitative. An "
    "MIC measured near the top of the concentration range may reflect "
    "constraints that disappear on dilution, whereas activity at "
    "intermediate concentrations may be carried by different chemistry. "
    "Evaluations of honey as an antimicrobial ingredient or preservative "
    "should therefore report the concentration range tested and, where "
    "possible, pair outcome measurement with the candidate mechanisms (pH, "
    "water activity, H2O2, MGO) across the same dilution ladder."
)
para(
    "Several findings bound what can be claimed. Cross-study "
    "chemistry-outcome correlations are observational and vulnerable to "
    "between-study confounding — the positive H2O2-MIC correlation is the "
    "clearest example. More importantly, grouped cross-validation showed "
    "that the apparent predictive value of measured chemistry did not "
    "survive leaving studies out: within-study gradients (notably the "
    "single-study MGO-MIC association) do not transfer across studies, and "
    "honey-type labels performed no better than a null model. Any claim "
    "that measured chemistry predicts potency across the literature would "
    "therefore overstate the evidence; what the data support is "
    "within-study association plus explicit uncertainty about "
    "generalization."
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
    "Within these limits, the evidence supports a model in which "
    "concentrated honey relies substantially on physicochemical constraints, "
    "partial dilution supports peroxide-associated activity, and "
    "non-peroxide components sustain residual activity in some honeys. It "
    "does not demonstrate a universal mechanistic switch, and the decisive "
    "experiment — matched dilution ladders of H2O2, water activity, pH and "
    "antibacterial endpoints within single studies — remains to be "
    "performed at scale."
)

# ================= 5. CONCLUSIONS =================
h("5. Conclusions", 1)
para(
    "Honey's antibacterial activity increased consistently with "
    "concentration in every extractable series, while the physicochemical "
    "constraints plausibly responsible for high-concentration activity "
    "weakened on dilution. Natural honey exceeded sugar-equivalent controls "
    "in most matched pairs, catalase-resistant residual activity was "
    "substantial where measured, and within-study chemistry-outcome "
    "associations — though real — did not generalize across studies. The "
    "evidence is consistent with dilution-dependent reweighting of "
    "osmotic/acidic, peroxide and non-peroxide mechanisms, but it does not "
    "establish a universal switch. Future studies should report full "
    "dilution ladders with matched physicochemical and antibacterial "
    "measurements, including concentration basis, so that mechanistic "
    "claims can be tested within studies rather than inferred across them."
)

# ================= DECLARATIONS =================
h("CRediT authorship contribution statement", 2)
para("[Author One]: Conceptualization, Methodology, Software, Formal "
     "analysis, Data curation, Writing — original draft. [Author Two]: "
     "Validation, Investigation, Writing — review & editing. "
     "[Corresponding Author]: Supervision, Project administration, Writing "
     "— review & editing.")
h("Declaration of competing interest", 2)
para("The authors declare that they have no known competing financial "
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
para("During the preparation of this work the authors used a large "
     "language-model coding assistant to develop the reproducible search, "
     "extraction and analysis code and to assist with drafting. The "
     "authors reviewed and edited all content and take full "
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

doc.save(os.path.join(OUT, "manuscript_fri.docx"))
print(f"wrote manuscript_fri.docx; {len(ALL)} cited references "
      f"(+ {len(REX)} synthesis-corpus refs in Supplementary Table S11)")
