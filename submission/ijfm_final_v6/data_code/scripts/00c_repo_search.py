"""Supplementary search of public data repositories (Zenodo, Dryad, Figshare)
for honey antibacterial datasets that may contain dilution-resolved data.
Queries and hit counts are logged to logs/repo_search_log.csv.
"""
import json
import os
import time
import urllib.parse
import urllib.request
import datetime

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw", "search")
os.makedirs(RAW, exist_ok=True)
TODAY = datetime.date.today().isoformat()

Q = "honey antibacterial"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "devin-sr/1.0"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read().decode())


def zenodo(q):
    url = ("https://zenodo.org/api/records?size=25&q=" +
           urllib.parse.quote(q + ' AND (MIC OR dilution OR peroxide)'))
    res = get(url)
    return [{"repo": "zenodo", "id": r.get("id"),
             "title": (r.get("metadata") or {}).get("title"),
             "doi": (r.get("metadata") or {}).get("doi"),
             "year": ((r.get("metadata") or {}).get("publication_date") or "")[:4]}
            for r in res.get("hits", {}).get("hits", [])]


def dryad(q):
    url = ("https://datadryad.org/api/v2/search?per_page=100&query=" +
           urllib.parse.quote(q))
    res = get(url)
    docs = res.get("_embedded", {}).get("stash:datasets", [])
    return [{"repo": "dryad", "id": d.get("id"),
             "title": d.get("title"), "doi": d.get("identifier"),
             "year": (d.get("publicationDate") or "")[:4]} for d in docs]


def figshare(q):
    req = urllib.request.Request(
        "https://api.figshare.com/v2/articles/search",
        data=json.dumps({"search_for": q + " antibacterial", "limit": 100}).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "devin-sr/1.0"})
    res = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
    return [{"repo": "figshare", "id": r.get("id"), "title": r.get("title"),
             "doi": r.get("doi"), "year": (r.get("published_date") or "")[:4]}
            for r in res]


def main():
    rows, log = [], []
    for name, fn in [("zenodo", zenodo), ("dryad", dryad), ("figshare", figshare)]:
        try:
            recs = fn(Q)
            rows.extend(recs)
            log.append({"repo": name, "date": TODAY, "retrieved": len(recs),
                        "error": ""})
            print(name, len(recs))
        except Exception as e:
            log.append({"repo": name, "date": TODAY, "retrieved": 0,
                        "error": str(e)})
            print(name, "FAILED", e)
        time.sleep(0.5)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(RAW, "repo_records.csv"), index=False)
    pd.DataFrame(log).to_csv(os.path.join(ROOT, "logs", "repo_search_log.csv"),
                             index=False)
    # screen: keep titles mentioning honey + antibacterial/peroxide/dilution
    if len(df):
        keep = df[df["title"].str.contains("honey", case=False, na=False)]
        keep.to_csv(os.path.join(ROOT, "data", "interim", "repo_candidates.csv"),
                    index=False)
        print("honey-related repo hits:", len(keep))


if __name__ == "__main__":
    main()
