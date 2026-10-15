"""Phase 1 search update: query PubMed, Europe PMC, Crossref, Dryad, Zenodo,
Figshare. Persist raw JSON responses under data/raw/search/ and record every
download in data/raw/ACQUISITION_LEDGER.csv.

Outputs:
  data/processed/search_records.csv  (deduplicated record table)
  qc/search_update_log.md
"""
import hashlib
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "search"
RAW.mkdir(parents=True, exist_ok=True)
LEDGER = ROOT / "data" / "raw" / "ACQUISITION_LEDGER.csv"
PROC = ROOT / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)
QC = ROOT / "qc"
QC.mkdir(exist_ok=True)

UA = {"User-Agent": "honey-dilution-review/1.0 (mailto:bougtoir@gmail.com)"}
NOW = datetime.now(timezone.utc).isoformat()

QUERIES = [
    "honey dilution antibacterial",
    "honey concentration antibacterial",
    "honey hydrogen peroxide dilution",
    "honey glucose oxidase dilution",
    "honey catalase antibacterial",
    "artificial honey antibacterial",
    "sugar equivalent honey antibacterial",
    "honey water activity antibacterial",
    "honey methylglyoxal MIC",
    "honey physicochemical antibacterial",
    "medical grade honey concentration antibacterial",
    "manuka honey dilution hydrogen peroxide",
    "honey minimum inhibitory concentration bacteria",
    "honey osmotic antibacterial mechanism",
]


def fetch(url, dest, source, query="", binary=False):
    req = urllib.request.Request(url, headers=UA)
    body = urllib.request.urlopen(req, timeout=60).read()
    dest.write_bytes(body)
    rec = {
        "source": source, "query_or_id": query, "url": url,
        "retrieved_utc": NOW, "file": str(dest.relative_to(ROOT)),
        "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
        "license": "public API response (metadata)", "notes": "",
    }
    new = pd.DataFrame([rec])
    if LEDGER.exists():
        old = pd.read_csv(LEDGER)
        new = pd.concat([old, new], ignore_index=True)
    new.to_csv(LEDGER, index=False)
    return body


def slug(s):
    return "".join(c if c.isalnum() else "_" for c in s)[:60]


records = []


def add_record(source, rid, title, year, doi, pmid, pmcid, journal, query):
    records.append({
        "source": source, "source_id": str(rid), "title": title,
        "year": year, "doi": (doi or "").lower().strip(), "pmid": str(pmid or ""),
        "pmcid": str(pmcid or ""), "journal": journal, "query": query,
    })


def safe_name(source, query):
    return RAW / f"{source}__{slug(query)}.json"


# ---------- PubMed (E-utilities) ----------
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
for q in QUERIES:
    term = f'({q}) AND (honey[Title/Abstract] OR honey[MeSH Terms])'
    url = f"{EUTILS}/esearch.fcgi?db=pubmed&retmax=200&retmode=json&term={urllib.parse.quote(term)}"
    try:
        data = json.loads(fetch(url, safe_name("pubmed_esearch", q), "pubmed", q))
        ids = data.get("esearchresult", {}).get("idlist", [])
        if ids:
            su = f"{EUTILS}/esummary.fcgi?db=pubmed&retmode=json&id={','.join(ids)}"
            sdata = json.loads(fetch(su, RAW / f"pubmed_esummary__{slug(q)}.json", "pubmed", q))
            for pid in ids:
                r = sdata.get("result", {}).get(pid, {})
                doi = ""
                for aid in r.get("articleids", []):
                    if aid.get("idtype") == "doi":
                        doi = aid.get("value", "")
                add_record("pubmed", pid, r.get("title", ""), str(r.get("pubdate", ""))[:4],
                           doi, pid, "", r.get("fulljournalname", ""), q)
        time.sleep(0.4)
    except Exception as e:  # noqa: BLE001
        print("pubmed fail", q, e)

# ---------- Europe PMC ----------
EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
for q in QUERIES:
    query = f'({q}) AND (honey)'
    url = f"{EPMC}?query={urllib.parse.quote(query)}&format=json&pageSize=200&resultType=core"
    try:
        data = json.loads(fetch(url, safe_name("europepmc", q), "europepmc", q))
        for r in data.get("resultList", {}).get("result", []):
            add_record("europepmc", r.get("id", ""), r.get("title", ""), r.get("pubYear", ""),
                       r.get("doi", ""), r.get("pmid", ""), r.get("pmcid", ""),
                       r.get("journalTitle", ""), q)
        time.sleep(0.4)
    except Exception as e:  # noqa: BLE001
        print("epmc fail", q, e)

# ---------- Crossref ----------
for q in QUERIES:
    url = ("https://api.crossref.org/works?rows=100&select=DOI,title,container-title,published,author,type"
           f"&query={urllib.parse.quote(q + ' honey')}")
    try:
        data = json.loads(fetch(url, safe_name("crossref", q), "crossref", q))
        for it in data.get("message", {}).get("items", []):
            title = (it.get("title") or [""])[0]
            year = ""
            dp = it.get("published", {}).get("date-parts", [[None]])
            if dp and dp[0] and dp[0][0]:
                year = str(dp[0][0])
            add_record("crossref", it.get("DOI", ""), title, year,
                       it.get("DOI", ""), "", "",
                       (it.get("container-title") or [""])[0], q)
        time.sleep(0.4)
    except Exception as e:  # noqa: BLE001
        print("crossref fail", q, e)

# ---------- Data repositories (datasets mentioning honey antibacterial) ----------
DSRC = [
    ("zenodo", "https://zenodo.org/api/records?q={q}&size=25"),  # unauthenticated max page size is 25
    ("figshare", None),  # POST API; handled separately
    ("dryad", "https://datadryad.org/api/v2/search?query={q}"),
]
for q in ["honey antibacterial", "honey dilution", "honey hydrogen peroxide", "manuka honey MIC"]:
    # Zenodo
    try:
        url = DSRC[0][1].format(q=urllib.parse.quote(q))
        data = json.loads(fetch(url, safe_name("zenodo", q), "zenodo", q))
        for h in data.get("hits", {}).get("hits", []):
            md = h.get("metadata", {})
            add_record("zenodo", h.get("id", ""), md.get("title", ""),
                       str(md.get("publication_date", ""))[:4], h.get("doi", ""), "", "",
                       "Zenodo dataset", q)
        time.sleep(0.4)
    except Exception as e:  # noqa: BLE001
        print("zenodo fail", q, e)
    # Figshare (POST)
    try:
        req = urllib.request.Request(
            "https://api.figshare.com/v2/articles/search",
            data=json.dumps({"search_for": q, "limit": 50}).encode(),
            headers={**UA, "Content-Type": "application/json"})
        body = urllib.request.urlopen(req, timeout=60).read()
        dest = safe_name("figshare", q)
        dest.write_bytes(body)
        rec = {"source": "figshare", "query_or_id": q,
               "url": "https://api.figshare.com/v2/articles/search (POST)",
               "retrieved_utc": NOW, "file": str(dest.relative_to(ROOT)),
               "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
               "license": "public API response (metadata)", "notes": ""}
        led = pd.read_csv(LEDGER) if LEDGER.exists() else pd.DataFrame()
        pd.concat([led, pd.DataFrame([rec])], ignore_index=True).to_csv(LEDGER, index=False)
        for a in json.loads(body):
            add_record("figshare", a.get("id", ""), a.get("title", ""),
                       str(a.get("published_date", ""))[:4], a.get("doi", ""), "", "",
                       "Figshare dataset", q)
        time.sleep(0.4)
    except Exception as e:  # noqa: BLE001
        print("figshare fail", q, e)
    # Dryad
    try:
        url = DSRC[2][1].format(q=urllib.parse.quote(q))
        data = json.loads(fetch(url, safe_name("dryad", q), "dryad", q))
        for d in data.get("_embedded", {}).get("stash:datasets", []):
            add_record("dryad", d.get("identifier", ""), d.get("title", ""),
                       str(d.get("publicationDate", ""))[:4], d.get("identifier", ""), "", "",
                       "Dryad dataset", q)
        time.sleep(0.4)
    except Exception as e:  # noqa: BLE001
        print("dryad fail", q, e)

df = pd.DataFrame(records).drop_duplicates()
df["key"] = df["doi"].where(df["doi"].ne(""), "pmid:" + df["pmid"])
df.loc[df["key"].eq("pmid:"), "key"] = df["source"] + ":" + df["source_id"]
df.to_csv(PROC / "search_records_raw.csv", index=False)
dedup = df.drop_duplicates("key").drop(columns="key")
dedup.to_csv(PROC / "search_records.csv", index=False)

with open(QC / "search_update_log.md", "w") as f:
    f.write(f"# Search update log\n\nRun UTC: {NOW}\n\n")
    f.write(f"Queries ({len(QUERIES)} core + repository queries): exact strings in `scripts/search_literature.py`.\n\n")
    f.write(f"Raw records: {len(df)}; deduplicated: {len(dedup)}.\n\n")
    f.write("Deduplication key: DOI, else PMID, else source id.\n\n")
    f.write("Raw API responses: `data/raw/search/`; ledger: `data/raw/ACQUISITION_LEDGER.csv`.\n")

print("records:", len(df), "dedup:", len(dedup))
