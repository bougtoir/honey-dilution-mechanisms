"""Generate publication-quality figures (PNG + TIFF, 300 dpi)."""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(ROOT, "results", "figures")
os.makedirs(FIG, exist_ok=True)

plt.rcParams.update({"font.size": 8, "font.family": "DejaVu Sans",
                     "axes.linewidth": 0.6, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 300})


def save(fig, name):
    fig.savefig(os.path.join(FIG, name + ".png"), dpi=300, bbox_inches="tight")
    # Elsevier: combination artwork (line+halftone) requires >=500 dpi TIFF
    fig.savefig(os.path.join(FIG, name + ".tiff"), dpi=500, bbox_inches="tight",
                format="tiff", pil_kwargs={"compression": "tiff_lzw"})
    fig.savefig(os.path.join(FIG, name + ".svg"), bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


def fig1_prisma():
    """PRISMA-2020-style flow with counts computed live from pipeline outputs."""
    import json
    import glob
    counts = json.load(open(os.path.join(ROOT, "logs", "prisma_counts.json")))
    el = pd.read_csv(os.path.join(ROOT, "data", "interim", "eligible.csv"))
    inc = el[el["elig"].isin(["include", "review_flag"])]
    n_inc = len(inc)
    n_pmcid = int(inc["pmcid"].notna().sum())
    have = {os.path.basename(f)[:-4]
            for f in glob.glob(os.path.join(ROOT, "data", "raw", "fulltext", "*.xml"))}
    n_xml = int(inc["pmcid"].isin(have).sum())
    ext = pd.read_csv(os.path.join(ROOT, "data", "processed", "extraction.csv"))
    n_ext = ext["study_id"].nunique()
    n_no_pmcid = n_inc - n_pmcid
    n_no_xml = n_pmcid - n_xml
    n_no_data = n_xml - n_ext
    n_excl_elig = int((el["elig"] == "exclude").sum())

    main_boxes = [
        (f"Records identified (n = {counts['raw_records']:,})\n"
         "PubMed, Europe PMC, Crossref,\ncitation mining, repositories", 0.905),
        (f"Records screened\n(title/abstract)\nn = {counts['unique_screened']:,}", 0.72),
        (f"Reports assessed for\neligibility\nn = {counts['screen1_passed']:,}", 0.51),
        (f"Studies included in\nqualitative synthesis\nn = {n_inc}", 0.30),
        (f"Studies included in\nquantitative synthesis\nn = {n_ext}", 0.09),
    ]
    side_boxes = [
        (f"Duplicates removed\nn = {counts['duplicates_removed']:,}", 0.72),
        (f"Records excluded\nn = {counts['excluded_screen1']:,}", 0.51),
        (f"Reports excluded\nn = {n_excl_elig}", 0.30),
        ("Reports not retrieved or\nnot extractable:\n"
         f"no PMC full text n = {n_no_pmcid + n_no_xml};\n"
         f"full text without\nextractable outcome data\nn = {n_no_data}", 0.09),
    ]
    fig, ax = plt.subplots(figsize=(6.7, 6.0))
    ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    for txt, y in main_boxes:
        ax.text(0.02, y, txt, fontsize=7.5, va="center",
                bbox=dict(boxstyle="round,pad=0.4", fc="#dce9f5", ec="#33608a", lw=0.8),
                transform=ax.transAxes)
    for txt, y in side_boxes:
        ax.text(0.55, y, txt, fontsize=7, va="center",
                bbox=dict(boxstyle="round,pad=0.35", fc="#f5e6dc", ec="#8a5a33", lw=0.8),
                transform=ax.transAxes)
    for i in range(len(main_boxes) - 1):
        ax.annotate("", xy=(0.16, main_boxes[i + 1][1] + 0.055),
                    xytext=(0.16, main_boxes[i][1] - 0.055),
                    xycoords="axes fraction",
                    arrowprops=dict(arrowstyle="->", lw=0.9, color="#33608a"))
    for _, y in side_boxes:
        ax.annotate("", xy=(0.53, y), xytext=(0.34, y),
                    xycoords="axes fraction",
                    arrowprops=dict(arrowstyle="->", lw=0.9, color="#8a5a33"))
    ax.set_title("PRISMA 2020-style study flow", fontsize=9)
    save(fig, "fig1_prisma")


def fig2_conc_response(df):
    fig, axes = plt.subplots(2, 2, figsize=(6.8, 5.2))
    # A: zones vs concentration, PMC12532491
    ax = axes[0, 0]
    g = df[(df.study_id == "PMC12532491") & df.concentration_pct.notna() &
           (df.outcome == "zone")]
    for org, gg in g.groupby("organism"):
        gg = gg.sort_values("concentration_pct")
        ax.plot(gg.concentration_pct, gg.value, "o-", ms=3, lw=0.9, label=org)
    ax.set_xlabel("Honey concentration (%)"); ax.set_ylabel("Inhibition zone (mm)")
    ax.set_title("A  Zone vs concentration (PMC12532491)", fontsize=8)
    ax.legend(fontsize=5.5, frameon=False)
    # B: Manuka UMF15+ zones vs conc, PMC11376693
    ax = axes[0, 1]
    g = df[(df.study_id == "PMC11376693") & df.concentration_pct.notna() &
           (df.outcome == "zone")]
    for org, gg in g.groupby("organism"):
        gg = gg.groupby("concentration_pct")["value"].mean().reset_index()
        ax.plot(gg.concentration_pct, gg.value, "o-", ms=3, lw=0.9, label=org)
    ax.set_xlabel("Honey concentration (%)"); ax.set_ylabel("Inhibition zone (mm)")
    ax.set_title("B  Manuka UMF15+ zone vs conc (PMC11376693)", fontsize=8)
    ax.legend(fontsize=5.5, frameon=False)
    # C: biofilm inhibition vs conc, PMC11792292
    ax = axes[1, 0]
    g = df[(df.study_id == "PMC11792292") & df.concentration_pct.notna()]
    for honey, gg in g.groupby("honey_label"):
        gg = gg.sort_values("concentration_pct")
        ax.plot(gg.concentration_pct, gg.value, "s-", ms=3, lw=0.9, label=honey)
    ax.set_xlabel("Honey concentration (%)"); ax.set_ylabel("Biofilm inhibition (%)")
    ax.set_title("C  Biofilm inhibition vs conc (PMC11792292)", fontsize=8)
    ax.legend(fontsize=5.5, frameon=False)
    # D: pH vs dilution, PMC2478674
    ax = axes[1, 1]
    g = df[(df.study_id == "PMC2478674") & (df.outcome == "series")]
    for honey, gg in g.groupby("honey_label"):
        gg = gg.sort_values("concentration_pct")
        ax.plot(gg.concentration_pct, gg.value, "o-", ms=3, lw=0.9,
                label=honey.split("(")[-1].rstrip(")"))
    ax.set_xlabel("Honey concentration (%)"); ax.set_ylabel("pH")
    ax.set_title("D  pH rises on dilution (PMC2478674)", fontsize=8)
    ax.legend(fontsize=5.5, frameon=False)
    fig.tight_layout()
    save(fig, "fig2_conc_response")


def fig3_natural_vs_artificial():
    P = pd.read_csv(os.path.join(ROOT, "results", "tables",
                                 "natural_vs_artificial_pairs.csv"))
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 3.0))
    ax = axes[0]
    z = P[P.outcome == "zone"]
    for _, r in z.iterrows():
        ax.plot([0, 1], [r.artificial_mean, r.natural_mean], "o-", color="#33608a",
                alpha=0.6, ms=3, lw=0.8)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["Artificial\nhoney", "Natural\nhoney"])
    ax.set_ylabel("Inhibition zone (mm)")
    ax.set_title(f"A  Paired zones (n={len(z)})", fontsize=8)
    ax = axes[1]
    m = P[P.outcome.isin(["MIC", "MBC"])]
    ax.scatter(m.artificial_mean, m.natural_mean, s=14, color="#8a5a33", alpha=0.7)
    lim = max(m.artificial_mean.max(), m.natural_mean.max()) * 1.1
    ax.plot([0, lim], [0, lim], "k--", lw=0.7)
    ax.set_xlabel("Artificial honey MIC/MBC (%)"); ax.set_ylabel("Natural honey MIC/MBC (%)")
    ax.set_title(f"B  MIC/MBC pairs (n={len(m)})", fontsize=8)
    fig.tight_layout()
    save(fig, "fig3_natural_vs_artificial")


def fig4_chemistry():
    J = pd.read_csv(os.path.join(ROOT, "results", "tables", "outcome_chem_joined.csv"))
    fig, axes = plt.subplots(2, 2, figsize=(6.8, 5.2))
    specs = [("MGO", "MIC", "MGO (mg/kg)", "MIC (%)", "log"),
             ("moisture", "MIC", "Moisture (%)", "MIC (%)", "log"),
             ("H2O2", "MIC", "H2O2 (reported units)", "MIC (%)", "log"),
             ("pH", "zone", "pH", "Inhibition zone (mm)", "lin")]
    for ax, (par, outc, xl, yl, _) in zip(axes.flat, specs):
        jj = J[(J.outcome == outc) & J[par].notna() & (J.unit=="%"
                                                     if outc == "MIC" else True)]
        jj = jj.dropna(subset=["value"])
        ax.scatter(jj[par], jj.value, s=10, alpha=0.5, color="#33608a")
        if len(jj) >= 12:
            from scipy import stats as st
            rho, p = st.spearmanr(jj[par], jj.value)
            ax.set_title(f"{par} vs {outc}: rho={rho:.2f}, n={len(jj)}", fontsize=8)
        ax.set_xlabel(xl); ax.set_ylabel(yl)
        if outc == "MIC":
            ax.set_yscale("log")
    fig.suptitle("Cross-study chemistry-outcome associations", fontsize=9)
    fig.tight_layout()
    save(fig, "fig4_chemistry")


def fig5_catalase():
    K = pd.read_csv(os.path.join(ROOT, "results", "tables", "catalase_pairs.csv"))
    fig, ax = plt.subplots(figsize=(4.4, 3.4))
    for sid, g in K.groupby("study_id"):
        for _, r in g.iterrows():
            ax.plot([0, 1], [r.untreated, r.catalase], "o-", ms=4, lw=1.0,
                    color="#33608a" if sid == "PMC6659206" else "#8a5a33", alpha=0.7)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["Untreated", "Catalase-treated"])
    ax.set_ylabel("Antibacterial activity (as reported)")
    ax.set_title(f"Residual activity after catalase\n(paired, n={len(K)}, "
                 f"{K.study_id.nunique()} studies)", fontsize=8.5)
    save(fig, "fig5_catalase")


def fig6_organisms(df):
    mic = df[(df.outcome == "MIC") & df.unit.astype(str).eq("%") &
             (df.value > 0)]
    order = mic.groupby("organism")["value"].median().sort_values().index[:12]
    d = [mic[mic.organism == o]["value"].values for o in order]
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    bp = ax.boxplot(d, vert=False, showfliers=False, widths=0.6,
                    medianprops=dict(color="#8a5a33", lw=1.2))
    ax.set_yticklabels(order, fontsize=7)
    ax.set_xlabel("MIC (% honey, as reported)")
    ax.set_xscale("log")
    ax.set_xticks([1, 5, 10, 25, 50, 100])
    ax.set_xticklabels(["1", "5", "10", "25", "50", "100"])
    ax.set_title("MIC distributions by organism (%-unit studies)", fontsize=8.5)
    fig.tight_layout()
    save(fig, "fig6_organisms")


def main():
    df = pd.read_csv(os.path.join(ROOT, "data", "processed", "extraction.csv"))
    fig1_prisma()
    fig2_conc_response(df)
    fig3_natural_vs_artificial()
    fig4_chemistry()
    fig5_catalase()
    fig6_organisms(df)


if __name__ == "__main__":
    main()
