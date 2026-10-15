"""Parse all tables from downloaded PMC XML files into CSVs + a catalog.

Output:
  data/interim/tables/{pmcid}_t{idx}.csv   - raw table cells
  data/interim/table_catalog.csv           - caption, dims, relevance flags
"""
import os
import re
import glob

import pandas as pd
from lxml import etree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FT = os.path.join(ROOT, "data", "raw", "fulltext")
OUT = os.path.join(ROOT, "data", "interim", "tables")
os.makedirs(OUT, exist_ok=True)

RELEVANT = re.compile(
    r"MIC|MBC|minimum inhibitory|inhibition|antibacterial|antimicrobial|zone|"
    r"honey|concentration|dilution|peroxide|H2O2|catalase|methylglyoxal|MGO|"
    r"water activity|osmolar|osmotic|phenol|sugar|artificial|pH|Brix|phenolic|"
    r"flavonoid|growth|bacteria|Staphylococcus|Pseudomonas|Escherichia|"
    r"susceptib|activity", re.I)


def parse_table(tw):
    """Extract a JATS table-wrap into a list-of-lists DataFrame."""
    label = " ".join(tw.findtext("label") or "")
    caption = " ".join(tw.find("caption").itertext()) if tw.find("caption") is not None else ""
    table = tw.find(".//table")
    if table is None:
        table = next((x for x in tw.iter("xhtml:table") ), None)
    if table is None:
        for x in tw.iter():
            if isinstance(x.tag, str) and etree.QName(x).localname == "table":
                table = x
                break
    if table is None:
        return None, label, caption.strip()
    rows = []
    for tr in table.iter():
        if not isinstance(tr.tag, str) or etree.QName(tr).localname != "tr":
            continue
        cells = []
        for cell in list(tr):
            if isinstance(cell.tag, str) and etree.QName(cell).localname in ("td", "th"):
                txt = " ".join("".join(cell.itertext()).split())
                try:
                    span = int(cell.get("colspan", "1"))
                except ValueError:
                    span = 1
                cells.append(txt)
                cells.extend([""] * (span - 1))
        if cells:
            rows.append(cells)
    if not rows:
        return None, label, caption.strip()
    ncols = max(len(r) for r in rows)
    rows = [r + [""] * (ncols - len(r)) for r in rows]
    return pd.DataFrame(rows), label, caption.strip()


def main():
    catalog = []
    for path in sorted(glob.glob(os.path.join(FT, "*.xml"))):
        pmcid = os.path.basename(path).replace(".xml", "")
        try:
            tree = etree.parse(path)
        except etree.XMLSyntaxError:
            continue
        art = tree.getroot()
        title = " ".join(" ".join(art.itertext()).split()[:0])  # unused
        atitle = art.findtext(".//article-title") or ""
        for i, tw in enumerate(art.iter("table-wrap")):
            df, label, caption = parse_table(tw)
            rel = bool(RELEVANT.search(caption)) or (
                df is not None and bool(RELEVANT.search(" ".join(df.values.ravel()[:200]))))
            fname = f"{pmcid}_t{i}.csv"
            if df is not None:
                df.to_csv(os.path.join(OUT, fname), index=False, header=False)
            catalog.append({
                "pmcid": pmcid, "table_idx": i, "label": label,
                "caption": caption[:400], "n_rows": 0 if df is None else len(df),
                "n_cols": 0 if df is None else df.shape[1],
                "relevant": rel, "file": fname if df is not None else "",
                "title": atitle[:120],
            })
    cat = pd.DataFrame(catalog)
    cat.to_csv(os.path.join(ROOT, "data", "interim", "table_catalog.csv"), index=False)
    print(f"tables: {len(cat)}, relevant-flagged: {cat['relevant'].sum()}")


if __name__ == "__main__":
    main()
