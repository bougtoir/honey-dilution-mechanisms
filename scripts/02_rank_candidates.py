"""Rank stage-2 candidates by relevance for manual eligibility review."""
import os
import re

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GROUPS = {
    "dilution": r"dilut|concentration series|range of concentration|serial",
    "mic": r"minimum inhibitory|\bMIC\b|\bMBC\b|IC50|IC90",
    "peroxide": r"hydrogen peroxide|H2O2|glucose oxidase|catalase",
    "osmotic": r"water activity|osmotic|osmolarity|artificial honey|sugar solution|sugar control",
    "mgo": r"methylglyoxal|\bMGO\b|non-?peroxide",
    "chem": r"phenolic|flavonoid|Brix|moisture|pH|acidity",
    "zone": r"inhibition zone|zone of inhibition|well diffusion|agar diffusion",
    "orgs": r"staphylococc|pseudomon|escherichia|MRSA|streptococc|enterococc|klebsiella|"
            r"bacillus|salmonella|listeria|proteus|acinetobacter",
    "quant": r"\d+\s*(%|mg/mL|µg/mL|ug/mL|mm\b)|mean|SD|standard deviation",
    "manuka": r"manuka|m[eé]dicinal|medical grade|medihoney|UMF",
}


def main():
    cand = pd.read_csv(os.path.join(ROOT, "data", "interim", "candidates.csv"))
    txt = (cand["title"].fillna("") + " " + cand["abstract"].fillna(""))
    score = pd.Series(0.0, index=cand.index)
    hits = {}
    for name, pat in GROUPS.items():
        h = txt.str.contains(pat, case=False, regex=True)
        hits[name] = h
        score += h.astype(int) * (2 if name in ("dilution", "peroxide", "osmotic", "mgo") else 1)
    cand["score"] = score
    for name, h in hits.items():
        cand[f"f_{name}"] = h

    # boost OA + has abstract
    cand["score"] += cand["pmcid"].notna().astype(int) * 1.5
    cand["score"] += (cand["abstract"].fillna("").str.len() > 200).astype(int) * 0.5
    cand = cand.sort_values("score", ascending=False)
    cand.to_csv(os.path.join(ROOT, "data", "interim", "candidates_ranked.csv"), index=False)
    print(cand["score"].describe())
    print("n score>=6:", (cand["score"] >= 6).sum(), "| n score>=5:", (cand["score"] >= 5).sum())


if __name__ == "__main__":
    main()
