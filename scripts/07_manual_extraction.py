"""Curated extraction of mechanistic datasets verified by hand from parsed tables.

Schema matches data/interim/manual_extraction.csv:
  pmcid, source (table_idx or 'text'), honey_label, organism, outcome,
  concentration_pct, condition (untreated|catalase|...), value, sd, unit, notes
"""
import os

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "interim", "manual_extraction.csv")

ROWS = []


def add(pmcid, source, honey, org, outcome, conc, cond, value, sd, unit, notes=""):
    ROWS.append(dict(pmcid=pmcid, source=source, honey_label=honey, organism=org,
                     outcome=outcome, concentration_pct=conc, condition=cond,
                     value=value, sd=sd, unit=unit, notes=notes))


# ---------------- PMC6659206: Saudi honeys vs MRSA/MSSA, catalase pairs, simulated honey ----
# Table 1 MICs (% v/v): Manuka 14, Sumra 12, Simulated 35 for all MRSA isolates + MSSA; E.coli 15/15/30
for org in ["MRSA (10 clinical isolates)", "MSSA ATCC 29213"]:
    add("PMC6659206", "t1", "Manuka", org, "MIC", None, "untreated", 14, 0.0, "%v/v")
    add("PMC6659206", "t1", "Sumra", org, "MIC", None, "untreated", 12, 0.0, "%v/v")
    add("PMC6659206", "t1", "Simulated honey (sugar)", org, "MIC", None, "untreated", 35, 0.0, "%v/v")
for org in ["Escherichia coli ATCC 25922"]:
    add("PMC6659206", "t1", "Manuka", org, "MIC", None, "untreated", 15, 0.0, "%v/v")
    add("PMC6659206", "t1", "Sumra", org, "MIC", None, "untreated", 15, 0.0, "%v/v")
    add("PMC6659206", "t1", "Simulated honey (sugar)", org, "MIC", None, "untreated", 30, 0.0, "%v/v")

# t2 = MSSA zones; t3 = MRSA zones; cols: 50% water, 50% catalase, 25% water, 25% catalase
saudi = {
    "t2_MSSA": [  # 50w, 50cat, 25w, 25cat
        ("Manuka", 16.8, 15.4, 12.5, 11.1),
        ("H01 Sidr", 16.7, None, 11.3, None),
        ("H02 Talha", 11.3, None, 10.1, None),
        ("H03 Sumra", 18.3, 11.4, 13.0, None),
        ("H04 Sidr", 16.9, None, 10.9, None),
        ("H05 Talha", 15.5, 11.8, 11.2, None),
        ("H06 Sumra", 15.2, None, 10.0, None),
        ("H07 Zahoor", 11.5, None, None, None),
        ("H08 Zahoor", 18.0, None, 12.0, None),
        ("H09 Zahoor", 13.9, None, 10.2, None),
        ("H11 Sidr", 14.1, None, 10.0, None),
    ],
    "t3_MRSA": [
        ("Manuka", 16.0, 14.9, 12.0, 11.1),
        ("H01 Sidr", 17.2, None, 10.2, None),
        ("H02 Talha", 13.4, None, 10.7, None),
        ("H03 Sumra", 18.1, 11.4, 13.0, None),
        ("H04 Sidr", 17.2, None, 10.9, None),
        ("H05 Talha", 14.5, 11.8, 11.1, None),
        ("H06 Sumra", 14.5, None, 10.0, None),
        ("H07 Zahoor", 11.8, None, None, None),
        ("H08 Zahoor", 17.5, None, 11.1, None),
        ("H09 Zahoor", 12.8, None, None, None),
        ("H11 Sidr", 12.6, None, 10.0, None),
    ],
}
for tbl, org in (("t2_MSSA", "MSSA"), ("t3_MRSA", "MRSA")):
    for honey, w50, c50, w25, c25 in saudi[tbl]:
        if w50 is not None:
            add("PMC6659206", tbl.split("_")[0], honey, org, "zone", 50, "untreated", w50, None, "mm")
        if c50 is not None:
            add("PMC6659206", tbl.split("_")[0], honey, org, "zone", 50, "catalase", c50, None, "mm")
        if w25 is not None:
            add("PMC6659206", tbl.split("_")[0], honey, org, "zone", 25, "untreated", w25, None, "mm")
        if c25 is not None:
            add("PMC6659206", tbl.split("_")[0], honey, org, "zone", 25, "catalase", c25, None, "mm")

# ---------------- PMC8021062: Malaysian stingless bee honey, catalase vs untreated, S. aureus ----
for honey, cat, unt in [("A", 10.75, 10.70), ("B", 13.30, 13.24), ("C", 11.05, 10.78),
                        ("D", 10.14, 10.05), ("E", 9.03, 8.75)]:
    add("PMC8021062", "t0", f"Honey {honey}", "Staphylococcus aureus", "zone", None, "catalase", cat, None, "mm")
    add("PMC8021062", "t0", f"Honey {honey}", "Staphylococcus aureus", "zone", None, "untreated", unt, None, "mm")

# ---------------- PMC7076972: Trinidad honeys, zone + phenol equiv; artificial honey = 0 -------
tt = [
    ("M. favosa (Tobago)", {"S. aureus ATCC 25923": (27, 22.7), "S. aureus clinical": (27, 28.6),
                           "E. coli ATCC 25922": (12, 4.9), "E. coli clinical": (14, 8.9),
                           "H. influenzae ATCC 19418": (11.3, 4.5), "S. pyogenes ATCC 19615": (0, 0)}),
    ("F. nigra (Trinidad)", {"S. aureus ATCC 25923": (0, 0), "S. aureus clinical": (0, 0),
                            "E. coli ATCC 25922": (0, 0), "E. coli clinical": (0, 0),
                            "H. influenzae ATCC 19418": (10.3, 3.7), "S. pyogenes ATCC 19615": (15.7, 6.5)}),
    ("F. nigra (Tobago)", {"S. aureus ATCC 25923": (12, 4.5), "S. aureus clinical": (15, 8.7),
                          "E. coli ATCC 25922": (13, 5.9), "E. coli clinical": (0, 0),
                          "H. influenzae ATCC 19418": (16, 8.1), "S. pyogenes ATCC 19615": (23, 13.5)}),
    ("A. mellifera (Aged)", {o: (0, 0) for o in
        ["S. aureus ATCC 25923", "S. aureus clinical", "E. coli ATCC 25922", "E. coli clinical",
         "H. influenzae ATCC 19418", "S. pyogenes ATCC 19615"]}),
    ("A. mellifera (Fresh)", {"S. aureus ATCC 25923": (10, 3.4), "S. aureus clinical": (0, 0),
                             "E. coli ATCC 25922": (0, 0), "E. coli clinical": (0, 0),
                             "H. influenzae ATCC 19418": (0, 0), "S. pyogenes ATCC 19615": (0, 0)}),
    ("Artificial honey", {o: (0, 0) for o in
        ["S. aureus ATCC 25923", "S. aureus clinical", "E. coli ATCC 25922", "E. coli clinical",
         "H. influenzae ATCC 19418", "S. pyogenes ATCC 19615"]}),
]
for honey, orgs in tt:
    for org, (zone, phen) in orgs.items():
        add("PMC7076972", "t1", honey, org, "zone", None, "untreated", zone, None, "mm")
        add("PMC7076972", "t1", honey, org, "phenol_equiv", None, "untreated", phen, None, "%w/v phenol")

# ---------------- PMC8234392: Lemnos honeys, zones at 25%/12.5% v/v, aw/pH, glucose syrup ------
lemnos_orgs = ["S. Enteritidis", "S. Typhimurium", "E. coli", "V. parahaemolyticus",
               "P. aeruginosa", "S. aureus", "S. epidermidis", "E. faecalis",
               "L. monocytogenes", "B. cereus"]
lemnos_25 = {
    "Lemnos honey No. 1": [22.0, 18.0, 22.0, 22.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
    "Lemnos honey No. 2": [21.3, 19.0, 21.3, 20.7, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
    "Lemnos honey No. 3": [20.7, 25.0, 21.3, 23.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
    "Lemnos honey No. 4": [24.0, 20.0, 21.3, 20.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
    "Lemnos honey No. 5": [23.0, 22.0, 21.3, 23.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
    "Lemnos honey No. 6": [20.0, 23.0, 22.0, 21.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
}
lemnos_125 = {
    "Lemnos honey No. 1": [17.0, 19.3, 19.3, 19.5, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
    "Lemnos honey No. 2": [19.0, 14.5, 18.7, 19.3, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
    "Lemnos honey No. 3": [17.5, 9.5, 19.3, 18.3, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
    "Lemnos honey No. 4": [19.7, 18.3, 18.3, 18.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
    "Lemnos honey No. 5": [20.0, 12.0, 21.0, 21.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
    "Lemnos honey No. 6": [5.0, 12.0, 20.0, 18.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
}
for honey in lemnos_25:
    for org, z in zip(lemnos_orgs, lemnos_25[honey]):
        add("PMC8234392", "t0", honey, org, "zone", 25.0, "untreated", z, None, "mm", "zone=5 mm = no inhibition (well diameter)")
    for org, z in zip(lemnos_orgs, lemnos_125[honey]):
        add("PMC8234392", "t0", honey, org, "zone", 12.5, "untreated", z, None, "mm", "zone=5 mm = no inhibition (well diameter)")
# MIC/MBC (t1): S. Typhimurium / S. aureus
lemnos_mic = [("Lemnos honey No. 1", ">25", ">25"), ("Lemnos honey No. 2", "12.5", "12.5"),
              ("Lemnos honey No. 3", ">25", ">25"), ("Lemnos honey No. 4", "25", "25"),
              ("Lemnos honey No. 5", ">25", ">25"), ("Lemnos honey No. 6", ">25", "25"),
              ("Lemnos honey No. 7", "25", "25"), ("Lemnos honey No. 8", "25", "25"),
              ("Manuka honey", ">25", "25"), ("Glucose syrup (82% v/v)", ">25", ">25")]
for honey, st, sa in lemnos_mic:
    for org, v in (("S. Typhimurium", st), ("S. aureus", sa)):
        cens = "gt" if str(v).startswith(">") else ""
        add("PMC8234392", "t1", honey, org, "MIC", None, "untreated",
            float(str(v).lstrip(">")), None, "%v/v", f"censor={cens}")
        add("PMC8234392", "t1", honey, org, "MBC", None, "untreated",
            float(str(v).lstrip(">")), None, "%v/v", f"censor={cens}")  # MIC==MBC reported per table
# aw / pH (t2)
lemnos_chem = [("Lemnos honey No. 1", 3.55, 0.574), ("Lemnos honey No. 2", 3.61, 0.587),
               ("Lemnos honey No. 3", 3.60, 0.568), ("Lemnos honey No. 4", 3.62, 0.574),
               ("Lemnos honey No. 5", 3.60, 0.597), ("Lemnos honey No. 6", 3.67, 0.551),
               ("Lemnos honey No. 7", 3.62, 0.570), ("Lemnos honey No. 8", 3.63, 0.604),
               ("Manuka honey", 4.26, 0.627), ("Glucose syrup (82% v/v)", 4.85, 0.731)]
for honey, ph, aw in lemnos_chem:
    add("PMC8234392", "t2", honey, "", "pH", None, "", ph, None, "pH")
    add("PMC8234392", "t2", honey, "", "aw", None, "", aw, None, "aw")

# ---------------- PMC8944737: honeys outperforming manuka by concentration (counts) ----------
outperf = {  # organism: [75%,50%,25%,12.5%,6.25%]
    "Enterobacter cloacae subsp. dissolvens": [2, 8, 16, 18, 5],
    "Pseudomonas aeruginosa": [7, 6, 23, 9, 9],
    "Klebsiella pneumoniae subsp. pneumoniae (1)": [6, 11, 30, 10, None],
    "Klebsiella pneumoniae subsp. pneumoniae (2)": [5, 19, 31, 12, 2],
}
for org, vals in outperf.items():
    for conc, v in zip([75, 50, 25, 12.5, 6.25], vals):
        if v is not None:
            add("PMC8944737", "t3", "Greek honeys (n=42)", org, "n_outperform_manuka",
                conc, "untreated", v, None, "count")

# ---------------- PMC11376693: Manuka UMF15+ zones at 50/80/100% vs CRE isolates -------------
cre50 = [4,2,2,0,0,3,6,4,3,4,4,6,2,2,3,6,0,2,2,7]
cre80 = [12,7,8,6,8,10,10,7,8,12,8,11,7,8,10,9,7,10,10,12]
cre100 = [14,9,9,10,10,12,12,10,9,12,9,12,7,9,12,10,8,10,10,12]
for i in range(20):
    for conc, arr in ((50,cre50),(80,cre80),(100,cre100)):
        add("PMC11376693", "t1", "Manuka UMF15+", f"CRE isolate {i+1}", "zone",
            conc, "untreated", arr[i], None, "mm")
for org, z50, z80, z100 in [("E. coli ATCC", 10, 13, 14), ("K. pneumoniae ATCC", 8, 12, 14)]:
    for conc, z in ((50, z50), (80, z80), (100, z100)):
        add("PMC11376693", "t1", "Manuka UMF15+", org, "zone", conc, "untreated", z, None, "mm")

# ---------------- PMC12532491: raw honey zones at 0/25/50/75/100% vs 5 organisms -------------
eth = {
    "Escherichia coli": [0, 15.73, 21.18, 21.68, 22.02],
    "Staphylococcus aureus": [0, 9.21, 12.42, 13.26, 16.45],
    "Klebsiella pneumoniae": [0, 1.23, 5.43, 8.71, 11.55],
    "Pseudomonas aeruginosa": [0, 0.0, 0.57, 0.62, 1.93],
    "Salmonella typhi": [0, 10.08, 12.63, 12.76, 18.16],
}
for org, vals in eth.items():
    for conc, v in zip([0, 25, 50, 75, 100], vals):
        add("PMC12532491", "t0", "Apis mellifera honey (Awi, Ethiopia)", org, "zone",
            conc, "untreated", v, None, "mm")

# ---------------- PMC9958606: viable cells % for 5 honeys x 3 organisms ----------------------
# t3: % viable cells (at honey MIC? columns 1,2,3 = organisms) - encode organism order per caption:
# organisms tested: S. epidermidis, MRSA, P. aeruginosa
for honey, vals in [("black locust", [57.4, 62.7, 52.7]), ("chestnut", [56.7, 50.4, 52.3]),
                    ("goldenrod", [67.4, 53.7, 56.7]), ("linden", [61.1, 61.2, 62.8]),
                    ("milkweed", [72.1, 75.2, 79.4])]:
    for org, v in zip(["S. epidermidis", "MRSA", "P. aeruginosa"], vals):
        add("PMC9958606", "t3", honey, org, "pct_viable", None, "untreated", v, None, "%")

# ---------------- PMC8209695: antimicrobial activity (% phenol) pre/post storage + max H2O2 ---
for honey, act0, act1, h2o2 in [
    ("Banksia 11", 17.1, 10.3, 1.14), ("Jarrah 2017", None, 12.9, 1.59),
    ("Jarrah 5", 25.4, 18.4, 2.95), ("Jarrah 8", 25.1, 17.1, 2.77),
    ("Jarrah 10", 25.7, 17.5, 2.86), ("Jarrah 13", 28.1, 23.4, 3.84),
    ("Karri 3", 29.6, 25.7, 2.22), ("Marri 6", 28.6, 24.0, 1.44),
    ("Marri 8", 27.2, 24.3, 2.38), ("Marri 10", 29.3, 20.7, 2.06),
    ("Marri 11", 29.7, 25.2, 2.54)]:
    if act0 is not None:
        add("PMC8209695", "t0", honey, "Staphylococcus aureus", "phenol_equiv", None,
            "untreated (original)", act0, None, "%w/v phenol")
    add("PMC8209695", "t0", honey, "Staphylococcus aureus", "phenol_equiv", None,
        "untreated (retested)", act1, None, "%w/v phenol")
    add("PMC8209695", "t0", honey, "", "H2O2", None, "", h2o2, None, "mM max")

# ---------------- PMC10141347: color, TPC, ORAC, H2O2 production ------------------------------
for honey, src, color, tpc, orac, h2o2 in [
    ("H77", "Buckwheat", 1.27, 513.25, 19.13, 1319.3), ("H76", "Buckwheat", 0.72, 318.74, 19.77, 1208),
    ("H226", "Buckwheat", 0.62, 362.86, 15.45, 1152), ("H23", "Buckwheat", 1.03, 410, 15.28, 1210),
    ("H149", "Buckwheat", 0.88, 408.03, 12.75, 1470), ("H221", "Buckwheat (light)", 0.38, 144, 5.31, 886),
    ("H208", "Buckwheat (light)", 0.37, 143.55, 4.86, 680), ("H11", "Wildflower/clover", 0.13, 106.97, 5.37, 1280),
    ("H210", "Wildflower", 0.30, 120.2, 4.74, 560), ("H20", "Sweet clover/buckwheat", 0.24, 83.75, 4.49, 1220),
    ("114", "Sunflower", 0.12, 80.82, 2.75, 424), ("H62", "Borage", 0.05, 66.45, 2.84, 529)]:
    add("PMC10141347", "t0", honey, "", "H2O2", None, "", h2o2, None, "fluorescence a.u.",
        f"source={src}")
    add("PMC10141347", "t0", honey, "", "TPC", None, "", tpc, None, "ug GAE/g")
    add("PMC10141347", "t0", honey, "", "color", None, "", color, None, "A560-720")

# ---------------- PMC9333225: MGO-spiked multifloral honey MICs -------------------------------
mgo_spike = [("MGO alone", "128 mg/l", "256 mg/l", "128 mg/l", "512 mg/l"),
             ("Multifloral honey alone", ">30%", ">30%", "29%", "25%"),
             ("Multifloral + 50 mg/kg MGO", "28%", ">30%", "29%", "24%"),
             ("Multifloral + 100 mg/kg MGO", "19%", ">30%", "25%", "24%"),
             ("Multifloral + 250 mg/kg MGO", "12%", "25%", "16%", "23%"),
             ("Multifloral + 500 mg/kg MGO", "8%", "17%", "10%", "21%"),
             ("Multifloral + 750 mg/kg MGO", "6%", "12%", "9%", "18%"),
             ("Multifloral + 1000 mg/kg MGO", "4%", "10%", "6%", "15%")]
for combo, sa, ef, ec, pa in mgo_spike:
    for org, v in (("S. aureus ATCC 29213", sa), ("E. faecalis ATCC 29212", ef),
                   ("E. coli ATCC 25922", ec), ("P. aeruginosa ATCC 27853", pa)):
        vs = str(v)
        cens = "gt" if vs.startswith(">") else ""
        unit = "mg/l" if "mg/l" in vs else "%"
        add("PMC9333225", "t4", combo, org, "MIC", None, "MGO-spike",
            float(vs.replace(">", "").replace("%", "").replace(" mg/l", "")), None,
            unit, f"censor={cens}")

pd.DataFrame(ROWS).to_csv(OUT, index=False)
print("manual extraction rows:", len(ROWS), "| studies:", pd.DataFrame(ROWS)["pmcid"].nunique())
