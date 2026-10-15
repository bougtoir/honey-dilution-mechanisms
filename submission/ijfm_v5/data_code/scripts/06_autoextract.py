"""Heuristic extraction of structured data from parsed PMC tables.

Detectors:
  A) honey-rows x organism-columns outcome tables (MIC/MBC/zone/%inhibition/phenol)
  B) honey-rows x physicochemical-parameter-columns tables
  C) concentration-series tables (first column = concentration)

Every emitted row carries provenance: pmcid, table_idx, row_idx, col_idx.
Manual curation (scripts/07_manual_extraction.py -> data/interim/manual_extraction.csv)
supplements this for mechanistic contrasts not cleanly parseable.
"""
import os
import re
import glob

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAB = os.path.join(ROOT, "data", "interim", "tables")

ORG = re.compile(
    r"(staphylococc|aureus|epidermidis|escherichia|e\.?\s?coli|\bcoli|pseudomon|aeruginosa|"
    r"enterococc|faecal|streptococc|pyogenes|mutans|pneumoniae(?!.*kleb)|agalactiae|"
    r"klebsiella|bacill|cereus|subtilis|salmonella|typhi|typhimurium|enteritidis|"
    r"listeria|monocytogenes|proteus|mirabilis|vulgaris|acinetobacter|baumannii|"
    r"MRSA|MSSA|MRSE|VRE|campylobacter|jejuni|helicobacter|pylori|serratia|marcescens|"
    r"morganella|citrobacter|enterobacter|cloacae|stenotrophomonas|maltophilia|"
    r"shigella|sonnei|flexneri|haemophilus|influenzae|neisseria|corynebacter|"
    r"mycobacter|abscessus|burkholderia|cepacia|propionibacter|cutibacter|acnes|"
    r"aggregatibacter|porphyromonas|gingivalis|prevotella|clostridi|difficile|"
    r"bacteroides|moraxella|aeromonas|vibrio|yersinia|borde?tella|aerococcus|"
    r"micrococcus|lactobacill|paenibacill|alcaligenes|faecalis|steno|"
    r"gram-?positive|gram-?negative|candida|albicans|neoformans|malassezia)", re.I)

CELLNUM = re.compile(
    r"^\s*(>|>=|<|<=|≤|≥)?\s*(\d+(?:\.\d+)?)\s*(%|mg/mL|µg/mL|ug/mL|mg/L|g/L|mM|µM|uM|mm)?"
    r"\s*(?:±.*)?$", re.I)

OUTCOME_KW = [
    ("MIC", re.compile(r"\bMIC\b|minimum inhibitory|inhibitory concentration", re.I)),
    ("MBC", re.compile(r"\bMBC\b|minimum bactericidal|bactericidal concentration|MFC", re.I)),
    ("zone", re.compile(r"zone|diameter|inhibition zone|\bmm\b|well diffusion|agar (well|diffusion)", re.I)),
    ("pct_inhib", re.compile(r"% ?inhibition|inhibition \(|inhibitory effect|growth inhibition", re.I)),
    ("phenol", re.compile(r"phenol|total activity|non-?peroxide activity|NPA|TPA|AAV", re.I)),
    ("MBEC", re.compile(r"MBEC|biofilm eradication|biofilm inhibitory|MBIC", re.I)),
]

CHEM_COLS = {
    "pH": re.compile(r"^pH\b", re.I),
    "aw": re.compile(r"\ba_?w\b|water activity", re.I),
    "Brix": re.compile(r"brix|soluble solid", re.I),
    "moisture": re.compile(r"moisture|water content", re.I),
    "H2O2": re.compile(r"h2o2|hydrogen peroxide|peroxide", re.I),
    "MGO": re.compile(r"\bMGO\b|methylglyoxal", re.I),
    "DHA": re.compile(r"\bDHA\b|dihydroxyacetone", re.I),
    "HMF": re.compile(r"\bHMF\b|hydroxymethylfurfural", re.I),
    "TPC": re.compile(r"TPC|total phenol|phenolic", re.I),
    "TFC": re.compile(r"TFC|flavonoid", re.I),
    "GOx": re.compile(r"\bGOx\b|glucose oxidase", re.I),
    "catalase": re.compile(r"catalase|\bCAT\b", re.I),
    "phenol_equiv": re.compile(r"phenol (equiv|%|coeff)|total activity|non-?peroxide|NPA", re.I),
    "free_acidity": re.compile(r"free acidity|acidity", re.I),
    "electrical_cond": re.compile(r"conductivity", re.I),
    "proline": re.compile(r"proline", re.I),
    "diastase": re.compile(r"diastase", re.I),
    "sugar_total": re.compile(r"total sugar|reducing sugar|fructose|glucose", re.I),
    "color": re.compile(r"color|pfund|absorbance.*color", re.I),
    "density": re.compile(r"density|specific gravity", re.I),
}

UNIT_IN_CTX = re.compile(
    r"(%\s*\(?\s*w/v\s*\)?|%\s*\(?\s*v/v\s*\)?|%\s*\(?\s*w/w\s*\)?|%|"
    r"mg/mL|µg/mL|ug/mL|g/L|mg/L|µM|mM|mm2|mm²|\bmm\b)", re.I)


def detect_unit(context):
    m = UNIT_IN_CTX.search(context)
    if not m:
        return ""
    u = re.sub(r"[\s()]", "", m.group(1))
    return {"%w/v": "%w/v", "%v/v": "%v/v", "%w/w": "%w/w", "%": "%",
            "µg/mL": "µg/mL", "ug/mL": "µg/mL", "mm2": "mm2", "mm²": "mm2"}.get(u, u)


def parse_cell(s):
    s = str(s).strip()
    m = CELLNUM.match(s)
    if not m:
        return None
    cens = {">": "gt", ">=": "ge", "<": "lt", "<=": "le", "≤": "le", "≥": "ge"}.get(
        (m.group(1) or "").strip(), "")
    return float(m.group(2)), cens, (m.group(3) or "")


def header_text(df, nrows=4):
    return " || ".join(
        " | ".join(str(x) for x in df.iloc[r].tolist()) for r in range(min(nrows, len(df))))


SUBHDR = re.compile(r"^\s*(MIC|MBC|MFC|MBEC|MBIC|MIC50|MIC90|zone|ZOI|diameter)\s*$", re.I)

ORG_ABBREV = re.compile(
    r"^\s*(EC|ECO|ECOLI|SA|SAU|MR|MRSA|MSSA|PA|PAE|PS|CA|KP|KPN|KLEB|BC|BS|SP|SE|ES|EF|"
    r"EFM|LM|ST|STM|AB|ABA|EB|ENC|ENT|PM|SMA|STR|BAC|LIS|SAL|PSE|CD|CDI|HP|CJ|SHI|"
    r"STY|BTH|VCH|NMEN|HI|BIN|LAC)\s*$")


def _outcome_from_ctx(ctx):
    for name, pat in OUTCOME_KW:
        if pat.search(ctx):
            return name
    return ""


def extract_A(df, pmcid, tidx, caption):
    """honey rows x organism columns outcome table (supports MIC/MBC subheader)."""
    best = None
    for hdr_row in range(min(4, len(df))):
        org_cols = [j for j in range(1, df.shape[1])
                    if ORG.search(str(df.iat[hdr_row, j]))]
        if len(org_cols) >= 1 and (best is None or len(org_cols) > len(best[1])):
            best = (hdr_row, org_cols)
    if best is None:
        # fallback: row with >=2 MIC/MBC subheader cells; row above = organism labels
        for sh in range(1, min(4, len(df))):
            sub_cols = [j for j in range(1, df.shape[1])
                        if SUBHDR.match(str(df.iat[sh, j]))]
            if len(sub_cols) >= 2:
                # forward-fill organism labels across merged (colspan) header cells
                ff = {}
                last = ""
                for j in range(1, df.shape[1]):
                    v = str(df.iat[sh - 1, j]).strip()
                    if v:
                        last = v
                    ff[j] = last
                org_cols = [j for j in sub_cols
                            if ORG.search(ff[j]) or ORG_ABBREV.match(ff[j])]
                if len(org_cols) >= 2:
                    best = (sh - 1, org_cols)
                    df = df.copy()
                    for j, v in ff.items():
                        if not str(df.iat[sh - 1, j]).strip():
                            df.iat[sh - 1, j] = v
                    break
        if best is None:
            return _extract_A_transposed(df, pmcid, tidx, caption)
    hdr_row, org_cols = best
    first_org = min(org_cols)
    ctx = caption + " || " + header_text(df)
    outcome = _outcome_from_ctx(ctx)
    unit = detect_unit(ctx)
    if outcome == "zone" and not unit:
        unit = "mm"

    # optional subheader row with MIC/MBC/etc tokens per column
    sub_map = {}
    data_start = hdr_row + 1
    if data_start < len(df):
        for j in org_cols:
            m = SUBHDR.match(str(df.iat[data_start, j]))
            if m:
                sub_map[j] = m.group(1).upper().replace("MFC", "MBC")
        if sub_map:
            data_start += 1

    rows = []
    for i in range(data_start, len(df)):
        lead = [str(df.iat[i, j]).strip() for j in range(first_org)]
        lead = [x for x in lead if x and x.lower() != "nan"]
        honey = " ".join(lead).strip()
        if not honey or re.match(r"^[\W_]+$", honey):
            continue
        if re.search(r"^(note|legend|foot)", honey, re.I):
            continue
        for j in org_cols:
            cell = parse_cell(df.iat[i, j])
            if cell is None:
                continue
            val, cens, u2 = cell
            cu = u2 or unit
            oc = sub_map.get(j, outcome or "unknown")
            if oc in ("MIC", "MBC") and cu == "mm":
                oc = "zone"
            if val > 500 and cu.startswith("%"):
                continue
            rows.append({
                "pmcid": pmcid, "table_idx": tidx, "row_idx": i, "col_idx": j,
                "honey_label": honey[:120],
                "organism_label": str(df.iat[hdr_row, j])[:120],
                "outcome": oc, "value": val, "censor": cens,
                "unit": cu, "unit_ctx": ctx[:200],
                "extract": "auto_A"})
    return rows


def _extract_A_transposed(df, pmcid, tidx, caption):
    """organism rows x honey columns."""
    org_rows = [i for i in range(1, len(df)) if ORG.search(str(df.iat[i, 0]))]
    if len(org_rows) < 2:
        return []
    ctx = caption + " || " + header_text(df)
    outcome = _outcome_from_ctx(ctx)
    unit = detect_unit(ctx)
    if outcome == "zone" and not unit:
        unit = "mm"
    sub_map = {}
    if len(df) > 1:
        for j in range(1, df.shape[1]):
            m = SUBHDR.match(str(df.iat[1, j]))
            if m:
                sub_map[j] = m.group(1).upper().replace("MFC", "MBC")
    # forward-fill top header row (colspan leaves blanks under merged labels)
    hdr0 = [str(df.iat[0, j])[:120] for j in range(df.shape[1])]
    last = ""
    for j in range(1, len(hdr0)):
        if hdr0[j].strip():
            last = hdr0[j].strip()
        else:
            hdr0[j] = last
    rows = []
    for i in org_rows:
        organism = str(df.iat[i, 0])[:120]
        for j in range(1, df.shape[1]):
            honey = hdr0[j]
            if not honey or ORG.search(honey):
                continue
            cell = parse_cell(df.iat[i, j])
            if cell is None:
                continue
            val, cens, u2 = cell
            oc = sub_map.get(j, outcome or "unknown")
            cu = u2 or unit
            if oc in ("MIC", "MBC") and cu == "mm":
                oc = "zone"
            rows.append({
                "pmcid": pmcid, "table_idx": tidx, "row_idx": i, "col_idx": j,
                "honey_label": honey, "organism_label": organism,
                "outcome": oc, "value": val, "censor": cens,
                "unit": cu, "unit_ctx": ctx[:200],
                "extract": "auto_A_t"})
    return rows


def extract_B(df, pmcid, tidx, caption):
    """honey rows x chemistry columns."""
    ctx = caption + " || " + header_text(df)
    # find header row containing >=2 chem columns
    best = None
    for hdr_row in range(min(4, len(df))):
        cols = {}
        for j in range(1, df.shape[1]):
            cell = str(df.iat[hdr_row, j])
            for name, pat in CHEM_COLS.items():
                if pat.search(cell):
                    cols.setdefault(name, j)
        if len(cols) >= 2 and (best is None or len(cols) > len(best[1])):
            best = (hdr_row, cols)
    if best is None:
        return []
    hdr_row, cols = best
    rows = []
    for i in range(hdr_row + 1, len(df)):
        honey = str(df.iat[i, 0]).strip()
        if not honey or honey.lower() == "nan":
            continue
        for name, j in cols.items():
            cell = parse_cell(df.iat[i, j])
            if cell is None:
                continue
            val, cens, u2 = cell
            rows.append({
                "pmcid": pmcid, "table_idx": tidx, "row_idx": i, "col_idx": j,
                "honey_label": honey[:120], "param": name,
                "param_header": str(df.iat[hdr_row, j])[:120],
                "value": val, "censor": cens, "unit": u2 or detect_unit(ctx),
                "extract": "auto_B"})
    return rows


def extract_C(df, pmcid, tidx, caption):
    """concentration-series tables: a column of increasing/decreasing % values.
    Only fires on tables whose caption explicitly signals a dilution series."""
    if not re.search(r"(dilution|concentration series|serial)", caption, re.I):
        return []
    rows = []
    # Orientation 1: a header row containing >=3 % concentration values;
    # each column's header is the concentration, each data row is a honey.
    for hi in range(min(4, len(df))):
        conc_map = {}
        for j in range(1, df.shape[1]):
            cell = str(df.iat[hi, j])
            m = re.match(r"^\s*<?\s*(\d+(?:\.\d+)?)\s*%", cell)
            if m:
                conc_map[j] = float(m.group(1))
        if len(conc_map) >= 3:
            for i in range(hi + 1, len(df)):
                honey = str(df.iat[i, 0]).strip()
                if not honey or honey.lower() in ("nan", ""):
                    honey = str(df.iat[i, 1]).strip() if df.shape[1] > 1 else ""
                for j, conc in conc_map.items():
                    cc = parse_cell(df.iat[i, j])
                    if not cc:
                        continue
                    rows.append({
                        "pmcid": pmcid, "table_idx": tidx, "row_idx": i,
                        "col_idx": j, "conc_label": str(df.iat[hi, j]),
                        "honey_label": honey[:120],
                        "organism_label": str(df.iat[0, j])[:120],
                        "concentration": conc,
                        "outcome": "series", "value": cc[0],
                        "unit": detect_unit(caption),
                        "extract": "auto_C"})
            if rows:
                return rows
    # Orientation 2: a column of increasing/decreasing % values.
    for j in range(df.shape[1]):
        colvals = []
        for i in range(1, len(df)):
            c = parse_cell(df.iat[i, j])
            colvals.append(c[0] if c else None)
        nums = [v for v in colvals if v is not None]
        if len(nums) < 3 or len(nums) < 0.6 * len(colvals):
            continue
        # look like concentrations: all <=100 and monotone-ish
        if all(v <= 100 for v in nums) and len(set(nums)) >= 3:
            hdr = str(df.iat[0, j])
            if not re.search(r"concentr|dilut|% ?\(?(w|v)/?(v|w)?\)?", hdr, re.I):
                continue
            # values must look like a dilution series (monotone or known dilutions)
            ser = sorted(set(nums))
            monotone = nums == sorted(nums) or nums == sorted(nums, reverse=True)
            if not (monotone or len(nums) <= 8):
                continue
            for i in range(1, len(df)):
                c = parse_cell(df.iat[i, j])
                if not c:
                    continue
                for jj in range(df.shape[1]):
                    if jj == j:
                        continue
                    cc = parse_cell(df.iat[i, jj])
                    if not cc:
                        continue
                    rows.append({
                        "pmcid": pmcid, "table_idx": tidx, "row_idx": i,
                        "col_idx": jj, "conc_label": hdr,
                        "honey_label": str(df.iat[i, 0])[:120],
                        "organism_label": str(df.iat[0, jj])[:120],
                        "concentration": c[0],
                        "outcome": "series", "value": cc[0],
                        "unit": detect_unit(caption + " " + str(df.iat[0, jj])),
                        "extract": "auto_C"})
            break
    return rows


def main():
    cat = pd.read_csv(os.path.join(ROOT, "data", "interim", "table_catalog.csv"))
    el = pd.read_csv(os.path.join(ROOT, "data", "interim", "eligible.csv"))
    keep = set(el.loc[el["elig"].isin(["include", "review_flag"]), "pmcid"].dropna())
    rowsA, rowsB, rowsC = [], [], []
    for _, r in cat.iterrows():
        if r["pmcid"] not in keep or not isinstance(r.get("file"), str) or not r["file"]:
            continue
        path = os.path.join(TAB, r["file"])
        if not os.path.exists(path):
            continue
        try:
            df = pd.read_csv(path, header=None, dtype=str).fillna("")
        except Exception:
            continue
        if len(df) < 2:
            continue
        cap = str(r.get("caption", ""))
        rowsA += extract_A(df, r["pmcid"], int(r["table_idx"]), cap)
        rowsB += extract_B(df, r["pmcid"], int(r["table_idx"]), cap)
        rowsC += extract_C(df, r["pmcid"], int(r["table_idx"]), cap)

    for name, rows in (("outcomes_A", rowsA), ("chem_B", rowsB), ("series_C", rowsC)):
        d = pd.DataFrame(rows)
        d.to_csv(os.path.join(ROOT, "data", "interim", f"auto_{name}.csv"), index=False)
        print(name, len(d), "rows from", d["pmcid"].nunique() if len(d) else 0, "studies")


if __name__ == "__main__":
    main()
