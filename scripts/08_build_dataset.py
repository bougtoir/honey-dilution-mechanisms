"""Assemble the analysis dataset: auto-extracted outcomes + chemistry + curated rows.

Output:
  data/processed/extraction.csv   - long-format observation-level dataset
  data/processed/chemistry.csv    - honey-level physicochemical data
  data/processed/studies.csv      - study-level metadata
  data/processed/data_dictionary.md
"""
import os
import re

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PARAM_NAMES = {"moisture", "ph", "hmf", "dn", "h2o2", "protein", "tpc", "dpph", "frap",
               "diastase", "phenol", "flavonoid", "brix", "aw", "mgo", "dha", "cat", "gox"}

ORG_MAP = [
    (re.compile(r"MRSA|methicillin.resistant", re.I), "MRSA"),
    (re.compile(r"MSSA|methicillin.sensitive|methicillin.susceptible", re.I), "MSSA"),
    (re.compile(r"aureus|s\. ?aureus|staphylococcus(?!.*epi)", re.I), "S. aureus"),
    (re.compile(r"epidermidis", re.I), "S. epidermidis"),
    (re.compile(r"escherichia|e\. ?coli|\bec\b|\beco\b|\becoli\b|\bes\b", re.I), "E. coli"),
    (re.compile(r"pseudomon|aeruginosa|\bpa\b|\bpae\b|\bps\b", re.I), "P. aeruginosa"),
    (re.compile(r"klebsiella|pneumoniae|\bkp\b|\bkpn\b", re.I), "K. pneumoniae"),
    (re.compile(r"faecal|enterococc|\bef\b|\befm\b", re.I), "E. faecalis"),
    (re.compile(r"typhimurium|typhi|salmonella|\bst\b|\bstm\b|\bsty\b", re.I), "Salmonella"),
    (re.compile(r"enteritidis", re.I), "Salmonella"),
    (re.compile(r"cereus|bacillus|\bbc\b|\bbs\b|\bbac\b", re.I), "B. cereus/Bacillus"),
    (re.compile(r"subtilis", re.I), "B. cereus/Bacillus"),
    (re.compile(r"monocytogenes|listeria|\blm\b", re.I), "L. monocytogenes"),
    (re.compile(r"cloacae|enterobacter|\beb\b|\benc\b|\bent\b", re.I), "Enterobacter"),
    (re.compile(r"parahaem|vibrio|\bvch\b", re.I), "Vibrio"),
    (re.compile(r"influenzae|haemophilus|\bhi\b", re.I), "H. influenzae"),
    (re.compile(r"pyogenes|\bsp\b", re.I), "S. pyogenes"),
    (re.compile(r"mutans", re.I), "S. mutans"),
    (re.compile(r"difficile|clostridi|\bcd\b|\bcdi\b", re.I), "C. difficile"),
    (re.compile(r"pylori|helicobacter|\bhp\b", re.I), "H. pylori"),
    (re.compile(r"baumannii|acinetobacter|\bab\b|\baba\b", re.I), "A. baumannii"),
    (re.compile(r"mirabilis|proteus|\bpm\b", re.I), "Proteus"),
    (re.compile(r"maltophilia|stenotrophomonas|\bsma\b", re.I), "S. maltophilia"),
    (re.compile(r"campylobacter|jejuni|\bcj\b", re.I), "Campylobacter"),
    (re.compile(r"neoformans|candida|albicans|\bca\b", re.I), "fungal"),
    (re.compile(r"lugdunensis", re.I), "S. lugdunensis"),
    (re.compile(r"gingivalis|porphyromonas", re.I), "P. gingivalis"),
    (re.compile(r"abscessus|mycobacter", re.I), "Mycobacterium"),
    (re.compile(r"malassezia|sporothrix|trichophyton|dermatophyt", re.I), "fungal"),
    (re.compile(r"sonnei|shigella|\bshi\b", re.I), "Shigella"),
    (re.compile(r"morganella|serratia|marcescens|citrobacter", re.I), "other Gram-"),
    (re.compile(r"burkholderia|cepacia", re.I), "Burkholderia"),
    (re.compile(r"agalactiae", re.I), "S. agalactiae"),
    (re.compile(r"CRE|carbapenem", re.I), "CRE isolate"),
]

GRAM_NEG = {"E. coli", "P. aeruginosa", "K. pneumoniae", "Salmonella", "Enterobacter",
            "Vibrio", "H. influenzae", "A. baumannii", "Proteus", "S. maltophilia",
            "Campylobacter", "Shigella", "other Gram-", "Burkholderia", "H. pylori",
            "P. gingivalis", "CRE isolate"}
GRAM_POS = {"S. aureus", "MRSA", "MSSA", "S. epidermidis", "S. pyogenes", "S. mutans",
            "E. faecalis", "B. cereus/Bacillus", "L. monocytogenes", "C. difficile",
            "S. lugdunensis", "S. agalactiae", "Mycobacterium"}


def map_org(s):
    s = str(s)
    for pat, name in ORG_MAP:
        if pat.search(s):
            return name
    return "other"


def is_param_label(h):
    return str(h).strip().lower().split(" ")[0] in PARAM_NAMES or \
        str(h).strip().lower() in PARAM_NAMES


def main():
    a = pd.read_csv(os.path.join(ROOT, "data", "interim", "auto_outcomes_A.csv"))
    man = pd.read_csv(os.path.join(ROOT, "data", "interim", "manual_extraction.csv"))
    chem = pd.read_csv(os.path.join(ROOT, "data", "interim", "auto_chem_B.csv"))
    el = pd.read_csv(os.path.join(ROOT, "data", "interim", "eligible.csv"))

    meta = el.drop_duplicates("pmcid").set_index("pmcid")

    # ---- clean auto_A ----
    a = a[~a["honey_label"].map(is_param_label)]
    a = a[~a["organism_label"].map(is_param_label)]
    a = a[a["outcome"] != "unknown"]
    a = a[~a["honey_label"].str.match(r"^\s*(r\s*=|p[- ]?value|note)", case=False, na=False)]
    # correlation-matrix leakage: values in [-1,1] labelled as MIC/% with a param-like label
    a = a[~((a["value"].abs() <= 1.05) & (a["outcome"].isin(["MIC", "MBC"])) &
            (a["honey_label"].str.lower().str.split().str[0].isin(PARAM_NAMES)))]
    a["organism"] = a["organism_label"].map(map_org)
    a["concentration_pct"] = pd.NA
    a["condition"] = "untreated"
    a["sd"] = pd.NA
    a["source"] = "t" + a["table_idx"].astype(str)
    a["extract_method"] = a["extract"]
    a = a.rename(columns={"unit_ctx": "context"})

    # concentration embedded in honey label e.g. "Thyme 9%"
    m = a["honey_label"].str.extract(r"^(.*?)\s+(\d+(?:\.\d+)?)\s*%")
    hasconc = m[1].notna() & (a["outcome"].isin(["zone", "MBEC", "pct_inhib"]))
    a.loc[hasconc, "concentration_pct"] = m.loc[hasconc, 1].astype(float)
    a.loc[hasconc, "honey_label"] = m.loc[hasconc, 0].str.strip()
    a.loc[hasconc, "outcome"] = a.loc[hasconc, "outcome"].replace({"MBEC": "pct_inhib_biofilm"})

    # ---- manual rows ----
    man["organism"] = man["organism"].map(map_org).where(man["organism"].notna() & (man["organism"] != ""), "")
    man["extract_method"] = "manual_curated"
    man["context"] = ""
    man["censor"] = man["notes"].str.extract(r"censor=(\w+)", expand=False).fillna("")

    # ---- series C (dilution-series tables) ----
    ser = pd.read_csv(os.path.join(ROOT, "data", "interim", "auto_series_C.csv"))
    ser["organism"] = ser["organism_label"].map(map_org)
    ser["condition"] = "untreated"
    ser["sd"] = pd.NA
    ser["source"] = "t" + ser["table_idx"].astype(str)
    ser["extract_method"] = "auto_C"
    ser["context"] = ""
    ser["censor"] = ""
    ser = ser.rename(columns={"concentration": "concentration_pct"})
    # caption-informed measure label
    capmap = {"PMC2478674": "pH"}
    ser["measure"] = ser["pmcid"].map(capmap).fillna("value")

    a["measure"] = a["outcome"]
    man["measure"] = man["outcome"]
    cols = ["pmcid", "source", "honey_label", "organism_label", "organism", "outcome",
            "concentration_pct", "condition", "value", "sd", "unit", "censor",
            "extract_method", "context", "measure"]
    if "organism_label" not in man.columns:
        man["organism_label"] = man["organism"]

    df = pd.concat([a[cols], man.reindex(columns=cols), ser.reindex(columns=cols)],
                   ignore_index=True)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["value"])
    # drop identical observations produced by double-parsing of nested
    # tables (same cell extracted under two table indices); legitimately
    # distinct replicate rows differ in at least one keyed field
    n_before = len(df)
    df = df.drop_duplicates(subset=["pmcid", "organism_label", "honey_label",
                                    "outcome", "concentration_pct",
                                    "condition", "value", "unit", "censor",
                                    "measure"], keep="first")
    print(f"deduped identical observation rows: {n_before - len(df)}")
    df["organism"] = df["organism"].fillna("other")
    df.loc[df["organism"] == "", "organism"] = "other"

    # normalize unit basis
    df["unit"] = df["unit"].fillna("").str.replace("μg/mL", "µg/mL", regex=False)\
        .str.replace("mg/ml", "mg/mL", regex=False).str.strip()
    df.loc[df["unit"] == "", "unit"] = pd.NA

    # unit basis: % w/v, % v/v and % w/w are NOT equated; analyses are run
    # separately on the dominant basis with the others as sensitivity.
    def unit_basis(u):
        u0 = str(u).lower().strip()
        if re.match(r"^%\s*\(?w/v\)?$", u0):
            return "%w/v"
        if re.match(r"^%\s*\(?v/v\)?$", u0):
            return "%v/v"
        if re.match(r"^%\s*\(?w/w\)?$", u0):
            return "%w/w"
        if u0 == "%":
            return "% (basis unspecified)"
        if "g/ml" in u0 or "g/l" in u0:
            return "mass"
        if u0 == "mm" or u0 == "mm2":
            return u0
        if u0 in ("nan", ""):
            return pd.NA
        return "other"
    df["unit_raw"] = df["unit"]
    df["unit_basis"] = df["unit"].map(unit_basis)
    df.loc[df["unit"].isin(["% v/v", "% w/v", "%w/v", "%v/v", "% w/w", "%w/w",
                            "% (v/v)", "% (w/v)", "% (w/w)"]), "unit"] = "%"

    # honey family flags
    hlow = df["honey_label"].str.lower()
    df["is_manuka"] = hlow.str.contains("manuka|leptospermum|umf|mgo")
    df["is_artificial"] = hlow.str.contains("artificial|simulated|sugar|glucose syrup|model")
    df["is_medical"] = hlow.str.contains("medihoney|medical|revamil|umf|mgo")

    # attach study metadata
    for c in ["title", "year", "doi", "pmid", "journal"]:
        df[c] = df["pmcid"].map(meta[c])
    df["study_id"] = df["pmcid"]

    df.to_csv(os.path.join(ROOT, "data", "processed", "extraction.csv"), index=False)

    # ---- chemistry ----
    chem = chem.rename(columns={"param": "chem_param", "param_header": "chem_header"})
    chem = chem.drop_duplicates(subset=[c for c in chem.columns
                                        if c not in ("table_idx",)])
    chem["study_id"] = chem["pmcid"]
    for c in ["title", "year", "doi", "pmid"]:
        chem[c] = chem["pmcid"].map(meta[c])
    chem.to_csv(os.path.join(ROOT, "data", "processed", "chemistry.csv"), index=False)

    # ---- studies table ----
    st = meta.reset_index()[["pmcid", "pmid", "doi", "title", "journal", "year", "elig",
                            "elig_reason", "score"]]
    st["n_rows"] = st["pmcid"].map(df.groupby("pmcid").size())
    st["extracted"] = st["n_rows"].notna()
    st.to_csv(os.path.join(ROOT, "data", "processed", "studies.csv"), index=False)

    print("extraction rows:", len(df), "| studies:", df["study_id"].nunique())
    print(df.groupby("outcome").size().to_string())
    print("organisms:", df["organism"].value_counts().head(15).to_string())


if __name__ == "__main__":
    main()
