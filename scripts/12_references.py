"""Build the numbered reference list (Vancouver-ish, MDPI style) for all studies
with extracted data plus screened-in records, and audit DOI availability."""
import os
import re

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def clean(t):
    t = re.sub(r"<[^>]+>", "", str(t))
    return re.sub(r"\s+", " ", t).strip().rstrip(".")


def fmt_ref(authors, title, journal, year, doi):
    a = str(authors) if pd.notna(authors) else ""
    a = a.replace(";", ",").strip()
    if a and not a.endswith("."):
        a += "."
    parts = []
    if a:
        parts.append(a)
    parts.append(clean(title) + ".")
    j = clean(journal) if pd.notna(journal) else ""
    if j:
        jr = j
        jr = re.sub(r"\s*\((Basel|Switzerland)[^)]*\)", "", jr).strip()
        parts.append(jr + (f" {int(year)}." if pd.notna(year) else "."))
    elif pd.notna(year):
        parts.append(f"{int(year)}.")
    if pd.notna(doi) and str(doi).strip():
        parts.append(f"https://doi.org/{str(doi).strip()}")
    return " ".join(parts)


def main():
    st = pd.read_csv(os.path.join(ROOT, "data", "processed", "studies.csv"))
    sc = pd.read_csv(os.path.join(ROOT, "data", "interim", "screened.csv"))
    sc = pd.concat([sc[sc["pmcid"].notna()].drop_duplicates("pmcid"),
                    sc[sc["pmcid"].isna()]])
    amap = sc[sc["pmcid"].notna()].set_index("pmcid")["authors"].to_dict()

    ex = st[st["extracted"]].copy()

    # fill missing authors from Europe PMC
    import time
    import urllib.request
    import json as _json

    def fetch_authors(pmcid):
        try:
            url = ("https://www.ebi.ac.uk/europepmc/webservices/rest/search?"
                   f"query=PMCID:{pmcid}&resultType=core&format=json")
            req = urllib.request.Request(url, headers={"User-Agent": "devin-sr/1.0"})
            d = _json.loads(urllib.request.urlopen(req, timeout=30).read())
            r = d["resultList"]["result"][0]
            return r.get("authorString", "")
        except Exception:
            return ""

    need = []
    for p in ex["pmcid"]:
        a = amap.get(p)
        if a is None or pd.isna(a) or not str(a).strip() or str(a).lower() == "nan":
            need.append(p)
    for i, p in enumerate(need):
        au = fetch_authors(p)
        if au:
            amap[p] = au
        if i % 10 == 0:
            time.sleep(0.3)

    # fallback: parse authors from local PMC XML
    from lxml import etree

    def xml_authors(pmcid):
        path = os.path.join(ROOT, "data", "raw", "fulltext", f"{pmcid}.xml")
        if not os.path.exists(path):
            return ""
        try:
            t = etree.parse(path)
            names = []
            for c in t.iter("contrib"):
                if c.get("contrib-type") != "author":
                    continue
                sn = c.find(".//surname"); gn = c.find(".//given-names")
                if sn is not None:
                    init = "".join(w[0] for w in (gn.text or "").split()) if gn is not None else ""
                    names.append(f"{sn.text} {init}")
            return ", ".join(names)
        except Exception:
            return ""

    for p in need:
        a = amap.get(p)
        if a is None or pd.isna(a) or not str(a).strip() or str(a).lower() == "nan":
            au = xml_authors(p)
            if au:
                amap[p] = au + "."

    refs = []
    for _, r in ex.iterrows():
        refs.append({
            "pmcid": r["pmcid"],
            "ref": fmt_ref(amap.get(r["pmcid"], ""), r["title"], r["journal"],
                           r["year"], r["doi"]),
            "doi": r["doi"] if pd.notna(r["doi"]) else ""})
    R = pd.DataFrame(refs)
    R.index = R.index + 1
    R.to_csv(os.path.join(ROOT, "references", "references_extracted.csv"),
             index_label="n")
    with open(os.path.join(ROOT, "references", "reference_list.txt"), "w",
              encoding="utf-8") as f:
        for i, row in R.iterrows():
            f.write(f"{i}. {row['ref']}\n")
    # audit
    n_doi = (R["doi"] != "").sum()
    print(f"{len(R)} references written; {n_doi} with DOI "
          f"({n_doi/len(R)*100:.0f}%); {len(R)-n_doi} lack DOI")

    # ---- context references (landmark mechanistic papers identified in screening
    # but not always PMC-extractable) ----
    ctx_pmids = [12804080.0, 20228250.0, 21394213.0, 1447054.0, 10472280.0]
    ctx = sc[sc["pmid"].astype(float).isin(ctx_pmids)]
    ctxrefs = []
    for _, r in ctx.iterrows():
        ctxrefs.append({"pmid": r["pmid"],
                        "ref": fmt_ref(r.get("authors", ""), r["title"],
                                       r["journal"], r["year"], r["doi"])})
    C = pd.DataFrame(ctxrefs).drop_duplicates("pmid")
    C.to_csv(os.path.join(ROOT, "references", "references_context.csv"),
             index_label="n")
    print(f"{len(C)} context references")
    for _, r in C.iterrows():
        print("  ", r["pmid"], r["ref"][:90])


if __name__ == "__main__":
    main()
