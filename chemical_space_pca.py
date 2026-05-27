#!/usr/bin/env python3
"""
Chemical space PCA: BBB Magnolia database vs ChEMBL DENV actives.

Computes 10 physicochemical descriptors for all compounds, runs PCA,
visualizes overlap, and ranks BBB compounds by proximity to known
DENV inhibitors (NS2B-NS3 protease and NS5 RdRp), stratified by target.

See CHEMICAL_SPACE_ANALYSIS_METHODOLOGY.md for full documentation.

Usage:
    python bbb/chemical_space_pca.py
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from rdkit import Chem, RDLogger
from rdkit.Chem import AllChem, DataStructs, Descriptors
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

RDLogger.logger().setLevel(RDLogger.ERROR)

REPO = Path(__file__).resolve().parent.parent
BBB_CSV = REPO / "bbb/data/magnolia_bbb_database.csv"
NS3_CSV = REPO / "data/dengue/inputs/validation/chembl_actives/NS2B_NS3_protease_actives.csv"
NS5_CSV = REPO / "data/dengue/inputs/validation/chembl_actives/NS5_RdRp_actives.csv"
OUT_DIR = REPO / "bbb/data"
FIG_DIR = OUT_DIR / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

DESCRIPTORS = [
    ("MW", Descriptors.MolWt),
    ("LogP", Descriptors.MolLogP),
    ("HBD", Descriptors.NumHDonors),
    ("HBA", Descriptors.NumHAcceptors),
    ("TPSA", Descriptors.TPSA),
    ("RotBonds", Descriptors.NumRotatableBonds),
    ("Rings", Descriptors.RingCount),
    ("AromaticRings", Descriptors.NumAromaticRings),
    ("FractionCSP3", Descriptors.FractionCSP3),
    ("MolMR", Descriptors.MolMR),
]


def compute_descriptors(smiles_list: list[str]) -> tuple[pd.DataFrame, list[int]]:
    """Compute descriptors for a list of SMILES. Returns (df, failed_indices)."""
    records = []
    failed = []
    for i, smi in enumerate(smiles_list):
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            failed.append(i)
            records.append({name: np.nan for name, _ in DESCRIPTORS})
            continue
        row = {}
        for name, func in DESCRIPTORS:
            try:
                row[name] = func(mol)
            except Exception:
                row[name] = np.nan
        records.append(row)
    return pd.DataFrame(records), failed


def compute_ecfp4(smiles_list: list[str]) -> list:
    """Compute ECFP4 fingerprints (Morgan radius=2, 2048 bits)."""
    fps = []
    for smi in smiles_list:
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            fps.append(None)
        else:
            fps.append(AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048))
    return fps


def max_tanimoto(fp, fp_list: list) -> tuple[float, int]:
    """Return (max_similarity, index_of_best_match) against a list of fingerprints."""
    if fp is None:
        return 0.0, -1
    best_sim = 0.0
    best_idx = -1
    for j, fp2 in enumerate(fp_list):
        if fp2 is None:
            continue
        sim = DataStructs.TanimotoSimilarity(fp, fp2)
        if sim > best_sim:
            best_sim = sim
            best_idx = j
    return best_sim, best_idx


def main():
    print("=" * 70)
    print("  Chemical Space PCA: BBB Database vs ChEMBL DENV Actives")
    print("=" * 70)

    # ── Load data ─────────────────────────────────────────────────────
    bbb = pd.read_csv(BBB_CSV)
    ns3 = pd.read_csv(NS3_CSV)
    ns5 = pd.read_csv(NS5_CSV)

    print(f"\nLoaded: BBB={len(bbb)}, NS3 actives={len(ns3)}, NS5 actives={len(ns5)}")

    bbb_smiles = bbb["canonical_smiles"].tolist()
    ns3_smiles = ns3["smiles"].tolist()
    ns5_smiles = ns5["smiles"].tolist()
    all_smiles = bbb_smiles + ns3_smiles + ns5_smiles

    labels = (
        ["BBB"] * len(bbb)
        + ["NS2B-NS3 protease"] * len(ns3)
        + ["NS5 RdRp"] * len(ns5)
    )

    # ── Step 1: Compute descriptors ───────────────────────────────────
    print("\n[1/7] Computing molecular descriptors...")
    desc_df, failed = compute_descriptors(all_smiles)
    desc_df["group"] = labels
    desc_df["smiles"] = all_smiles

    valid_mask = ~desc_df[[name for name, _ in DESCRIPTORS]].isna().any(axis=1)
    n_failed = (~valid_mask).sum()
    if n_failed > 0:
        print(f"  WARNING: {n_failed} compounds failed descriptor computation, excluded from PCA")
    desc_valid = desc_df[valid_mask].copy().reset_index(drop=True)
    print(f"  Valid compounds: {len(desc_valid)} / {len(desc_df)}")

    feat_cols = [name for name, _ in DESCRIPTORS]

    # ── Step 2: Standardize ───────────────────────────────────────────
    print("[2/7] Standardizing descriptors...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(desc_valid[feat_cols].values)

    # ── Step 3: PCA ───────────────────────────────────────────────────
    print("[3/7] Running PCA...")
    pca = PCA(n_components=min(len(feat_cols), 5))
    X_pca = pca.fit_transform(X_scaled)

    for i, var in enumerate(pca.explained_variance_ratio_):
        print(f"  PC{i+1}: {var*100:.1f}% variance")
    print(f"  Cumulative (PC1-3): {sum(pca.explained_variance_ratio_[:3])*100:.1f}%")

    desc_valid["PC1"] = X_pca[:, 0]
    desc_valid["PC2"] = X_pca[:, 1]
    desc_valid["PC3"] = X_pca[:, 2]

    var_csv = pd.DataFrame({
        "component": [f"PC{i+1}" for i in range(len(pca.explained_variance_ratio_))],
        "explained_variance_ratio": pca.explained_variance_ratio_,
        "cumulative": np.cumsum(pca.explained_variance_ratio_),
    })
    var_csv.to_csv(OUT_DIR / "pca_explained_variance.csv", index=False)

    loadings = pd.DataFrame(
        pca.components_[:3].T,
        columns=["PC1", "PC2", "PC3"],
        index=feat_cols,
    )
    print("\n  PCA Loadings:")
    print(loadings.to_string())

    # ── Step 4: Visualization ─────────────────────────────────────────
    print("\n[4/7] Generating PCA scatter plot...")

    bbb_mask = desc_valid["group"] == "BBB"
    ns3_mask = desc_valid["group"] == "NS2B-NS3 protease"
    ns5_mask = desc_valid["group"] == "NS5 RdRp"

    fig, ax = plt.subplots(figsize=(10, 8))

    ax.scatter(
        desc_valid.loc[bbb_mask, "PC1"],
        desc_valid.loc[bbb_mask, "PC2"],
        c="#888888", alpha=0.35, s=20, label=f"BBB Magnolia (n={bbb_mask.sum()})",
        edgecolors="none", zorder=2,
    )
    ax.scatter(
        desc_valid.loc[ns3_mask, "PC1"],
        desc_valid.loc[ns3_mask, "PC2"],
        c="#2196F3", alpha=0.85, s=70, label=f"NS2B-NS3 actives (n={ns3_mask.sum()})",
        edgecolors="white", linewidths=0.5, zorder=3, marker="D",
    )
    ax.scatter(
        desc_valid.loc[ns5_mask, "PC1"],
        desc_valid.loc[ns5_mask, "PC2"],
        c="#E53935", alpha=0.85, s=70, label=f"NS5 RdRp actives (n={ns5_mask.sum()})",
        edgecolors="white", linewidths=0.5, zorder=3, marker="s",
    )

    # 95% confidence ellipses
    from matplotlib.patches import Ellipse
    for mask, color, label_tag in [
        (ns3_mask, "#2196F3", "NS3"),
        (ns5_mask, "#E53935", "NS5"),
        (bbb_mask, "#888888", "BBB"),
    ]:
        subset = desc_valid.loc[mask, ["PC1", "PC2"]].values
        if len(subset) < 3:
            continue
        cov = np.cov(subset.T)
        eigenvalues, eigenvectors = np.linalg.eigh(cov)
        order = eigenvalues.argsort()[::-1]
        eigenvalues = eigenvalues[order]
        eigenvectors = eigenvectors[:, order]
        angle = np.degrees(np.arctan2(eigenvectors[1, 0], eigenvectors[0, 0]))
        width, height = 2 * np.sqrt(eigenvalues * 5.991)  # chi2 95% for 2 dof
        ellipse = Ellipse(
            xy=(subset[:, 0].mean(), subset[:, 1].mean()),
            width=width, height=height, angle=angle,
            facecolor=color, alpha=0.08, edgecolor=color,
            linewidth=1.5, linestyle="--", zorder=1,
        )
        ax.add_patch(ellipse)

    ev1 = pca.explained_variance_ratio_[0] * 100
    ev2 = pca.explained_variance_ratio_[1] * 100
    ax.set_xlabel(f"PC1 ({ev1:.1f}% variance)", fontsize=12)
    ax.set_ylabel(f"PC2 ({ev2:.1f}% variance)", fontsize=12)
    ax.set_title("Chemical Space: BBB Magnolia Compounds vs Known DENV Inhibitors", fontsize=13)
    ax.legend(loc="upper right", fontsize=10, framealpha=0.9)
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "pca_chemical_space.png", dpi=300, bbox_inches="tight")
    fig.savefig(FIG_DIR / "pca_chemical_space.svg", bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {FIG_DIR / 'pca_chemical_space.png'}")

    # ── Loadings biplot ───────────────────────────────────────────────
    print("[4b/7] Generating loadings biplot...")
    fig2, ax2 = plt.subplots(figsize=(8, 8))

    ax2.scatter(
        desc_valid.loc[bbb_mask, "PC1"],
        desc_valid.loc[bbb_mask, "PC2"],
        c="#CCCCCC", alpha=0.2, s=10, zorder=1,
    )
    ax2.scatter(
        desc_valid.loc[ns3_mask, "PC1"],
        desc_valid.loc[ns3_mask, "PC2"],
        c="#2196F3", alpha=0.5, s=30, zorder=2, marker="D",
    )
    ax2.scatter(
        desc_valid.loc[ns5_mask, "PC1"],
        desc_valid.loc[ns5_mask, "PC2"],
        c="#E53935", alpha=0.5, s=30, zorder=2, marker="s",
    )

    scale_factor = max(abs(desc_valid["PC1"]).max(), abs(desc_valid["PC2"]).max()) * 0.8
    for i, feat in enumerate(feat_cols):
        ax2.annotate(
            feat,
            xy=(loadings.iloc[i, 0] * scale_factor, loadings.iloc[i, 1] * scale_factor),
            fontsize=9, fontweight="bold", color="#333333",
            ha="center", va="center",
            arrowprops=dict(arrowstyle="->", color="#333333", lw=1.5),
            xytext=(0, 0),
        )

    ax2.set_xlabel(f"PC1 ({ev1:.1f}%)", fontsize=12)
    ax2.set_ylabel(f"PC2 ({ev2:.1f}%)", fontsize=12)
    ax2.set_title("PCA Loadings Biplot", fontsize=13)
    ax2.grid(True, alpha=0.2)
    fig2.tight_layout()
    fig2.savefig(FIG_DIR / "pca_loadings_biplot.png", dpi=300, bbox_inches="tight")
    plt.close(fig2)
    print(f"  Saved: {FIG_DIR / 'pca_loadings_biplot.png'}")

    # ── Descriptor distributions ──────────────────────────────────────
    print("[4c/7] Generating descriptor distribution plots...")
    fig3, axes = plt.subplots(2, 5, figsize=(20, 8))
    axes = axes.ravel()
    palette = {"BBB": "#888888", "NS2B-NS3 protease": "#2196F3", "NS5 RdRp": "#E53935"}

    for i, feat in enumerate(feat_cols):
        sns.boxplot(
            data=desc_valid, x="group", y=feat, ax=axes[i],
            palette=palette, order=["BBB", "NS2B-NS3 protease", "NS5 RdRp"],
            fliersize=2,
        )
        axes[i].set_title(feat, fontsize=11, fontweight="bold")
        axes[i].set_xlabel("")
        axes[i].tick_params(axis="x", rotation=30, labelsize=8)

    fig3.suptitle("Descriptor Distributions by Compound Group", fontsize=14, y=1.01)
    fig3.tight_layout()
    fig3.savefig(FIG_DIR / "descriptor_distributions.png", dpi=300, bbox_inches="tight")
    plt.close(fig3)
    print(f"  Saved: {FIG_DIR / 'descriptor_distributions.png'}")

    # ── Step 5: Nearest-neighbor ranking in PCA space ─────────────────
    print("\n[5/7] Computing nearest-neighbor rankings in PCA space...")

    bbb_pca = desc_valid.loc[bbb_mask, ["PC1", "PC2", "PC3"]].values
    ns3_pca = desc_valid.loc[ns3_mask, ["PC1", "PC2", "PC3"]].values
    ns5_pca = desc_valid.loc[ns5_mask, ["PC1", "PC2", "PC3"]].values

    ns3_ids = ns3["chembl_id"].tolist()
    ns5_ids = ns5["chembl_id"].tolist()
    ns3_ic50 = ns3["ic50_uM"].tolist()
    ns5_ic50 = ns5["ic50_uM"].tolist()

    bbb_valid = desc_valid.loc[bbb_mask].reset_index(drop=True)

    nn_records = []
    for i in range(len(bbb_pca)):
        d_ns3 = np.linalg.norm(bbb_pca[i] - ns3_pca, axis=1)
        d_ns5 = np.linalg.norm(bbb_pca[i] - ns5_pca, axis=1)
        j3 = int(np.argmin(d_ns3))
        j5 = int(np.argmin(d_ns5))

        nn_records.append({
            "nearest_ns3_distance": round(d_ns3[j3], 4),
            "nearest_ns3_chembl_id": ns3_ids[j3],
            "nearest_ns3_ic50_uM": ns3_ic50[j3],
            "nearest_ns5_distance": round(d_ns5[j5], 4),
            "nearest_ns5_chembl_id": ns5_ids[j5],
            "nearest_ns5_ic50_uM": ns5_ic50[j5],
        })

    nn_df = pd.DataFrame(nn_records)
    nn_df["closest_target"] = np.where(
        nn_df["nearest_ns3_distance"] < nn_df["nearest_ns5_distance"],
        "NS2B-NS3", "NS5 RdRp",
    )

    # ── Step 6: ECFP4 Tanimoto ────────────────────────────────────────
    print("[6/7] Computing ECFP4 Tanimoto similarities...")

    bbb_fps = compute_ecfp4(bbb_valid["smiles"].tolist())
    ns3_fps = compute_ecfp4(ns3_smiles)
    ns5_fps = compute_ecfp4(ns5_smiles)

    tani_ns3 = []
    tani_ns5 = []
    for fp in bbb_fps:
        sim3, idx3 = max_tanimoto(fp, ns3_fps)
        sim5, idx5 = max_tanimoto(fp, ns5_fps)
        tani_ns3.append({
            "max_tanimoto_ns3": round(sim3, 4),
            "most_similar_ns3_chembl_id": ns3_ids[idx3] if idx3 >= 0 else "",
        })
        tani_ns5.append({
            "max_tanimoto_ns5": round(sim5, 4),
            "most_similar_ns5_chembl_id": ns5_ids[idx5] if idx5 >= 0 else "",
        })

    tani_df = pd.DataFrame(tani_ns3)
    tani_df["max_tanimoto_ns5"] = [r["max_tanimoto_ns5"] for r in tani_ns5]
    tani_df["most_similar_ns5_chembl_id"] = [r["most_similar_ns5_chembl_id"] for r in tani_ns5]

    # ── Assemble output ───────────────────────────────────────────────
    out = pd.DataFrame({
        "inchikey": bbb_valid["smiles"].map(
            dict(zip(bbb["canonical_smiles"], bbb["inchikey"]))
        ),
        "common_names": bbb_valid["smiles"].map(
            dict(zip(bbb["canonical_smiles"], bbb["common_names"]))
        ),
        "canonical_smiles": bbb_valid["smiles"].values,
        "molecular_weight": bbb_valid["MW"].values,
        "LogP": bbb_valid["LogP"].values,
    })

    out = pd.concat([out.reset_index(drop=True), nn_df, tani_df.reset_index(drop=True)], axis=1)
    out["ns3_rank"] = out["nearest_ns3_distance"].rank().astype(int)
    out["ns5_rank"] = out["nearest_ns5_distance"].rank().astype(int)

    out.to_csv(OUT_DIR / "pca_similarity_rankings.csv", index=False)
    print(f"\n  Saved rankings: {OUT_DIR / 'pca_similarity_rankings.csv'}")

    # ── Step 7: Summary tables ────────────────────────────────────────
    print("\n[7/7] Summary tables")

    display_cols = [
        "common_names", "molecular_weight", "LogP",
        "nearest_ns3_distance", "nearest_ns3_chembl_id", "nearest_ns3_ic50_uM",
        "max_tanimoto_ns3",
    ]
    display_cols_ns5 = [
        "common_names", "molecular_weight", "LogP",
        "nearest_ns5_distance", "nearest_ns5_chembl_id", "nearest_ns5_ic50_uM",
        "max_tanimoto_ns5",
    ]

    print("\n" + "=" * 90)
    print("  TOP 20 BBB COMPOUNDS CLOSEST TO NS2B-NS3 PROTEASE INHIBITORS (PCA distance)")
    print("=" * 90)
    top_ns3 = out.nsmallest(20, "nearest_ns3_distance")[display_cols]
    print(top_ns3.to_string(index=False))

    print("\n" + "=" * 90)
    print("  TOP 20 BBB COMPOUNDS CLOSEST TO NS5 RdRp INHIBITORS (PCA distance)")
    print("=" * 90)
    top_ns5 = out.nsmallest(20, "nearest_ns5_distance")[display_cols_ns5]
    print(top_ns5.to_string(index=False))

    print("\n" + "=" * 90)
    print("  TOP 20 BBB COMPOUNDS BY ECFP4 TANIMOTO TO NS3 ACTIVES")
    print("=" * 90)
    top_tc_ns3 = out.nlargest(20, "max_tanimoto_ns3")[
        ["common_names", "molecular_weight", "max_tanimoto_ns3", "most_similar_ns3_chembl_id"]
    ]
    print(top_tc_ns3.to_string(index=False))

    print("\n" + "=" * 90)
    print("  TOP 20 BBB COMPOUNDS BY ECFP4 TANIMOTO TO NS5 ACTIVES")
    print("=" * 90)
    top_tc_ns5 = out.nlargest(20, "max_tanimoto_ns5")[
        ["common_names", "molecular_weight", "max_tanimoto_ns5", "most_similar_ns5_chembl_id"]
    ]
    print(top_tc_ns5.to_string(index=False))

    # ── Summary statistics ────────────────────────────────────────────
    n_closer_ns3 = (out["closest_target"] == "NS2B-NS3").sum()
    n_closer_ns5 = (out["closest_target"] == "NS5 RdRp").sum()
    print(f"\n{'=' * 90}")
    print(f"  SUMMARY")
    print(f"{'=' * 90}")
    print(f"  BBB compounds closer to NS3 actives: {n_closer_ns3} ({n_closer_ns3/len(out)*100:.1f}%)")
    print(f"  BBB compounds closer to NS5 actives: {n_closer_ns5} ({n_closer_ns5/len(out)*100:.1f}%)")
    print(f"  Mean Tanimoto to NS3: {out['max_tanimoto_ns3'].mean():.3f}")
    print(f"  Mean Tanimoto to NS5: {out['max_tanimoto_ns5'].mean():.3f}")
    print(f"  Max Tanimoto to NS3: {out['max_tanimoto_ns3'].max():.3f}")
    print(f"  Max Tanimoto to NS5: {out['max_tanimoto_ns5'].max():.3f}")
    print(f"\n  Total valid BBB compounds analyzed: {len(out)}")
    print(f"  Artifacts saved to: {OUT_DIR}")
    print("  Done.")


if __name__ == "__main__":
    main()
