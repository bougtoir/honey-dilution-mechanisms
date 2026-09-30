"""Generate the main manuscript DOCX (MDPI/Antibiotics research-article structure)."""
import os
import re

import pandas as pd
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "manuscript")

# ---------- citation map ----------
REX = pd.read_csv(os.path.join(ROOT, "references", "references_extracted.csv"))
RCT = pd.read_csv(os.path.join(ROOT, "references", "references_context.csv"))
CTX_BASE = len(REX)
CITE = {p: i + 1 for i, p in enumerate(REX["pmcid"])}
for i, p in enumerate(RCT["pmid"]):
    CITE[f"PMID{int(p)}"] = CTX_BASE + i + 1


def cite(*keys):
    nums = sorted(CITE[k] for k in keys if k in CITE)
    return "[" + ",".join(str(n) for n in nums) + "]"


def load_results():
    import json
    return json.load(open(os.path.join(ROOT, "results", "models",
                                      "analysis_results.json")))


R = load_results()

doc = Document()
st = doc.styles["Normal"]
st.font.name = "Times New Roman"
st.font.size = Pt(11)


def h(text, level=1):
    p = doc.add_heading(text, level=level)
    for r in p.runs:
        r.font.name = "Times New Roman"
        r.font.color.rgb = __import__("docx.shared", fromlist=["RGBColor"]).RGBColor(0, 0, 0)
    return p


def para(text, italic_species=True):
    """Add paragraph; *...* renders italic."""
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
    """Embed a figure inline with its caption beneath it."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(os.path.join(FIGDIR, name + ".png"),
                            width=Inches(width))
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.LEFT
    parts = caption.split(". ", 1)
    r = cap.add_run(parts[0] + ". ")
    r.bold = True
    cap.add_run(parts[1] if len(parts) > 1 else "")
    doc.add_paragraph()


# ================= TITLE PAGE =================
center("Dilution-Dependent Antibacterial Mechanisms of Honey: A Systematic "
       "Review and Cross-Study Quantitative Evidence Synthesis", 15)
doc.add_paragraph()
center("[Author One] 1, [Author Two] 2 and [Corresponding Author] 1,*", 11, bold=False)
center("1 [Affiliation 1]; 2 [Affiliation 2]", 10, bold=False)
center("* Correspondence: [email]", 10, bold=False)
doc.add_paragraph()

# ================= ABSTRACT =================
h("Abstract", 1)
para(
    "Honey exhibits broad-spectrum antibacterial activity, yet how its mechanism "
    "of action depends on dilution remains incompletely characterized. Concentrated "
    "honey is hypothesized to act primarily through low water activity, acidity and "
    "osmotic stress, whereas moderate dilution may enhance glucose oxidase-derived "
    "hydrogen peroxide (H2O2) production, and some honeys retain non-peroxide "
    "activity associated with methylglyoxal (MGO) or other constituents. We conducted "
    "a systematic review and quantitative evidence synthesis of published primary "
    "studies. Searches of PubMed, Europe PMC and Crossref (with backward citation "
    "mining) retrieved 4,042 records; 2,236 unique records were screened, 412 studies "
    "met eligibility criteria, and structured antibacterial and physicochemical data "
    "were extracted from 103 open-access full texts (5,026 observations). "
    "Concentration-response series were consistently positive: all 10 extractable "
    "antibacterial dilution series increased with honey concentration (median "
    "Spearman rho = 1.00), while measured pH rose monotonically on dilution "
    "(rho = -1.00, n = 4 series), consistent with weakening acidity as honey is "
    "diluted. Natural honeys modestly but consistently outperformed sugar-equivalent "
    "artificial-honey comparators (paired zone differences, median +0.6 mm, "
    "p = 0.002; MIC ratio 0.81). Catalase-treated honey retained a median 92% of "
    "untreated activity (13 paired observations, 2 studies), indicating substantial "
    "non-peroxide activity in the honeys examined. Within-study, honey-level MGO "
    "correlated inversely with MIC (rho = -0.52, n = 116), and a multivariable model "
    "using measured chemistry (pH, moisture) explained more outcome variance than "
    "botanical or medical-grade labels (R2 = 0.30 vs. 0.00). Antibacterial potency "
    "differed strongly across organisms (Kruskal-Wallis p < 0.0001). These findings "
    "support a model in which dilution shifts the dominant antibacterial mechanism "
    "of honey, and indicate that assays performed only at high concentration may "
    "misestimate activity under diluted conditions such as exudative environments."
)
para("Keywords: honey; antibacterial activity; dilution; hydrogen peroxide; "
     "methylglyoxal; water activity; catalase; systematic review; evidence synthesis")

# ================= 1. INTRODUCTION =================
h("1. Introduction", 1)
para(
    "Honey has been used as a topical antimicrobial for centuries, and its "
    "antibacterial properties are now well documented in vitro "
    + cite("PMID20228250", "PMID1447054") +
    ". Multiple mechanisms contribute: high osmolarity and low water activity "
    "restrict microbial growth, acidity (typically pH 3.2-4.5) inhibits many "
    "pathogens, enzymatic generation of hydrogen peroxide by bee-derived glucose "
    "oxidase provides a peroxide-based mechanism in many honeys, and "
    "non-peroxide factors, most prominently methylglyoxal (MGO) in manuka-type "
    "honeys, add further activity "
    + cite("PMID21394213", "PMID20228250") +
    ". These mechanisms do not respond identically to dilution. Osmotic and acidic "
    "constraints weaken progressively as honey is diluted, whereas glucose oxidase "
    "requires aqueous conditions and can generate more H2O2 after partial dilution "
    "than in undiluted honey, a phenomenon demonstrated experimentally by Bang and "
    "colleagues " + cite("PMID12804080") + ". Non-peroxide mechanisms have their own "
    "dilution-response characteristics. It is therefore plausible that the dominant "
    "antibacterial mechanism of honey is dilution-dependent rather than simply "
    "dilution-attenuated."
)
para(
    "This question matters for interpretation of the evidence base. In vitro assays "
    "performed on undiluted or highly concentrated honey may not represent "
    "conditions in which honey is substantially diluted, for example by wound "
    "exudate. If concentrated honey relies heavily on mechanisms that collapse on "
    "dilution (water activity, acidity) while peroxide-mediated activity only "
    "emerges or peaks at intermediate dilutions, then undiluted assays could "
    "systematically misestimate antibacterial performance under diluted conditions. "
    "Cross-study synthesis offers a route to examine this question at scale, "
    "because individual studies rarely measure all mechanisms across a dilution "
    "gradient simultaneously."
)
para(
    "We performed a systematic review and quantitative evidence synthesis of "
    "published primary studies addressing the dilution dependence of honey's "
    "antibacterial mechanisms. We asked six questions: (RQ1) how antibacterial "
    "activity varies with honey concentration; (RQ2) whether natural honey "
    "outperforms artificial or sugar-equivalent controls; (RQ3) how H2O2 production "
    "varies with dilution and whether it corresponds to measured activity; (RQ4) "
    "what residual activity remains after catalase-mediated removal of H2O2; (RQ5) "
    "whether measured physicochemical parameters predict antibacterial outcomes "
    "beyond honey-type labels; and (RQ6) whether concentration-response "
    "relationships differ across organisms. We pre-specified that causal language "
    "would be reserved for perturbation evidence (for example catalase treatment), "
    "with cross-study associations reported as observational."
)

# ================= 2. METHODS =================
h("2. Materials and Methods", 1)

h("2.1. Protocol and reporting", 2)
para(
    "This systematic review was conducted and reported with reference to the "
    "PRISMA 2020 guideline where applicable; a PRISMA-style flow diagram is given "
    "in Figure 1. The review was not prospectively registered; the full analytic "
    "pipeline is released as executable code (Data Availability Statement). "
    "Because no protocol registration exists, eligibility criteria and analysis "
    "decisions are reported here in full and the screening and extraction code is "
    "deterministic and versioned."
)

h("2.2. Search strategy", 2)
para(
    "We searched PubMed (NCBI E-utilities), Europe PMC (REST API) and Crossref "
    "(works API) for records combining honey-related terms with antibacterial, "
    "minimum inhibitory concentration (MIC), zone-of-inhibition, peroxide, "
    "methylglyoxal, water-activity and dilution terms (full query strings are "
    "stored with the raw search output in the accompanying repository). Searches "
    "were executed programmatically and raw JSON responses were retained. Backward "
    "and forward citation mining was then performed through Europe PMC for "
    "candidate mechanistic studies, contributing additional records. All retrieved "
    "records were deduplicated on DOI, PubMed ID and normalized title."
)

h("2.3. Eligibility criteria", 2)
para(
    "Records were eligible if they reported a primary in vitro antibacterial "
    "evaluation of natural honey with a quantitative endpoint (MIC, minimum "
    "bactericidal concentration, inhibition zone, biofilm inhibition or "
    "equivalent) and at least one of: a concentration or dilution series, an "
    "artificial-honey or sugar-equivalent comparator, a catalase or other "
    "mechanistic perturbation, or quantitative physicochemical characterization "
    "(H2O2, MGO, water activity, pH, phenolics). Reviews, non-antibacterial "
    "studies, non-honey studies and records without a usable abstract were "
    "excluded. Eligibility was assigned by a deterministic rule-based classifier "
    "applied to titles and abstracts, followed by manual verification of included "
    "candidates; the classifier rules and per-record decisions are released with "
    "the dataset."
)

h("2.4. Data extraction", 2)
para(
    "Open-access full texts were retrieved from PubMed Central as JATS XML. All "
    "tables were parsed programmatically, including nested table structures, with "
    "merged header cells (colspan) expanded and multi-row headers reconstructed. "
    "A rule-based extractor converted the dominant table layouts into long-format "
    "observations with study, table, row and column provenance. For key "
    "mechanistic datasets (catalase-treated versus untreated pairs, "
    "simulated-honey controls, concentration series and MGO-spike dose-response), "
    "rows were additionally extracted manually after direct inspection of the "
    "source tables and captions; manually curated rows are flagged in the dataset "
    "and take precedence. Organism labels were harmonized to organism groups "
    "using a documented mapping. Concentrations embedded in sample labels were "
    "parsed into a dedicated concentration field. Values reported with inequality "
    "signs were retained with a censoring flag."
)

h("2.5. Risk-of-bias and reporting-quality assessment", 2)
para(
    "No validated risk-of-bias instrument exists for cross-study in vitro "
    "antibacterial data. We therefore applied a structured, documented framework "
    "covering five domains: assay standardization, comparator quality, dispersion "
    "reporting, mechanistic perturbation and reporting completeness, each scored "
    "0-2. Availability of concentration-series data was recorded separately as an "
    "availability flag rather than a quality judgement. Ratings (low, some, high "
    "concern) were assigned from domain totals and used in sensitivity analyses."
)

h("2.6. Statistical analysis", 2)
para(
    "Analyses were restricted to comparable measurement bases (for example, MIC "
    "expressed as percentage honey). Concentration-response was summarized by "
    "per-series Spearman correlations between concentration and response. Natural "
    "versus artificial honey was compared within study, organism, outcome and "
    "concentration strata using paired differences, with Wilcoxon signed-rank "
    "tests. Catalase-treated versus untreated observations were paired identically "
    "and expressed as residual activity fractions. Honey-level physicochemical "
    "parameters were joined to antibacterial outcomes on study and normalized "
    "sample label; Spearman correlations were computed per parameter and outcome, "
    "and nested ordinary least squares models on log10(MIC) compared variance "
    "explained by measured chemistry versus a honey-type label. Organism "
    "heterogeneity was assessed with Kruskal-Wallis tests and distributional "
    "summaries. Sensitivity analyses repeated key contrasts on the low-risk-of-"
    "bias subset. Analyses were performed in Python 3.12 (pandas, SciPy, "
    "statsmodels); the analysis script regenerates every reported number."
)

# ================= 3. RESULTS =================
h("3. Results", 1)

h("3.1. Study selection and characteristics", 2)
para(
    "Searches retrieved 4,042 records; after removing 1,806 duplicates, 2,236 "
    "records were screened and 1,371 excluded at title/abstract stage. Of 865 "
    "reports assessed for eligibility, 412 met inclusion criteria (Figure 1). "
    "Open-access full texts were obtained for 376 records, and quantitative data "
    "were extracted from 103 studies, yielding 5,026 harmonized observations "
    "(MIC 2,616; inhibition zone 1,458; MBC 651; other endpoints and "
    "dilution-series measures the remainder). Physicochemical data were extracted "
    "for 59 studies (pH n = 400, H2O2 n = 272, MGO n = 74, water activity n = 74 "
    "observations). Risk-of-bias ratings were 'some concerns' for most extracted "
    "studies (90 of 103), reflecting incomplete dispersion reporting and "
    "inconsistent mechanistic characterization; 7 studies were rated low concern "
    "and 3 high concern."
)
fig("fig1_prisma",
    "Figure 1. PRISMA-style flow of study identification, screening, "
    "eligibility and quantitative extraction.")

h("3.2. Concentration-response (RQ1)", 2)
para(
    "Ten antibacterial concentration-series were extractable across 4 studies, "
    "spanning inhibition zones, biofilm inhibition and carbapenemase-producer "
    "isolates. All 10 series showed positive monotonic trends of activity with "
    "concentration (median Spearman rho = 1.00; Figure 2A-2C). In parallel, the "
    "physicochemical constraints weakened with dilution: in the one study "
    "reporting pH across a full dilution ladder, pH rose monotonically from "
    "approximately 5.25 at 50% honey to 7.28 at 3.12% honey for all four honeys "
    "examined (rho = -1.00; Figure 2D). This pattern is consistent with the "
    "hypothesis that acidity- and osmolarity-based constraints dominate at high "
    "concentration and weaken progressively on dilution; however, series data "
    "were scarce (concentration-series flag positive in only 8 of 103 extracted "
    "studies), and publication of full dilution ladders is uncommon."
)
fig("fig2_conc_response",
    "Figure 2. Concentration-response series. (A) Inhibition zones versus "
    "honey concentration for five organisms [32]. (B) Manuka UMF15+ zones "
    "versus concentration for three organisms [63]. (C) Biofilm inhibition "
    "versus concentration for two honeys [15]. (D) pH versus concentration "
    "for four honeys [89]; pH rises as honey is diluted.")

h("3.3. Natural versus artificial honey (RQ2)", 2)
para(
    "Twenty-one paired comparisons of natural honey versus artificial or "
    "sugar-equivalent controls were identified across 8 studies. Natural honeys "
    "produced larger inhibition zones than matched artificial controls "
    "(median paired difference +0.6 mm; Wilcoxon p = 0.002; Figure 3A) and lower "
    "MIC/MBC values (median ratio natural:artificial = 0.81; Figure 3B). "
    "Artificial honey therefore reproduced part, but not all, of natural honey's "
    "antibacterial effect, supporting an osmotic component that is real but "
    "incomplete as an explanatory model."
)
fig("fig3_natural_vs_artificial",
    "Figure 3. Natural versus artificial honey. (A) Paired inhibition zones. "
    "(B) Paired MIC/MBC values; points below the diagonal indicate greater "
    "potency of natural honey.")

h("3.4. Hydrogen peroxide and dilution (RQ3)", 2)
para(
    "Cross-study, honey-level H2O2 measurements correlated weakly and positively "
    "with MIC (rho = +0.46, n = 29, 2 studies; Figure 4). This direction is "
    "opposite to a simple 'more peroxide, more potent' expectation and most likely "
    "reflects confounding across studies (for example, highly active non-peroxide "
    "honeys with low H2O2), so it should not be read as a peroxide-dose effect. "
    "Direct within-study evidence on dilution was sparse but consistent with a "
    "dilution-dependent peroxide mechanism: in one extracted study, H2O2 was "
    "detectable only at 6.25% and 3.12% honey and not at higher concentrations, "
    "and a second study linked glucose oxidase activity, catalase sensitivity and "
    "H2O2 concentration to MIC. The predicted pattern of maximal peroxide "
    "production at intermediate dilution is therefore supported qualitatively, "
    "but the data do not permit estimation of a peak location or even confirmation "
    "of monotonicity; we report this as an evidence gap."
)
fig("fig4_chemistry",
    "Figure 4. Cross-study associations between honey-level physicochemical "
    "parameters and antibacterial outcomes (Spearman rho; MIC on log scale).")

h("3.5. Catalase perturbation and residual activity (RQ4)", 2)
para(
    "Thirteen paired catalase-perturbed observations were extracted from 2 "
    "studies. Catalase-treated honey retained a median 92% of untreated "
    "antibacterial activity (range roughly 77-100%; Figure 5). This indicates "
    "substantial peroxide-independent activity in the honeys tested, but with "
    "only two contributing studies the estimate should be treated as preliminary, "
    "and residual activity cannot be attributed to MGO or any other single "
    "constituent without further evidence."
)
fig("fig5_catalase",
    "Figure 5. Paired antibacterial activity before and after catalase "
    "treatment (13 pairs, 2 studies); residual activity indicates "
    "peroxide-independent components.")

h("3.6. Chemistry versus label prediction (RQ5)", 2)
para(
    "Honey-level physicochemical measurements could be joined to antibacterial "
    "outcomes for 687 observations from 18 studies. Within the largest "
    "single-study block, honey MGO content correlated inversely with MIC "
    "(rho = -0.52, n = 116), consistent with MGO-associated potency. Honey "
    "moisture correlated positively with MIC (rho = +0.32 unfiltered; +0.17 on "
    "the percentage-unit subset), the expected direction if water activity "
    "constrains growth. Honey pH showed no monotone association with MIC "
    "(rho = 0.07) but a moderate inverse association with inhibition-zone size "
    "(rho = -0.52, n = 53). On the largest complete-case block (112 MIC "
    "observations, 3 studies), a linear model using measured pH and moisture "
    "explained 30% of log10(MIC) variance, while a medical/manuka label alone "
    "explained 0%; adding the label to chemistry provided no improvement. "
    "Measured chemistry therefore carried more predictive information than the "
    "label in this subset, though the modest absolute fit and small study count "
    "limit generalization."
)

h("3.7. Organism heterogeneity (RQ6)", 2)
para(
    "MIC distributions differed strongly across organisms (Kruskal-Wallis "
    "H = 173, p = 2.2 x 10-27; Figure 6). Gram-positive organisms tended to be inhibited "
    "at lower honey concentrations (median MIC: *S. epidermidis* 8.1%, "
    "*S. aureus* 12.5%, MRSA 12.5%) than Gram-negative organisms (*E. coli* 20%, "
    "*P. aeruginosa* 20%, Salmonella 20.3%) or fungi (27.5%). Manuka-type honeys "
    "showed a lower median MIC than other honeys on the percentage-unit subset "
    "(15% vs. 18%), but the difference did not reach significance once all "
    "comparable data were included (p = 0.065)."
)
fig("fig6_organisms",
    "Figure 6. MIC distributions by organism group (percentage-unit "
    "studies, log scale).")

para("Table 2. Median MIC (% honey) by organism group, percentage-unit "
     "studies.")
tbl2 = doc.add_table(rows=1, cols=2)
tbl2.style = "Light Grid Accent 1"
tbl2.rows[0].cells[0].text = "Organism group"
tbl2.rows[0].cells[1].text = "Median MIC (%)"
for org, v in R["A6"]["median_MIC_by_organism"].items():
    c = tbl2.add_row().cells
    c[0].text = org
    c[1].text = str(v)
doc.add_paragraph()

h("3.8. Sensitivity analyses", 2)
para(
    "Restricting MIC analyses to the low-risk-of-bias subset left the qualitative "
    "pattern unchanged (6 studies, 185 observations, median MIC 25% reflecting "
    "the organisms assayed in those studies). Concentration-response conclusions "
    "were insensitive to whether auto-extracted or manually curated rows were "
    "used, and MIC distributions were robust to excluding mass-unit endpoints. "
    "The catalase and artificial-honey analyses could not be broadened beyond "
    "the studies that performed those experiments. Table 1 summarizes the "
    "paired mechanistic contrasts."
)

para("Table 1. Paired evidence for mechanistic contrasts.")
tbl = doc.add_table(rows=1, cols=5)
tbl.style = "Light Grid Accent 1"
hdr = tbl.rows[0].cells
for j, t in enumerate(["Contrast", "n pairs", "n studies", "Effect", "p value"]):
    hdr[j].text = t
for row in [
    ("Natural vs artificial honey, zones (mm)", "10", "8+", "median +0.6 mm", "0.002"),
    ("Natural vs artificial honey, MIC ratio", "11", "8+", "median 0.81", "-"),
    ("Catalase residual activity", "13", "2", "median 92% retained", "-"),
    ("Activity vs concentration (series)", "10", "4", "10/10 positive, rho = 1.00", "-"),
    ("MGO vs MIC (within-study)", "116 obs", "1", "rho = -0.52", "<0.001"),
    ("pH vs inhibition zone", "53 obs", "2", "rho = -0.52", "<0.001"),
]:
    c = tbl.add_row().cells
    for j, v in enumerate(row):
        c[j].text = str(v)
doc.add_paragraph()

# ================= 4. DISCUSSION =================
h("4. Discussion", 1)
para(
    "This synthesis supports a dilution-dependent, multi-mechanism account of "
    "honey's antibacterial action. At high concentration, activity is consistent "
    "with dominance of water-activity/osmotic and acidity constraints: artificial "
    "sugar-equivalent honey recapitulated much (though not all) of natural "
    "honey's effect, pH rose monotonically toward neutrality on dilution in the "
    "one full ladder available, and honeys with higher moisture content tended "
    "to have higher MICs. As honey is diluted, these constraints weaken; "
    "independently, glucose oxidase can generate H2O2 under diluted aqueous "
    "conditions, and within-study evidence indicated peroxide detectable only "
    "after substantial dilution " + cite("PMID12804080") +
    ". Finally, the high residual activity after catalase (median 92%) in the two "
    "studies performing that perturbation, together with the within-study "
    "MGO-MIC association, supports a peroxide-independent component in at least "
    "some honeys. The three mechanisms are therefore not simply additive along "
    "the dilution axis: their relative contributions plausibly shift, with "
    "osmotic/acidic activity strongest at high concentration and peroxide "
    "activity most relevant at intermediate dilution."
)
para(
    "The practical implication for the evidence base is that assay concentration "
    "matters mechanistically, not only quantitatively. An MIC measured near the "
    "top of the concentration range may reflect constraints (water activity, "
    "acidity) that disappear on dilution, whereas activity at intermediate "
    "concentrations may be carried by different chemistry entirely. Environments "
    "in which honey is substantially diluted, such as exudative wounds, may "
    "therefore not be well represented by undiluted assays, and the effective "
    "concentration range rather than a single endpoint may be the relevant "
    "exposure metric. This observation is restricted to the biological and "
    "physicochemical phenomenon; no downstream application is implied."
)
para(
    "The cross-study associations should be read cautiously. The positive "
    "H2O2-MIC correlation across studies likely reflects confounding (non-peroxide "
    "honeys can be both potent and low in H2O2) rather than any perverse "
    "peroxide effect; within-study perturbation evidence (catalase, artificial "
    "honey, dilution ladders) is the appropriate level for mechanistic claims, "
    "and we have reserved directional claims for those contrasts. Similarly, the "
    "label-versus-chemistry comparison suggests measured parameters are more "
    "informative than botanical or marketing designations, but the absolute "
    "variance explained remained modest, and MGO, water activity and H2O2 were "
    "measured together in too few honeys to build a joint model."
)
para(
    "Several limitations qualify these findings. First, extraction depended on "
    "open-access full texts and machine-readable tables; the 103 extracted "
    "studies are a subset of the 412 eligible studies, and the extracted subset "
    "may over-represent recent open-access work. Second, concentration-series "
    "data were rare (8 of 103 studies), catalase pairs came from only 2 studies, "
    "and no extractable dataset measured H2O2 across a dilution ladder with "
    "matched antibacterial outcomes; RQ3 is therefore supported only "
    "qualitatively. Third, assay heterogeneity (broth dilution, agar diffusion, "
    "different inocula and media) limits pooling, and we deliberately avoided "
    "formal meta-analytic pooling where measurement bases differed. Fourth, "
    "automated table extraction, although validated against manual curation, may "
    "retain residual errors; all rows carry provenance for audit. Fifth, the "
    "rule-based risk-of-bias framework is a reporting-quality proxy, not a "
    "validated instrument. Finally, the review was not prospectively registered."
)

# ================= 5. CONCLUSIONS =================
h("5. Conclusions", 1)
para(
    "Honey's antibacterial activity rises consistently with concentration in "
    "extractable series, while the physicochemical constraints plausibly "
    "responsible for high-concentration activity weaken on dilution. Natural "
    "honey exceeds sugar-equivalent controls, catalase-resistant residual "
    "activity is substantial where measured, and measured chemistry predicts "
    "outcomes better than honey-type labels. The evidence is consistent with a "
    "dilution-dependent shift between osmotic/acidic, peroxide and non-peroxide "
    "mechanisms, but direct dilution-resolved measurements of H2O2 paired with "
    "antibacterial endpoints remain a clear gap. Future studies should report "
    "full dilution ladders with paired chemistry."
)

# ================= DECLARATIONS =================
h("Author Contributions", 2)
para("[To be completed by the authors.]")
h("Funding", 2)
para("This research received no external funding.")
h("Institutional Review Board Statement", 2)
para("Not applicable; this study synthesizes previously published data.")
h("Informed Consent Statement", 2)
para("Not applicable.")
h("Data Availability Statement", 2)
para(
    "All extracted data, the data dictionary, screening decisions, analysis code "
    "and figure scripts are released with this submission (see accompanying "
    "repository archive). Raw database search responses are included as JSON."
)
h("Acknowledgments", 2)
para("None.")
h("Conflicts of Interest", 2)
para("The authors declare no conflicts of interest.")

# ================= REFERENCES =================
h("References", 1)
for i, r in REX.iterrows():
    doc.add_paragraph(f"{i}. {r['ref']}", style="List Paragraph")
for i, r in RCT.iterrows():
    doc.add_paragraph(f"{CTX_BASE + i + 1}. {r['ref']}", style="List Paragraph")

doc.save(os.path.join(OUT, "manuscript.docx"))
print("wrote manuscript.docx")
