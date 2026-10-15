"""Gate 2 targeted rescue: append manually recovered rows to manual_extraction.csv.

Sources (all locally held full text, data/raw/fulltext/<pmcid>.xml):
  PMC13460517 t0  - UMF-graded Manuka MIC (%w/v) vs MGO+water / MGO+sugar controls
  PMC9906859  t3  - zone of inhibition (mm), 5 honeys x 13 XDR S. Typhi
  PMC9906859  t4  - MIC/MBC (%v/v), 5 honeys x 13 XDR S. Typhi
  PMC13315830 t0  - MIC (%v/v), 81 honey samples x 3 H. pylori strains
  PMC13315830 t3  - H2O2 content (mg/mL/h) per honey sample
  PMC4355501  t4  - phenol equivalence (%w/v) mean+SD vs S. Typhi
  PMC3273858  t0  - H2O2 (mM/L) and water activity per honey sample
  PMC10617706 t2  - TPC (ug/g), GOX (mU/mL), H2O2 (uM) per honey sample
  PMC10000891 t1  - MGO (mg/kg), TPC (mg/kg GAE) per honey

Skipped (rationale in qc/GATE2_EVIDENCE_MATURITY.md):
  PMC10617706 antibacterial outcomes (figure-only, no table)
  PMC11083411 (single correlation matrix - cited qualitatively)
  PMC9419396 (presence/absence matrix, no numeric outcome)
  PMC3572166 (qualitative morphology)
  PMC13315830 t2 (honey+Lactobacillus combination - inseparable matrix)
  PMC10051060 (formulation release kinetics - inseparable matrix)
"""
import csv
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(ROOT, "data", "interim", "tables")
OUT = os.path.join(ROOT, "data", "interim", "manual_extraction.csv")

COLS = ["pmcid", "source", "honey_label", "organism", "organism_label", "outcome",
        "concentration_pct", "condition", "value", "sd", "unit", "notes"]


def row(pmcid, source, honey, org, outcome, value, sd="", unit="", notes="", conc="", cond="untreated"):
    return {"pmcid": pmcid, "source": source, "honey_label": honey,
            "organism": org, "organism_label": org, "outcome": outcome, "concentration_pct": conc,
            "condition": cond, "value": value, "sd": sd, "unit": unit,
            "notes": notes}


def ms(x):
    """parse '12.50 ± 0.00' -> (value, sd); also handles '50.00 ±0.00'"""
    x = str(x).replace("±", "+-").replace("+-", "±")
    m = re.match(r"^\s*([<>]?\d+(?:\.\d+)?)\s*(?:±\s*(\d+(?:\.\d+)?))?", x)
    if not m:
        return None, "", ""
    v, sd = m.group(1), m.group(2) or ""
    cens = ""
    if v.startswith(">"):
        v = v[1:]
        cens = "censor=gt"
    elif v.startswith("<"):
        v = v[1:]
        cens = "censor=lt"
    try:
        float(v)
    except ValueError:
        return None, "", ""
    return v, sd, cens


def rows_of(fn):
    return list(csv.reader(open(os.path.join(T, fn))))


def main():
    new = []

    # ---- PMC13460517: UMF grade x species x {honey, MGO+water, MGO+sugar} MIC %w/v
    r = rows_of("PMC13460517_t0.csv")
    grade, mgo = "", ""
    for line in r[2:]:
        if len(line) < 6:
            continue
        if line[0].strip():
            grade, mgo = line[0].strip(), line[1].replace(",", "").strip()
        sp = line[2].strip()
        if not sp:
            continue
        for cond, col in (("Mānuka honey", 3), ("MGO+water", 4), ("MGO+sugar", 5)):
            v, _, cens = ms(line[col])
            if v is None:
                continue
            lab = (f"artificial methylglyoxal+water ({mgo} ppm matched)" if cond=="MGO+water" else f"artificial methylglyoxal+sugar ({mgo} ppm matched)") if cond != "Mānuka honey" \
                else f"Mānuka {grade} (MGO {mgo} ppm)"
            new.append(row("PMC13460517", "t1", lab, sp, "MIC", v, unit="%w/v",
                           notes=cens))

    # ---- PMC9906859: zones (t3) and MIC/MBC %v/v (t4), 5 honeys x 13 isolates
    r = rows_of("PMC9906859_t3.csv")
    honeys = [h.strip() for h in r[0][1:] if h.strip()]
    for line in r[1:]:
        if not line or not line[0].strip():
            continue
        iso = line[0].strip()
        for i, h in enumerate(honeys):
            if i + 1 >= len(line):
                break
            v, sd, _ = ms(line[i + 1])
            if v is None:
                continue
            new.append(row("PMC9906859", "t3", h,
                           f"S. Typhi ({iso}, XDR)", "zone", v, sd=sd, unit="mm"))
    r = rows_of("PMC9906859_t4.csv")
    honeys = [h.strip() for h in r[0][1:] if h.strip()]
    for line in r[2:]:
        if not line or not line[0].strip():
            continue
        iso = line[0].strip()
        for i, h in enumerate(honeys):
            for j, out in enumerate(("MIC", "MBC")):
                c = 1 + 2 * i + j
                if c >= len(line):
                    break
                v, _, _ = ms(line[c])
                if v is None:
                    continue
                new.append(row("PMC9906859", "t4", h,
                               f"S. Typhi ({iso}, XDR)", out, v, unit="%v/v"))

    # ---- PMC13315830: MIC %v/v vs 3 H. pylori strains (t0); H2O2 (t3)
    r = rows_of("PMC13315830_t0.csv")
    for line in r[2:]:
        if len(line) < 4 or not line[0].strip():
            continue
        samp = "Manuka" if line[0].strip() == "M" else f"Honey {line[0].strip()}"
        for i, st in enumerate(("strain 1", "strain 2", "strain 3")):
            v, sd, _ = ms(line[i + 1])
            if v is None:
                continue
            new.append(row("PMC13315830", "t0", samp, f"H. pylori {st}",
                           "MIC", v, sd=sd, unit="%v/v"))
    r = rows_of("PMC13315830_t3.csv")
    for line in r[2:]:
        if len(line) < 2 or not line[0].strip():
            continue
        v, _, _ = ms(line[1])
        if v is None:
            continue
        samp = "Manuka" if line[0].strip() == "M" else f"Honey {line[0].strip()}"
        new.append(row("PMC13315830", "t3", samp, "", "H2O2", v,
                       unit="mg/mL/h", notes="H2O2 production rate"))

    # ---- PMC4355501: phenol equivalence %w/v vs S. Typhi (t4)
    r = rows_of("PMC4355501_t4.csv")
    for line in r[2:]:
        if len(line) < 2 or not line[0].strip():
            continue
        v, sd, _ = ms(line[1])
        if v is None:
            continue
        h = re.sub(r"\s*\(\d+\)\s*$", "", line[0].strip())
        new.append(row("PMC4355501", "t4", h, "S. Typhi", "phenol_equiv",
                       v, sd=sd, unit="%w/v phenol"))

    # ---- PMC3273858: H2O2 (mM/L) + aw per honey (t0)
    r = rows_of("PMC3273858_t0.csv")
    for line in r[1:]:
        if len(line) < 5 or not line[0].strip():
            continue
        lab = f"{line[0].strip()} ({line[1].strip()})"
        v, sd, _ = ms(line[3])
        if v is not None and line[3].strip().upper() != "NA":
            new.append(row("PMC3273858", "t0", lab, "", "H2O2", v, sd=sd,
                           unit="mM/L"))
        v, _, _ = ms(line[4])
        if v is not None and line[4].strip().upper() != "NA":
            new.append(row("PMC3273858", "t0", lab, "", "aw", v, unit="aw"))

    # ---- PMC10617706: TPC, GOX, H2O2 per honey (t2)
    r = rows_of("PMC10617706_t2.csv")
    for line in r[1:]:
        if len(line) < 4 or not line[0].strip():
            continue
        lab = f"New Caledonian honey No. {line[0].strip()}"
        for out, col, un in (("TPC", 1, "µg/g"), ("GOX", 2, "mU/mL"),
                             ("H2O2", 3, "µM")):
            v, sd, _ = ms(line[col])
            if v is None:
                continue
            new.append(row("PMC10617706", "t2", lab, "", out, v, sd=sd,
                           unit=un))

    # ---- PMC10000891: MGO, 3-PLA, GAE per honey (t1)
    r = rows_of("PMC10000891_t1.csv")
    for line in r[1:]:
        if len(line) < 4 or not line[0].strip():
            continue
        lab = line[0].strip()
        for out, col, un in (("MGO", 1, "mg/kg"), ("PLA", 2, "mg/kg"),
                             ("TPC", 3, "mg/kg GAE")):
            v, sd, _ = ms(line[col])
            if v is None:
                continue
            new.append(row("PMC10000891", "t1", lab, "", out, v, sd=sd,
                           unit=un))

    # ---- rewrite the file with the organism_label column added for all rows
    old = []
    if os.path.exists(OUT):
        old = list(csv.DictReader(open(OUT)))
        for rw in old:
            rw.setdefault("organism_label", "")
            if not rw["organism_label"]:
                rw["organism_label"] = rw.get("organism", "")
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for rw in old + new:
            w.writerow(rw)
    print(f"wrote {len(old)} existing + {len(new)} rescued rows to {OUT}")


if __name__ == "__main__":
    main()
