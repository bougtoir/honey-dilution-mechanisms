"""Fetch PMC open-access full-text XML for all ranked candidates with a PMCID.

Saves XML to data/raw/fulltext/{pmcid}.xml; logs failures.
"""
import json
import os
import time
import urllib.request

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FT = os.path.join(ROOT, "data", "raw", "fulltext")
os.makedirs(FT, exist_ok=True)


def fetch(pmcid):
    url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
    req = urllib.request.Request(url, headers={"User-Agent": "devin-sr/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    return data


def main():
    cand = pd.read_csv(os.path.join(ROOT, "data", "interim", "candidates_ranked.csv"))
    ids = [p for p in cand["pmcid"].dropna().unique() if str(p).startswith("PMC")]
    ok, fail = 0, []
    for i, pmcid in enumerate(ids):
        out = os.path.join(FT, f"{pmcid}.xml")
        if os.path.exists(out) and os.path.getsize(out) > 1000:
            ok += 1
            continue
        try:
            data = fetch(pmcid)
            if b"<article" not in data[:5000]:
                fail.append({"pmcid": pmcid, "err": "not-article"})
                continue
            with open(out, "wb") as f:
                f.write(data)
            ok += 1
        except Exception as e:
            fail.append({"pmcid": pmcid, "err": str(e)})
        if i % 25 == 0:
            print(f"{i}/{len(ids)} ok={ok} fail={len(fail)}", flush=True)
        time.sleep(0.35)
    with open(os.path.join(ROOT, "logs", "pmc_fetch_log.json"), "w") as f:
        json.dump({"attempted": len(ids), "ok": ok, "failures": fail}, f, indent=1)
    print(f"DONE ok={ok} fail={len(fail)}")


if __name__ == "__main__":
    main()
