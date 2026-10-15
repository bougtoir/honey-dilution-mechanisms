"""Targeted supplementary search (citation mining): author+keyword PubMed lookups
for landmark honey antibacterial studies potentially missed by the main queries.
Appends records to data/interim/all_records.csv and logs to search_log.csv.
"""
import json
import os
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import datetime

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TODAY = datetime.date.today().isoformat()

LOOKUPS = [
    'Blair SE[Author] AND honey',
    'Irish J[Author] AND honey AND antibacterial',
    'Roberts AEL[Author] AND honey',
    'Henriques AF[Author] AND honey',
    'Maddocks SE[Author] AND honey',
    'Allen KL[Author] AND honey AND antibacterial',
    'Molan PC[Author] AND honey',
    'Voidarou C[Author] AND honey',
    'Cooper RA[Author] AND honey AND antibacterial',
    'Carnwath R[Author] AND honey',
    'Alnaqdy[Author] AND honey',
    'Lusby PE[Author] AND honey',
    'Jenkins R[Author] AND honey AND antibacterial',
    'Wilkinson JM[Author] AND honey',
    'Brudzynski K[Author] AND honey AND antibacterial',
    'Bucekova M[Author] AND honey',
    'Kwakman PHS[Author] AND honey',
    'Johnston M[Author] AND honey AND antibacterial',
    'Girma A[Author] AND honey',
    'Masoura M[Author] AND honey',
    'Grecka K[Author] AND honey',
    'Nolan VC[Author] AND honey',
    'Oryan A[Author] AND honey AND antibacterial',
    'Cokcetin NN[Author] AND honey',
    'Bouacha M[Author] AND honey',
    'Combarros-Fuertes P[Author] AND honey',
    'Shepherd P[Author] AND honey',
    'Carter DA[Author] AND honey',
]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "devin-sr/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def main():
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    all_ids = set()
    per_q = {}
    for q in LOOKUPS:
        es = f"{base}esearch.fcgi?db=pubmed&retmode=json&retmax=200&term={urllib.parse.quote(q)}"
        res = json.loads(get(es).decode())
        ids = res["esearchresult"].get("idlist", [])
        per_q[q] = ids
        all_ids.update(ids)
        time.sleep(0.35)
    print("unique pmids:", len(all_ids))

    recs = []
    ids = list(all_ids)
    for chunk in [ids[i:i + 200] for i in range(0, len(ids), 200)]:
        ef = f"{base}esummary.fcgi?db=pubmed&retmode=json&id={','.join(chunk)}"
        summ = json.loads(get(ef).decode())
        for pid in chunk:
            r = summ["result"].get(pid, {})
            recs.append({
                "source_db": "pubmed_citemine",
                "pmid": pid,
                "doi": next((a["value"] for a in r.get("articleids", []) if a.get("idtype") == "doi"), None),
                "title": r.get("title"),
                "journal": r.get("fulljournalname"),
                "year": (r.get("pubdate") or "")[:4],
                "authors": "; ".join(a.get("name", "") for a in r.get("authors", [])[:6]),
                "pubtype": "; ".join(r.get("pubtype", [])),
            })
        time.sleep(0.35)

    xml_txt = get(f"{base}efetch.fcgi?db=pubmed&retmode=xml&id={','.join(ids)}").decode("utf-8", "replace")
    abstr = {}
    try:
        tree = ET.fromstring(xml_txt)
        for art in tree.iter("PubmedArticle"):
            pmid = art.findtext(".//PMID")
            abstr[pmid] = " ".join("".join(t.itertext()) for t in art.iter("AbstractText"))
    except ET.ParseError:
        pass
    for r in recs:
        r["abstract"] = abstr.get(r["pmid"], "")
        r["query"] = "citation_mining_author_lookup"
        r["query_idx"] = 99

    df_new = pd.DataFrame(recs)
    df_new.to_csv(os.path.join(ROOT, "data", "raw", "search", "citation_mining.json.csv"), index=False)

    df = pd.read_csv(os.path.join(ROOT, "data", "interim", "all_records.csv"))
    df_all = pd.concat([df, df_new], ignore_index=True)
    df_all.to_csv(os.path.join(ROOT, "data", "interim", "all_records.csv"), index=False)

    log = pd.read_csv(os.path.join(ROOT, "logs", "search_log.csv"))
    log.loc[len(log)] = {"db": "pubmed_citemine", "query_idx": 99,
                         "query": "; ".join(LOOKUPS), "date": TODAY,
                         "hits": len(all_ids), "retrieved": len(recs), "error": ""}
    log.to_csv(os.path.join(ROOT, "logs", "search_log.csv"), index=False)
    print("appended", len(recs))


if __name__ == "__main__":
    main()
