"""Deduplicate + stage-1/stage-2 screening for the honey dilution review.

Produces:
  data/interim/unique_records.csv     - deduplicated records
  data/interim/screened.csv           - with screen1 decisions + reasons
  data/interim/candidates.csv         - stage-2 candidates for manual eligibility review
  logs/prisma_counts.json             - counts for PRISMA flow
"""
import json
import os
import re

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def norm_title(t):
    if not isinstance(t, str):
        return ""
    return re.sub(r"[^a-z0-9]", "", t.lower())


BACTERIAL = re.compile(
    r"(antibacterial|antimicrobial|bactericid|bacteriostat|inhibitor?y|inhibition|"
    r"minimum inhibitory|\bMIC\b|anti-bacterial|staphylococc|pseudomon|escherichia|"
    r"e\. ?coli|MRSA|streptococc|enterococc|klebsiella|bacillus|salmonella|listeria|"
    r"proteus|helicobacter|acinetobacter|burkholderia|bacterial growth|bacteria)", re.I)

HONEY = re.compile(r"\bhoney\b|manuka|medihoney", re.I)

# obvious non-primary / off-scope markers
REVIEW_TYPE = re.compile(r"review|meta-analysis|systematic|editorial|comment|letter|"
                         r"news|erratum|correction|retraction|book|conference", re.I)
OFFTOPIC = re.compile(
    r"(adulterat|authenticity|authentication|pollen analysis|melissopalynolog|"
    r"pesticide|residue|heavy metal|quality control|physicochemical characteri|"
    r"beekeep|colony collapse|varroa|pollinat|apitherapy|honeybee health|"
    r"geographical origin|botanical origin determination|classification of honey|"
    r"anticancer|anti-?cancer|antioxidant only|wound healing clinical|"
    r"randomi[sz]ed|clinical trial|dermatitis|gel formulation|hydrogel|"
    r"nanoparticle|electrospun|scaffold|film|composite dressing)", re.I)

# mechanistic-relevance flags (stage 2 priority)
MECH = re.compile(
    r"(dilution|diluted|concentration|water activity|\ba_?w\b|osmotic|osmolarity|"
    r"hydrogen peroxide|H2O2|glucose oxidase|catalase|methylglyoxal|MGO|"
    r"non-?peroxide|artificial honey|sugar solution|sugar control|"
    r"minimum inhibitory|\bMIC\b|\bMBC\b|inhibition zone|zone of inhibition|"
    r"time-?kill|growth curve|IC50|IC90|Brix|moisture content|phenolic|flavonoid|"
    r"medical grade|gamma irradiat|steriliz)", re.I)


def main():
    df = pd.read_csv(os.path.join(ROOT, "data", "interim", "all_records.csv"))
    df["doi_norm"] = df["doi"].fillna("").str.lower().str.strip()
    df["pmid_norm"] = df["pmid"].fillna("").astype(str).str.replace(r"\.0$", "", regex=True)
    df["title_norm"] = df["title"].map(norm_title)

    # dedupe: prefer record with abstract; key = doi or pmid or title
    df["has_abs"] = df["abstract"].fillna("").str.len() > 50
    df = df.sort_values("has_abs", ascending=False)
    df["key"] = df["doi_norm"]
    df.loc[df["key"] == "", "key"] = "pmid:" + df.loc[df["key"] == "", "pmid_norm"]
    df.loc[df["key"] == "pmid:", "key"] = "title:" + df.loc[df["key"] == "pmid:", "title_norm"]
    n_raw = len(df)
    uniq = df.drop_duplicates("key").copy()
    n_dup = n_raw - len(uniq)

    # merge EPMC metadata (pmcid / OA) onto records sharing doi/pmid
    epmc = df[df["source_db"] == "europepmc"][["doi_norm", "pmid_norm", "pmcid", "isOpenAccess", "inEPMC"]]
    epmc = epmc.dropna(subset=["pmcid"]).drop_duplicates("pmcid")
    epmc_d = epmc[["doi_norm", "pmcid"]].dropna()
    epmc_d = epmc_d[epmc_d["doi_norm"] != ""].drop_duplicates("doi_norm")
    uniq = uniq.merge(epmc_d, on="doi_norm", how="left", suffixes=("", "_epmc"))
    epmc_pmid = epmc[["pmid_norm", "pmcid"]].dropna()
    epmc_pmid = epmc_pmid[epmc_pmid["pmid_norm"] != ""].drop_duplicates("pmid_norm")
    uniq = uniq.merge(epmc_pmid, on="pmid_norm", how="left", suffixes=("", "_p2"))
    uniq["pmcid"] = uniq["pmcid"].combine_first(uniq.get("pmcid_epmc")).combine_first(uniq.get("pmcid_p2"))
    uniq = uniq.drop(columns=[c for c in uniq.columns if c.endswith("_epmc") or c.endswith("_p2")])

    txt = (uniq["title"].fillna("") + " " + uniq["abstract"].fillna(""))
    uniq["s1_review"] = uniq["pubtype"].fillna("").map(lambda s: bool(REVIEW_TYPE.search(s))) | \
        txt.str.contains(r"\breview\b", case=False, regex=True) & ~txt.str.contains(BACTERIAL)
    uniq["s1_no_honey"] = ~txt.map(lambda s: bool(HONEY.search(s)))
    uniq["s1_no_bacteria"] = ~txt.map(lambda s: bool(BACTERIAL.search(s)))
    uniq["s1_offtopic"] = txt.map(lambda s: bool(OFFTOPIC.search(s))) & ~txt.str.contains("antibacterial|antimicrobial|inhibit", case=False)
    uniq["s1_no_abstract"] = ~uniq["has_abs"]

    uniq["screen1"] = "include"
    uniq.loc[uniq["s1_no_honey"], "screen1"] = "exclude: not about honey"
    uniq.loc[uniq["s1_no_bacteria"], "screen1"] = "exclude: no antibacterial outcome"
    uniq.loc[uniq["s1_review"] & (uniq["screen1"] == "include"), "screen1"] = "exclude: review/non-primary"
    uniq.loc[uniq["s1_offtopic"] & (uniq["screen1"] == "include"), "screen1"] = "exclude: off-topic"
    uniq.loc[uniq["s1_no_abstract"] & (uniq["screen1"] == "include"), "screen1"] = "exclude: no abstract"

    uniq["mech_flag"] = txt.map(lambda s: bool(MECH.search(s)))
    uniq.to_csv(os.path.join(ROOT, "data", "interim", "screened.csv"), index=False)

    cand = uniq[(uniq["screen1"] == "include") & uniq["mech_flag"]].copy()
    cand = cand.sort_values("year")
    cand[["pmid", "pmcid", "doi", "title", "journal", "year", "authors",
          "isOpenAccess", "abstract"]].to_csv(
        os.path.join(ROOT, "data", "interim", "candidates.csv"), index=False)

    counts = {
        "raw_records": int(n_raw),
        "duplicates_removed": int(n_dup),
        "unique_screened": int(len(uniq)),
        "excluded_screen1": int((uniq["screen1"] != "include").sum()),
        "screen1_passed": int((uniq["screen1"] == "include").sum()),
        "mech_candidates": int(len(cand)),
        "candidates_with_pmcid": int(cand["pmcid"].notna().sum()),
    }
    with open(os.path.join(ROOT, "logs", "prisma_counts.json"), "w") as f:
        json.dump(counts, f, indent=1)
    print(json.dumps(counts, indent=1))


if __name__ == "__main__":
    main()
