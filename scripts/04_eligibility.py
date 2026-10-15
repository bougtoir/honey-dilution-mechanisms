"""Full-text-availability-aware eligibility classification of the 726 candidates.

Rules implement the eligibility criteria in the protocol:
  include: quantitative primary honey antibacterial study, interpretable outcome
  exclude: reviews, fungal-only, formulations with inseparable actives,
           qualitative-only reports, off-topic, non-bacterial outcomes.
Output: data/interim/eligible.csv with decision + reason per record.
"""
import os
import re

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

QUANT = re.compile(
    r"(\bMIC\b|\bMBC\b|minimum inhibitory|minimum bactericidal|inhibition zone|"
    r"zone of inhibition|inhibition of growth|growth inhibition|\binhibit(?:ed|ion)\b.{0,40}\d|"
    r"phenol (equivalen|coefficient)|IC50|IC90|CFU|log reduction|time-?kill|"
    r"\d+(?:\.\d+)?\s*(?:%|mg/mL|µg/mL|ug/mL|mm\b)|turbidimetr|optical density|\bOD\b)", re.I)

FORMULATION = re.compile(
    r"(electrospun|scaffold|nanofib|hydrogel|nanoparticle|nano-?emulsion|liposom|"
    r"microemulsion|coating|implant|bandage|wound dressing|ointment|cream formulation|"
    r"loaded with|impregnat|encapsulat|biofilm removal device|patches|suture)", re.I)

FUNGAL_ONLY = re.compile(
    r"candida|yeast|fungal|fungus|dermatophyte|aspergill|malassezia|sporothrix|"
    r"trichophyton|mould|mold|onychomycosis", re.I)

BACT = re.compile(
    r"staphylococc|streptococc|pseudomon|escherichia|e\. ?coli|enterococc|klebsiella|"
    r"bacill|salmonella|listeria|proteus|acinetobacter|helicobacter|MRSA|MSSA|VRE|"
    r"burkholderia|clostridi|mycobacter|bacteria|bactericid|bacteriostat|gram-?pos|"
    r"gram-?neg|s\. ?aureus|p\. ?aeruginosa", re.I)

COMBINATION_MAIN = re.compile(
    r"(combined with|in combination|synerg\w+ (?:with|between).{0,30}(antibiotic|"
    r"essential oil|silver|phage|drug)|plus.{0,20}(antibiotic|essential oil))", re.I)

NONPRIMARY = re.compile(r"(clinical trial|randomi[sz]ed|patients|in vivo wound|"
                        r"rat wound model|histolog)", re.I)


def classify(row):
    t = f"{row.get('title','')} {row.get('abstract','')}"
    tl = t.lower()
    title = str(row.get("title", ""))

    if "honey" not in tl and "manuka" not in tl:
        return "exclude", "honey not a test article"
    if FORMULATION.search(tl) and not re.search(r"honey alone|unformulated honey", tl):
        return "exclude", "formulation with inseparable matrix"
    if FUNGAL_ONLY.search(tl) and not BACT.search(tl):
        return "exclude", "non-bacterial outcome only"
    if re.search(r"leishmania|giardia|trichomonas|toxoplasma|plasmodium", tl) and not BACT.search(tl):
        return "exclude", "parasite outcome only"
    if re.search(r"\bvirus|viral|bacteriophage|phage therapy\b", tl) and not BACT.search(tl):
        return "exclude", "viral/phage outcome only"
    if NONPRIMARY.search(tl) and not QUANT.search(tl):
        return "exclude", "clinical/in-vivo without microbiological assay"
    if not QUANT.search(t):
        return "exclude", "no quantitative antibacterial outcome"
    if re.search(r"propolis|royal jelly|bee venom|bee pollen", tl) and "honey" not in title.lower() and "manuka" not in title.lower():
        return "exclude", "non-honey bee product is main article"
    if COMBINATION_MAIN.search(tl) and not re.search(r"honey alone|alone was|honey itself|also tested.{0,30}alone", tl):
        return "review_flag", "combination therapy - verify honey-alone arm"
    return "include", "meets criteria"


def main():
    cand = pd.read_csv(os.path.join(ROOT, "data", "interim", "candidates_ranked.csv"))
    res = cand.apply(classify, axis=1, result_type="expand")
    cand["elig"] = res[0]
    cand["elig_reason"] = res[1]
    cand.to_csv(os.path.join(ROOT, "data", "interim", "eligible.csv"), index=False)
    print(cand["elig"].value_counts())
    print("\nreasons:")
    print(cand["elig_reason"].value_counts().head(15))
    inc = cand[cand["elig"] == "include"]
    print(f"\nincluded: {len(inc)}; with PMCID: {inc['pmcid'].notna().sum()}")


if __name__ == "__main__":
    main()
