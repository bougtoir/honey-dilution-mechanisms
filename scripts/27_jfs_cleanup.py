"""Post-extraction eligibility cleanup + reference-metadata repair for the
Journal of Food Science retarget (external audit findings).

Exclusions (non-honey interventions captured by the table extractor):
- PMC12379519: 54 rows are inhibition zones of *lactobacillus strains*
  isolated from Ethiopian honey wine (Tej) — the antibacterial agent is
  the bacterium, not honey. Entire study removed from the corpus.
- PMC11120828: 8 rows are zones of *yeast isolates* (Z. rouxii, S. pombe,
  M. chrysoperlae) — same class of contamination. Entire study removed.
- PMC8868498: 1 row labelled "Meropenem" is an antibiotic control arm,
  not honey; the three fir-honeydew honey arms (HS 1-3) are retained.

Metadata repair:
- references_fri.csv author string "Voidarou, C.(." repaired to
  "Voidarou, C." (Crossref given name "Chrysoula (Chrysa)" was truncated
  mid-parenthesis by the initialiser).

Citation-ecology additions (references_fri_context.csv): three closest
prior works verified via Crossref — Nolan et al. 2020 (clinical-grade
systematic review), Aljadi et al. 2025 (medical-grade MIC
meta-analysis), Eryilmaz et al. 2026 (honey microbiota review, IJFM).

Writes qc/JFS_ELIGIBILITY_AUDIT.md with row-level evidence.
"""
import os

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)

DROP_STUDIES = ["PMC12379519", "PMC11120828"]
DROP_ROW = ("PMC8868498", "Meropenem")

ex = pd.read_csv(P("data", "processed", "extraction.csv"))
n0, s0 = len(ex), ex["study_id"].nunique()
mask = ex["study_id"].isin(DROP_STUDIES) | (
    (ex["study_id"] == DROP_ROW[0]) & (ex["honey_label"] == DROP_ROW[1]))
dropped = ex[mask]
ex = ex[~mask]
ex.to_csv(P("data", "processed", "extraction.csv"), index=False)

rob = pd.read_csv(P("data", "processed", "risk_of_bias.csv"))
rob = rob[~rob["study_id"].isin(DROP_STUDIES)]
rob.to_csv(P("data", "processed", "risk_of_bias.csv"), index=False)

rex = pd.read_csv(P("references", "references_fri.csv"))
rex = rex[~rex["pmcid"].isin(DROP_STUDIES)]
for col in ("authors", "ref", "intext"):
    rex[col] = rex[col].str.replace("Voidarou, C.(.", "Voidarou, C.",
                                   regex=False)
rex.to_csv(P("references", "references_fri.csv"), index=False)

ctx = pd.read_csv(P("references", "references_fri_context.csv"))
new = pd.DataFrame([
    {"pmid": "nolan2020", "doi": "10.3390/antibiotics9110766",
     "year": 2020,
     "authors": "Nolan, V.C.; Harrison, J.; Wright, J.E.E.; Cox, J.A.G.",
     "intext": "Nolan et al., 2020",
     "ref": ("Nolan, V.C., Harrison, J., Wright, J.E.E., Cox, J.A.G. "
             "(2020). Clinical Significance of Manuka and Medical-Grade "
             "Honey for Antibiotic-Resistant Infections: A Systematic "
             "Review. Antibiotics, 9(11), 766. "
             "https://doi.org/10.3390/antibiotics9110766"),
     "cr_status": "ok"},
    {"pmid": "aljadi2025", "doi": "10.63883/ijsrisjournal.v4i3.482",
     "year": 2025,
     "authors": "Aljadi, R.A.",
     "intext": "Aljadi et al., 2025",
     "ref": ("Aljadi, R.A. (2025). The Efficacy of Medical-Grade Honey "
             "as an Antimicrobial Agent Against Antibiotic-Resistant "
             "Bacteria: A Systematic Review and Meta-Analysis. "
             "International Journal of Scientific Research and "
             "Innovative Studies, 4(3), 32-37. "
             "https://doi.org/10.63883/ijsrisjournal.v4i3.482"),
     "cr_status": "ok"},
    {"pmid": "eryilmaz2026",
     "doi": "10.1016/j.ijfoodmicro.2026.111686",
     "year": 2026,
     "authors": ("Eryilmaz, H.S.; Gunal-Koroglu, D.; Ozkan, G.; "
                 "Oztekin, S.; Capanoglu, E."),
     "intext": "Eryilmaz et al., 2026",
     "ref": ("Eryilmaz, H.S., Gunal-Koroglu, D., Ozkan, G., Oztekin, "
             "S., Capanoglu, E. (2026). Honey-associated microorganisms "
             "and antimicrobial activity: Probiotic, synbiotic, and "
             "postbiotic properties. International Journal of Food "
             "Microbiology, 452, 111686. "
             "https://doi.org/10.1016/j.ijfoodmicro.2026.111686"),
     "cr_status": "ok"},
])
ctx = pd.concat([ctx[~ctx["pmid"].isin(new["pmid"])], new],
                ignore_index=True)
ctx.to_csv(P("references", "references_fri_context.csv"), index=False)

lines = [
    "# Post-extraction eligibility audit (JFS retarget)",
    "",
    "External audit flagged S11 entries as possibly outside honey-alone",
    "antibacterial eligibility. Row-level inspection of the extraction",
    "contexts confirmed three contamination events:",
    "",
    "| study | evidence | action | rows removed |",
    "|---|---|---|---|",
    "| PMC12379519 | Context header: 'Antibacterial properties of "
    "'lactobacilli' against selected test bacteria'; ST1-ST18 are LAB "
    "strains, not honey arms | study excluded | 54 |",
    "| PMC11120828 | Context header: 'Antimicrobial activity of the "
    "yeast isolates'; Z. rouxii / S. pombe / M. chrysoperlae are yeast "
    "isolates from honey | study excluded | 8 |",
    "| PMC8868498 | 'Meropenem' arm is an antibiotic control; HS 1-3 "
    "fir-honeydew arms retained | row excluded | 1 |",
    "",
    f"Corpus: {s0} studies / {n0} rows -> {ex['study_id'].nunique()} "
    f"studies / {len(ex)} rows. RoB table likewise 102 -> {len(rob)}.",
    "S11 (included-study bibliography) now lists "
    f"{len(rex)} entries. Screening-stage counts (404 eligible incl. "
    "381 include + 23 review_flag) are unchanged: these are "
    "post-extraction eligibility failures, documented here.",
    "",
    "Metadata repair: 'Voidarou, C.(.' -> 'Voidarou, C.' in the two "
    "affected S11 entries (Crossref 10.3390/antibiotics11030422, "
    "10.3390/foods10071568).",
    "",
    "Citation ecology: added Nolan et al. 2020, Aljadi et al. 2025 and "
    "Eryilmaz et al. 2026 (all Crossref-verified) to the context set.",
]
open(P("qc", "JFS_ELIGIBILITY_AUDIT.md"), "w").write("\n".join(lines))
print("\n".join(lines[-8:]))
