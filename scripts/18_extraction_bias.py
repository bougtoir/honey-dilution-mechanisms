"""Phase 2/4H(14): extraction-selection bias.

Compares extracted vs non-extracted eligible studies on available metadata
(year, journal, open-access status, mechanistic feature flags, score) and
writes:
  data/processed/extraction_status.csv     (per-study status + reason)
  results/tables/extracted_vs_nonextracted.csv
  qc/extraction_selection_bias.md
"""
import os
import pandas as pd
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
M = pd.read_csv(os.path.join(ROOT, "results", "tables", "eligibility_extraction_map.csv"))

elig = M[M["elig"].isin(["include", "review_flag"])].copy()
elig["extracted"] = elig["extracted"].astype(bool)

# non-extraction reason (documented, mutually exclusive priority)
def reason(r):
    if r["extracted"]:
        return "extracted"
    if not r["has_pmcid"]:
        return "no PMC full text available"
    if not r["xml_available"]:
        return "PMC record but full-text XML not retrievable"
    return "full text available but no extractable quantitative table"
elig["extraction_status"] = elig.apply(reason, axis=1)
elig[["pmid", "pmcid", "doi", "title", "journal", "year", "elig",
      "extraction_status"]].to_csv(
    os.path.join(ROOT, "data", "processed", "extraction_status.csv"),
    index=False)

ex = elig[elig["extracted"]]
nx = elig[~elig["extracted"]]
rows = []

def add(name, stat, p, n_ex, n_nx):
    rows.append({"comparison": name, "statistic": stat, "p_value": p,
                 "n_extracted": n_ex, "n_nonextracted": n_nx})

# year
mw = stats.mannwhitneyu(ex["year"], nx["year"], alternative="two-sided")
add("publication year (Mann-Whitney)", f"U={mw.statistic:.0f}, medians {ex['year'].median():.0f} vs {nx['year'].median():.0f}",
    mw.pvalue, len(ex), len(nx))
# journal concentration: share in top-10 journals
top10 = elig["journal"].value_counts().head(10).index
for grp, name in ((ex, "extracted"), (nx, "nonextracted")):
    pass
ct = pd.crosstab(elig["journal"].isin(top10), elig["extracted"])
chi = stats.chi2_contingency(ct)
add("top-10 journal membership (chi2)", f"chi2={chi.statistic:.2f}, top10 share {ex['journal'].isin(top10).mean():.2f} vs {nx['journal'].isin(top10).mean():.2f}",
    chi.pvalue, len(ex), len(nx))
# OA status
oa = pd.crosstab(elig["isOpenAccess"].fillna("N") == "Y", elig["extracted"])
chi = stats.chi2_contingency(oa)
add("open-access flag (chi2)", f"chi2={chi.statistic:.2f}, OA share { (ex['isOpenAccess']=='Y').mean():.2f} vs {(nx['isOpenAccess']=='Y').mean():.2f}",
    chi.pvalue, len(ex), len(nx))
# feature flags
for c in ["f_dilution", "f_mic", "f_peroxide", "f_osmotic", "f_mgo", "f_chem",
          "f_zone", "f_orgs", "f_quant", "f_manuka"]:
    ct = pd.crosstab(elig[c], elig["extracted"])
    if ct.shape[0] == 2:
        chi = stats.chi2_contingency(ct)
        add(f"flag {c} (chi2)", f"chi2={chi.statistic:.2f}, {c} share {ex[c].mean():.2f} vs {nx[c].mean():.2f}",
            chi.pvalue, len(ex), len(nx))
# score
mw = stats.mannwhitneyu(ex["score"], nx["score"], alternative="two-sided")
add("relevance score (Mann-Whitney)", f"U={mw.statistic:.0f}, medians {ex['score'].median():.1f} vs {nx['score'].median():.1f}",
    mw.pvalue, len(ex), len(nx))

res = pd.DataFrame(rows)
res.to_csv(os.path.join(ROOT, "results", "tables",
                        "extracted_vs_nonextracted.csv"), index=False)

sig = res[res["p_value"].astype(float) < 0.05]
with open(os.path.join(ROOT, "qc", "extraction_selection_bias.md"), "w") as f:
    f.write("# Extraction-selection bias assessment\n\n")
    f.write(f"Eligible studies: {len(elig)}; quantitatively extracted: {len(ex)} "
            f"({len(ex)/len(elig):.0%}); not extracted: {len(nx)}.\n\n")
    f.write("## Non-extraction reasons\n\n")
    for k, v in elig["extraction_status"].value_counts().items():
        f.write(f"- {k}: {v}\n")
    f.write("\n## Extracted vs non-extracted comparisons\n\n")
    f.write(res.to_markdown(index=False))
    f.write("\n\n## Interpretation\n\n")
    if len(sig):
        f.write("Significant differences (p<0.05): "
                + "; ".join(sig["comparison"]) + ".\n")
        f.write("The extracted subset is therefore NOT a random census of "
                "eligible studies; quantitative claims are subset-specific. "
                "This is stated in the manuscript limitations.\n")
    else:
        f.write("No significant metadata differences detected.\n")
print(res.to_string(index=False))
print(elig["extraction_status"].value_counts())
