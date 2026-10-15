"""Resolve PMCIDs for included records lacking them, via Europe PMC DOI/PMID lookup."""
import json
import os
import time
import urllib.parse
import urllib.request

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def epmc_search(q):
    url = ("https://www.ebi.ac.uk/europepmc/webservices/rest/search?"
           f"query={urllib.parse.quote(q)}&format=json&pageSize=5&resultType=lite")
    req = urllib.request.Request(url, headers={"User-Agent": "devin-sr/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def main():
    el = pd.read_csv(os.path.join(ROOT, "data", "interim", "eligible.csv"))
    need = el[el["elig"].isin(["include", "review_flag"]) & el["pmcid"].isna()].copy()
    print("missing pmcid:", len(need))
    found = []
    for i, r in need.iterrows():
        pmcid = None
        for q in ([f'DOI:"{r["doi"]}"'] if isinstance(r.get("doi"), str) and r["doi"] else []) + \
                 ([f'EXT_ID:{str(r["pmid"]).split(".")[0]}']
                  if isinstance(r.get("pmid"), float) and pd.notna(r["pmid"]) else []):
            try:
                res = epmc_search(q)
                hits = res.get("resultList", {}).get("result", [])
                for h in hits:
                    if h.get("pmcid"):
                        pmcid = h["pmcid"]
                        break
            except Exception:
                pass
            if pmcid:
                break
            time.sleep(0.3)
        if pmcid:
            found.append({"idx": i, "pmcid": pmcid})
            el.loc[i, "pmcid"] = pmcid
        time.sleep(0.3)
    el.to_csv(os.path.join(ROOT, "data", "interim", "eligible.csv"), index=False)
    with open(os.path.join(ROOT, "logs", "pmcid_resolution.json"), "w") as f:
        json.dump({"queried": len(need), "found": found}, f, indent=1)
    print("resolved:", len(found))


if __name__ == "__main__":
    main()
