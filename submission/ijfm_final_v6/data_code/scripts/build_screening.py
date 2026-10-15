"""Phase 2a: screening. Applies eligibility criteria to deduplicated records.

Eligibility (PICOS):
  - Population/subject: any bacterial/fungal microorganism tested in vitro
    (food-borne, clinical, or reference strains) OR physicochemical data on honey.
  - Intervention/exposure: honey (any type) tested at >=1 stated concentration,
    or mechanistic perturbation (catalase, artificial/sugar-equivalent honey,
    H2O2 measurement, aw/pH measurement paired with activity).
  - Outcome: quantitative antibacterial/bacteriostatic readout
    (MIC, MBC, inhibition zone, % inhibition, growth, OD) or measured chemistry.
  - Design: in-vitro experimental study OR dataset. Excludes: human/animal
    clinical outcomes only, reviews (screened separately for citation mining),
    non-English without abstract, irrelevant topics (e.g. honey adulteration,
    sensory, plants).

Two-stage: (1) title screen, (2) abstract screen (Europe PMC core results carry
abstractText in raw JSON). Outputs data/processed/screening_decisions.csv.
"""
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "search"
PROC = ROOT / "data" / "processed"

records = pd.read_csv(PROC / "search_records.csv").fillna("")

# pull abstracts from europepmc raw files
abs_map = {}
for f in RAW.glob("europepmc__*.json"):
    try:
        data = json.loads(f.read_text())
    except Exception:  # noqa: BLE001
        continue
    for r in data.get("resultList", {}).get("result", []):
        key = (r.get("doi") or "").lower() or ("pmid:" + str(r.get("pmid", "")))
        if key and r.get("abstractText"):
            abs_map[key] = re.sub(r"<[^>]+>", " ", r["abstractText"])

records["doi"] = records["doi"].astype(str).fillna("")
records["pmid"] = records["pmid"].astype(str).str.replace(r"\.0$", "", regex=True).fillna("")
records["key"] = records["doi"].where(records["doi"].ne(""), "pmid:" + records["pmid"])
records["abstract"] = records["key"].map(abs_map).fillna("")

# enrich abstracts for PubMed records lacking one (efetch, chunks of 200)
import urllib.request
import urllib.parse
import time
need_abs = records[(records["abstract"] == "") & (records["pmid"] != "")]["pmid"].unique()
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
fetched = {}
for i in range(0, len(need_abs), 200):
    ids = ",".join(need_abs[i:i + 200])
    url = (f"{EUTILS}/efetch.fcgi?db=pubmed&retmode=xml&id={ids}")
    dest = RAW / f"pubmed_efetch_abs_{i}.xml"
    req = urllib.request.Request(url, headers={"User-Agent": "honey-dilution-review/1.0"})
    try:
        body = urllib.request.urlopen(req, timeout=120).read()
        dest.write_bytes(body)
        import xml.etree.ElementTree as ET
        root = ET.fromstring(body)
        for art in root.iter("PubmedArticle"):
            pmid = art.findtext(".//PMID")
            txt = " ".join(t.text or "" for t in art.iter("AbstractText"))
            if pmid and txt:
                fetched[pmid] = txt
    except Exception as e:  # noqa: BLE001
        print("efetch fail", i, e)
    time.sleep(0.4)
records.loc[records["abstract"] == "", "abstract"] = records["pmid"].map(fetched).fillna("")

HONEY = re.compile(r"honey|manuka|melipona|stingless bee|apiary", re.I)
ANTIBAC = re.compile(
    r"antibacter|antimicrob|bactericid|bacteriostat|minimum inhibitory|"
    r"\bMIC\b|\bMBC\b|zone of inhibition|inhibition zone|bacterial (growth|inhibition)|"
    r"anti-biofilm|antibiofilm|anti-microbial|bactericidal|bacterial count|"
    r"pathogen.*(inhibit|growth)|inhibit.*(bacter|pathogen)", re.I)
MECH = re.compile(
    r"dilut|concentration|peroxide|H2O2|hydrogen peroxide|glucose oxidase|catalase|"
    r"methylglyoxal|MGO|water activity|osmolar|osmotic|pH|artificial honey|"
    r"sugar solution|sugar control|phenolic|non-?peroxide", re.I)
EXCLUDE_HARD = re.compile(
    r"adulterat|authentication|sensory|pollen analys|melissopalynolog|"
    r"propolis(?!.*honey)|geographic origin|fingerprint|nectar|beehive air|"
    r"clinical trial|randomized|wound healing patient|case report|"
    r"biopesticide|aphid|plant pathogen|phytopathog|fungicide(?!.*honey)|"
    r"in vivo(?!.*in vitro)", re.I)
REVIEW = re.compile(r"\breview\b|systematic review|meta-analysis|scoping", re.I)
DATASET_SRC = {"zenodo", "figshare", "dryad"}


def screen(row):
    t = row["title"]
    a = row["abstract"]
    text = t + " " + a
    if row["source"] in DATASET_SRC:
        ok = bool(HONEY.search(text) and (ANTIBAC.search(text) or MECH.search(text)))
        return ("eligible_dataset" if ok else "exclude_irrelevant",
                "data repository record; retained for data mining" if ok else "topic mismatch")
    if not HONEY.search(text):
        return "exclude_no_honey", "honey not in title/abstract"
    if EXCLUDE_HARD.search(text) and not MECH.search(text):
        return "exclude_topic", "off-scope topic per exclusion regex"
    is_review = bool(REVIEW.search(t) or REVIEW.search(a[:200]))
    if not ANTIBAC.search(text):
        if MECH.search(text):
            return "eligible_mechanism_only", "mechanistic/chemistry variable without explicit antibacterial outcome"
        return "exclude_no_outcome", "no antibacterial outcome or mechanistic variable"
    if is_review:
        return "review_citation_mining", "review retained for citation mining, not extraction"
    if not a:
        return "eligible_title_only", "no abstract available; eligible by title, needs full-text check"
    quant = bool(re.search(r"\d", a))
    return ("eligible" if quant else "eligible_weak",
            "antibacterial quantitative signal in abstract" if quant else "antibacterial outcome, weak quantitative signal")


res = records.apply(screen, axis=1, result_type="expand")
records["screening_decision"] = res[0]
records["exclusion_reason"] = res[1]
records.to_csv(PROC / "screening_decisions.csv", index=False)

summ = records["screening_decision"].value_counts()
with open(ROOT / "qc" / "screening_summary.md", "w") as f:
    f.write("# Screening summary\n\n")
    f.write(f"Deduplicated records screened: {len(records)}\n\n")
    for k, v in summ.items():
        f.write(f"- {k}: {v}\n")
    f.write("\nCriteria documented in `scripts/build_screening.py` (PICOS block).\n")
print(summ)
