"""Rebuild references for FRI: verify each extracted study's DOI against
Crossref, fetch full metadata (authors, volume, issue, pages/article no.),
unescape HTML entities, and emit an author-year (alphabetical) list plus
in-text citation labels mapped to PMCID/PMID.
"""
import os
import re
import time
import html
import json
import urllib.parse
import urllib.request

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "data", "interim", "crossref_cache.json")


def clean(t):
    t = html.unescape(str(t or ""))          # &lt;i&gt; -> <i>
    t = re.sub(r"<[^>]+>", "", t)            # strip real/entity tags
    return re.sub(r"\s+", " ", t).strip().rstrip(".")


def crossref(doi):
    if os.path.exists(CACHE):
        cache = json.load(open(CACHE, encoding="utf-8"))
    else:
        cache = {}
    if doi in cache:
        return cache[doi]
    try:
        url = ("https://api.crossref.org/works/" +
               urllib.parse.quote(doi, safe=""))
        req = urllib.request.Request(url, headers={"User-Agent":
                                     "devin-sr/1.0 (mailto:devin@example.org)"})
        r = json.loads(urllib.request.urlopen(req, timeout=30).read())["message"]
        out = {
            "authors": [f"{a.get('family','')}, {a.get('given','')}".strip(", ")
                        for a in r.get("author", [])],
            "title": (r.get("title") or [""])[0],
            "journal": (r.get("container-title") or [""])[0],
            "year": (r.get("published", {}).get("date-parts", [[None]])[0][0]),
            "volume": r.get("volume", ""),
            "issue": r.get("issue", ""),
            "pages": r.get("page", ""),
            "artno": r.get("article-number", ""),
            "type": r.get("type", ""),
        }
    except Exception as e:
        out = {"error": str(e)}
    cache[doi] = out
    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1)
    time.sleep(0.15)
    return out


def surname(author_field):
    """First-author surname from 'Family, Given' or 'Family G.' formats."""
    a = str(author_field or "").split(";")[0].split(",")[0].strip()
    return re.sub(r"[^A-Za-zÀ-ÿ\-']", "", a)


def intext_label(authors_list, year):
    if not authors_list:
        return f"Anon., {year}"
    s1 = re.sub(r",.*", "", authors_list[0]).strip()
    if len(authors_list) == 1:
        return f"{s1}, {year}"
    if len(authors_list) == 2:
        s2 = re.sub(r",.*", "", authors_list[1]).strip()
        return f"{s1} and {s2}, {year}"
    return f"{s1} et al., {year}"


def fmt_fri(authors_list, year, title, journal, volume, issue, pages, artno, doi):
    a = ", ".join(f"{x.split(',')[0].strip()}, "
                  f"{''.join(w[0] + '.' for w in x.split(',')[1].split() if w)}"
                  if "," in x else x for x in authors_list)
    parts = [f"{a} ({year})." if a else f"({year}).", clean(title) + "."]
    loc = ""
    if volume:
        loc = str(volume)
        if issue:
            loc += f"({issue})"
        if pages:
            loc += f", {pages}"
        elif artno:
            loc += f", {artno}"
    elif pages:
        loc = pages
    elif artno:
        loc = artno
    jr = clean(journal)
    parts.append((jr + (", " + loc if loc else "") + ".").strip())
    if doi:
        parts.append(f"https://doi.org/{doi}")
    return " ".join(parts)


def main():
    st = pd.read_csv(os.path.join(ROOT, "data", "processed", "studies.csv"))
    sc = pd.read_csv(os.path.join(ROOT, "data", "interim", "screened.csv"),
                     low_memory=False)
    scp = pd.concat([sc[sc["pmcid"].notna()].drop_duplicates("pmcid"),
                     sc[sc["pmcid"].isna()]])
    amap = scp[scp["pmcid"].notna()].set_index("pmcid")["authors"].to_dict()

    ex = st[st["extracted"]].copy()
    rows = []
    for _, r in ex.iterrows():
        doi = str(r["doi"]).strip() if pd.notna(r["doi"]) else ""
        cr = crossref(doi) if doi else {"error": "no doi"}
        if "error" in cr:
            # fall back to local metadata
            auth = str(amap.get(r["pmcid"], "") or "")
            authors_list = [a.strip() for a in auth.replace(";", ",").split(",")
                            if a.strip()]
            ref = None
        else:
            authors_list = cr["authors"]
            ref = None
        year = cr.get("year") or (int(r["year"]) if pd.notna(r["year"]) else "")
        if ref is None and "error" not in cr:
            ref = fmt_fri(authors_list, year, cr["title"], cr["journal"],
                          cr["volume"], cr["issue"], cr["pages"],
                          cr["artno"], doi)
        rows.append({"pmcid": r["pmcid"], "doi": doi,
                     "title": clean(cr.get("title") or r["title"]),
                     "journal": clean(cr.get("journal") or r["journal"]),
                     "year": year,
                     "authors": "; ".join(authors_list),
                     "intext": intext_label(authors_list, year),
                     "ref": ref or "",
                     "cr_status": "ok" if "error" not in cr else cr["error"]})
    R = pd.DataFrame(rows)
    # disambiguate identical author-year intext labels (2024 -> 2024a, 2024b)
    dup = R["intext"].duplicated(keep=False)
    for lbl in R.loc[dup, "intext"].unique():
        idx = R.index[R["intext"] == lbl]
        for j, ix in enumerate(idx):
            suffix = chr(ord("a") + j)
            R.loc[ix, "intext"] = lbl + suffix
            R.loc[ix, "ref"] = R.loc[ix, "ref"].replace(
                f"({lbl.rsplit(',', 1)[-1].strip()})",
                f"({lbl.rsplit(',', 1)[-1].strip()}{suffix})")
    R = R.sort_values(["intext"]).reset_index(drop=True)
    R["n"] = R.index + 1
    R.to_csv(os.path.join(ROOT, "references", "references_fri.csv"),
             index=False)
    ok = (R["cr_status"] == "ok").sum()
    noref = (R["ref"] == "").sum()
    print(f"{len(R)} refs; crossref-ok {ok}; fallback/missing ref text {noref}")
    print("unresolved:", R[R["ref"] == ""]["pmcid"].tolist())

    # ---- context (landmark) references: resolve DOI via Europe PMC, verify on Crossref
    ctx = pd.read_csv(os.path.join(ROOT, "references", "references_context.csv"))
    crows = []
    for _, r in ctx.iterrows():
        pmid = str(r["pmid"]).split(".")[0]
        doi = ""
        try:
            url = ("https://www.ebi.ac.uk/europepmc/webservices/rest/search?"
                   f"query=EXT_ID:{pmid}&format=json&resultType=lite")
            req = urllib.request.Request(url, headers={"User-Agent": "devin-sr/1.0"})
            res = json.loads(urllib.request.urlopen(req, timeout=30).read())
            hits = res.get("resultList", {}).get("result", [])
            if hits:
                doi = hits[0].get("doi", "") or ""
        except Exception:
            pass
        time.sleep(0.15)
        cr = crossref(doi) if doi else {"error": "no doi"}
        if "error" in cr:
            m = re.match(r"(.+?)\.\s*(.+)", str(r["ref"]))
            auth = [a.strip() for a in (m.group(1) if m else "").split(",")
                    if a.strip()]
            authors_list = [
                "{}, {}".format(
                    re.sub(r"\s*[A-Z]+\.?$", "", a).strip(), a.split()[-1])
                for a in auth[::1]] if m else []
            yr = re.search(r"\b(19|20)\d{2}\b", str(r["ref"]))
            crows.append({"pmid": pmid, "doi": doi, "year": yr.group(0) if yr else "",
                          "authors": "; ".join(authors_list),
                          "intext": intext_label(authors_list, yr.group(0) if yr else ""),
                          "ref": clean(r["ref"]), "cr_status": "fallback"})
            continue
        authors_list = cr["authors"]
        year = cr.get("year") or ""
        ref = fmt_fri(authors_list, year, cr["title"], cr["journal"],
                      cr["volume"], cr["issue"], cr["pages"], cr["artno"], doi)
        crows.append({"pmid": pmid, "doi": doi, "year": year,
                      "authors": "; ".join(authors_list),
                      "intext": intext_label(authors_list, year),
                      "ref": ref, "cr_status": "ok"})
    C = pd.DataFrame(crows)
    C.to_csv(os.path.join(ROOT, "references", "references_fri_context.csv"),
             index=False)
    print("context refs:", len(C), "|", C["cr_status"].value_counts().to_dict())
    print(C[["intext", "cr_status"]].to_string(index=False))


if __name__ == "__main__":
    main()
