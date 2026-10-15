#!/usr/bin/env python3
"""Adversarial-review provenance cleanup (Gate 2).

Two corrections found by auditing every included study against its scope:

1. STUDY-LEVEL EXCLUSIONS: papers whose extracted records do not quantify
   natural-honey antibacterial activity (non-honey bee product, peptide
   fraction, review article, or no genuine honey rows).
2. ROW-LEVEL FILTERING in retained studies: comparator rows that are not
   honey (antibiotics, essential oils, extracts, nanoparticles, combination
   arms, sugar/vehicle controls) were captured by table parsing. They are
   not honey observations and are removed.

Re-audit whitelist: for a few studies the row label alone cannot identify
the honey arm; keep only explicitly honey-labelled rows there.
"""
import os
import re
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)

# --- studies excluded at full-text audit (not honey-specific primary data) ---
DROP_STUDIES = {
    "PMC10223701": "bee venom / venom extracts; no honey rows",
    "PMC9311549":  "Saudi propolis MICs (mg/mL); not honey",
    "PMC12092607": "Egyptian propolis IZDs; no honey rows",
    "PMC8709083":  "review article (bee venom/honey/royal jelly); not primary in-vitro data",
    "PMC4382210":  "isolated Jellein peptide MICs (ug/ml); not whole-honey dilution exposure",
    "PMC12891082": "Biocidin botanical blend; not honey",
    "PMC9951885":  "enriched creamed honey paper; only antibiotic control rows extracted, no honey rows",
    "PMC11585709": "copper-nanocomposite study; honey only incidental zero-IZD control",
}

# --- per-study row whitelist (label regex to KEEP) for ambiguous tables ---
KEEP_ONLY = {
    "PMC9703798": r"^Honey alone",
    "PMC5489923": r"^Honey \(%\)",
    "PMC11596660": r"Fennel Honey",
    "PMC11851655": r"^(Linden|Chestnut) honey$",
    "PMC10622673": r"^WT MICs$",  # honey-alone MIC column of the WT table
}
# --- generic non-honey row labels dropped anywhere ---
BAD_LABEL = re.compile(
    r"propolis|venom|royal|jellein|chloramphenicol|gentamicin|tetracycline|"
    r"ampicillin|ciprofloxacin|streptomycin|penicillin|amoxicillin|"
    r"erythromycin|vancomycin|azithromycin|antibiotic|nanocomposite|"
    r"Cu\d|AgNP|silver|nanoparticle|cinnamon|MCEO|essential oil|mixture|"
    r"combination|FIC\b|carbohydrate control|control \(\W|control solution|"
    r"ether extract|methanol extract|Biocidin",
    re.I,
)

def main():
    sp = P("data/processed/studies.csv")
    ep = P("data/processed/extraction.csv")
    S = pd.read_csv(sp)
    E = pd.read_csv(ep)
    n_st0 = int(S["extracted"].sum())
    n_rows0 = len(E)

    # study-level exclusion
    S.loc[S["pmcid"].isin(DROP_STUDIES), ["eligible", "extracted"]] = False
    E = E[~E["pmcid"].isin(DROP_STUDIES)].copy()

    # row-level: whitelist for ambiguous studies
    keep_mask = pd.Series(True, index=E.index)
    for pid, pat in KEEP_ONLY.items():
        m = E["pmcid"].eq(pid)
        keep_mask &= ~(m & ~E["honey_label"].astype(str).str.contains(pat, regex=True))
    # generic bad labels outside whitelist studies
    wl = E["pmcid"].isin(KEEP_ONLY)
    keep_mask &= ~(~wl & E["honey_label"].astype(str).str.contains(BAD_LABEL, na=False))
    E = E[keep_mask].copy()

    # studies left with zero extracted rows -> un-extract (still audited eligible flag False)
    zero = set(S.loc[S["extracted"] == True, "pmcid"]) - set(E["pmcid"])
    if zero:
        S.loc[S["pmcid"].isin(zero), "extracted"] = False
        print("studies with no honey rows after filtering:", zero)

    S.to_csv(sp, index=False)
    E.to_csv(ep, index=False)

    n_st1 = int(S["extracted"].sum())
    print(f"extracted studies {n_st0} -> {n_st1} (excluded {len(DROP_STUDIES)} + {len(zero)} empty)")
    print(f"extraction rows {n_rows0} -> {len(E)} (removed {n_rows0-len(E)} non-honey rows)")

if __name__ == "__main__":
    main()
