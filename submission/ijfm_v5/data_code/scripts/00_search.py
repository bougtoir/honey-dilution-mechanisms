"""Reproducible literature search: PubMed (E-utilities), Europe PMC, Crossref.

Every query, hit count, retrieval date and raw record is written to
data/raw/search/ and a log to logs/search_log.csv.
"""
import json
import os
import time
import datetime
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw", "search")
LOGS = os.path.join(ROOT, "logs")
os.makedirs(RAW, exist_ok=True)
os.makedirs(LOGS, exist_ok=True)

TODAY = datetime.date.today().isoformat()
TOOL_EMAIL = "devin@example.org"  # non-personal contact for NCBI

QUERIES = {
    "pubmed": [
        'honey[Title/Abstract] AND (antibacterial[Title/Abstract] OR antimicrobial[Title/Abstract]) AND ("minimum inhibitory"[Title/Abstract] OR dilution[Title/Abstract])',
        'honey[Title/Abstract] AND (bacteriostatic[Title/Abstract] OR bactericidal[Title/Abstract]) AND (dilution[Title/Abstract] OR concentration[Title/Abstract])',
        'honey[Title/Abstract] AND ("hydrogen peroxide"[Title/Abstract] OR "glucose oxidase"[Title/Abstract] OR peroxide[Title/Abstract] OR catalase[Title/Abstract]) AND (bacteria*[Title/Abstract] OR antimicrobial[Title/Abstract])',
        'honey[Title/Abstract] AND ("water activity"[Title/Abstract] OR osmotic[Title/Abstract] OR osmolarity[Title/Abstract] OR "artificial honey"[Title/Abstract] OR "sugar solution"[Title/Abstract]) AND (antibacterial[Title/Abstract] OR antimicrobial[Title/Abstract] OR inhibitory[Title/Abstract])',
        'honey[Title/Abstract] AND (methylglyoxal[Title/Abstract] OR MGO[Title/Abstract] OR "non-peroxide"[Title/Abstract] OR "nonperoxide"[Title/Abstract]) AND (antibacterial[Title/Abstract] OR antimicrobial[Title/Abstract] OR bactericidal[Title/Abstract])',
        'honey[Title/Abstract] AND ("inhibition zone"[Title/Abstract] OR "zone of inhibition"[Title/Abstract] OR "well diffusion"[Title/Abstract] OR "agar dilution"[Title/Abstract] OR "broth dilution"[Title/Abstract])',
    ],
    "europepmc": [
        'honey AND (antibacterial OR antimicrobial OR bacteriostatic) AND (dilution OR concentration OR "minimum inhibitory" OR MIC) IN_EPMC:y OPEN_ACCESS:y',
        'honey AND ("hydrogen peroxide" OR "glucose oxidase" OR catalase) AND (antibacterial OR antimicrobial)',
        'honey AND ("water activity" OR osmotic OR "artificial honey" OR "sugar solution") AND (antibacterial OR antimicrobial OR inhibitory)',
        'honey AND (methylglyoxal OR MGO OR "non-peroxide") AND (antibacterial OR antimicrobial OR bactericidal)',
        'honey AND ("inhibition zone" OR "zone of inhibition" OR "well diffusion" OR "agar dilution" OR "broth microdilution") AND (MIC OR antibacterial OR antimicrobial)',
    ],
    "crossref": [
        'honey antibacterial dilution minimum inhibitory concentration',
        'honey hydrogen peroxide antibacterial activity dilution',
        'honey water activity osmotic antibacterial artificial honey',
        'manuka honey methylglyoxal antibacterial non-peroxide',
        'honey inhibition zone antibacterial concentration',
    ],
}


def urlopen_json(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "devin-sr/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            if i == retries - 1:
                raise
            time.sleep(2 * (i + 1))


def urlopen_text(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "devin-sr/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", errors="replace")
        except Exception:
            if i == retries - 1:
                raise
            time.sleep(2 * (i + 1))


def pubmed_query(q, qidx):
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    es = f"{base}esearch.fcgi?db=pubmed&retmode=json&retmax=500&email={TOOL_EMAIL}&term={urllib.parse.quote(q)}"
    res = urlopen_json(es)
    count = int(res["esearchresult"]["count"])
    ids = res["esearchresult"].get("idlist", [])
    time.sleep(0.4)
    records = []
    if ids:
        ef = f"{base}esummary.fcgi?db=pubmed&retmode=json&email={TOOL_EMAIL}&id={','.join(ids)}"
        summ = urlopen_json(ef)
        for pid in ids:
            r = summ["result"].get(pid, {})
            records.append({
                "source_db": "pubmed",
                "pmid": pid,
                "doi": next((a["value"] for a in r.get("articleids", []) if a.get("idtype") == "doi"), None),
                "title": r.get("title"),
                "journal": r.get("fulljournalname"),
                "year": (r.get("pubdate") or "")[:4],
                "authors": "; ".join(a.get("name", "") for a in r.get("authors", [])[:6]),
                "pubtype": "; ".join(r.get("pubtype", [])),
            })
        time.sleep(0.4)
        # fetch abstracts
        ef2 = f"{base}efetch.fcgi?db=pubmed&retmode=xml&email={TOOL_EMAIL}&id={','.join(ids)}"
        xml_txt = urlopen_text(ef2)
        abstr = {}
        try:
            tree = ET.fromstring(xml_txt)
            for art in tree.iter("PubmedArticle"):
                pmid = art.findtext(".//PMID")
                parts = [t.text or "" for t in art.iter("AbstractText")]
                for t in art.iter("AbstractText"):
                    if t.text is None:
                        parts.append("".join(t.itertext()))
                abstr[pmid] = " ".join("".join(t.itertext()) for t in art.iter("AbstractText"))
        except ET.ParseError:
            pass
        for rec in records:
            rec["abstract"] = abstr.get(rec["pmid"], "")
        time.sleep(0.4)
    return count, records


def epmc_query(q):
    url = ("https://www.ebi.ac.uk/europepmc/webservices/rest/search?"
           f"query={urllib.parse.quote(q)}&format=json&pageSize=500&resultType=core")
    res = urlopen_json(url)
    count = int(res.get("hitCount", 0))
    records = []
    for r in res.get("resultList", {}).get("result", []):
        records.append({
            "source_db": "europepmc",
            "pmid": r.get("pmid"),
            "pmcid": r.get("pmcid"),
            "doi": r.get("doi"),
            "title": r.get("title"),
            "journal": r.get("journalInfo", {}).get("journal", {}).get("title"),
            "year": r.get("pubYear"),
            "authors": r.get("authorString"),
            "abstract": r.get("abstractText", ""),
            "inEPMC": r.get("inEPMC"),
            "isOpenAccess": r.get("isOpenAccess"),
            "pubtype": r.get("pubType"),
        })
    return count, records


def crossref_query(q):
    url = ("https://api.crossref.org/works?rows=100&select=DOI,title,container-title,"
           f"published,author,type,abstract&query={urllib.parse.quote(q)}")
    res = urlopen_json(url)
    items = res.get("message", {}).get("items", [])
    count = int(res.get("message", {}).get("total-results", 0))
    records = []
    for r in items:
        records.append({
            "source_db": "crossref",
            "doi": r.get("DOI"),
            "title": (r.get("title") or [None])[0],
            "journal": (r.get("container-title") or [None])[0],
            "year": str(r.get("published", {}).get("date-parts", [[None]])[0][0] or ""),
            "authors": "; ".join(f"{a.get('family','')} {a.get('given','')}".strip()
                                 for a in r.get("author", [])[:6]),
            "pubtype": r.get("type"),
        })
    return count, records


def main():
    log_rows = []
    all_records = []
    for db, func in (("pubmed", pubmed_query), ("europepmc", epmc_query), ("crossref", crossref_query)):
        for i, q in enumerate(QUERIES[db]):
            print(f"[{db} q{i}] {q[:80]}...")
            try:
                if db == "pubmed":
                    count, recs = func(q, i)
                else:
                    count, recs = func(q)
            except Exception as e:
                print(f"  FAILED: {e}")
                log_rows.append({"db": db, "query_idx": i, "query": q, "date": TODAY,
                                 "hits": None, "retrieved": 0, "error": str(e)})
                continue
            for r in recs:
                r["query_idx"] = i
                r["query"] = q
            all_records.extend(recs)
            log_rows.append({"db": db, "query_idx": i, "query": q, "date": TODAY,
                             "hits": count, "retrieved": len(recs), "error": ""})
            with open(os.path.join(RAW, f"{db}_q{i}.json"), "w", encoding="utf-8") as f:
                json.dump(recs, f, ensure_ascii=False, indent=1)
            print(f"  hits={count} retrieved={len(recs)}")
            time.sleep(0.5)

    pd.DataFrame(log_rows).to_csv(os.path.join(LOGS, "search_log.csv"), index=False)
    df = pd.DataFrame(all_records)
    df.to_csv(os.path.join(ROOT, "data", "interim", "all_records.csv"), index=False)
    print(f"Total raw records: {len(df)}")


if __name__ == "__main__":
    main()
