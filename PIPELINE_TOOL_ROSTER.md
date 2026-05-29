# Pipeline Tool Roster: What Stays, What Goes, What's New

**Created**: 2026-05-26
**Context**: After enrichment validation (Plan 0/0C) proved Vina scoring is random on property-matched decoys (ultra-matched AUC=0.47), the pipeline needs multi-scorer rescoring. This document defines exactly which tools are in, out, and new.

---

## STAYS (already deployed and working)

| Tool | Role | What it does | Why it stays |
|------|------|-------------|--------------|
| **Uni-Dock** | Pose generator | GPU-accelerated Vina docking. Generates 3D binding poses + Vina scores. 1600x faster than CPU Vina. | Poses are good. Scoring is bad. We keep the poses, discard the ranking. |
| **Uni-Mol Docking V2** | Better pose generator | AI pose prediction, 77.6% RMSD <2A vs Vina's 52.3%. | Generates geometrically superior poses for top candidates. No scoring capability — never had it. |
| **Uni-GBSA** | Physics energy | MM-GBSA binding free energy (actual kcal/mol). Minimization-only for screening, short MD for top candidates. | Only tool that gives real thermodynamic energies. Used on top 50-100 per target. Already set up. |

## GOES (role changes or deprecated)

| Tool | Old role | What happens | Why |
|------|----------|-------------|-----|
| **Vina scoring** (via Uni-Dock) | Primary ranking | Demoted to pose generation metric only. Scores kept for reference, never used for final ranking. | Ultra-matched AUC = 0.47. Random. Captures properties, not binding. (DEC-035) |
| **RRF consensus** | Score fusion | Replaced by ECR. | "Noisy and mostly random numbers for larger datasets" — Houston & Walkinshaw 2019. (DEC-041) |
| **dist_to_site** (Uni-Mol V2) | Scoring metric | Deleted entirely. | Geometric distance to pocket center. Not binding affinity. AUC = 0.378. (DEC-009) |

## NEW (to be deployed)

### 1. GNINA — Primary Rescorer

- **What**: CNN-augmented molecular docking from Koes lab (U. Pittsburgh). Ensemble of 3D CNNs trained on CrossDocked2020 (22,584 crystal structures). Outputs CNNscore (pose quality, 0-1), CNNaffinity (predicted pKd), and CNN_VS (product — best for VS ranking).
- **Integration**: `gnina -r receptor.pdb -l unidock_poses.sdf --autobox_ligand ref.pdb --score_only`. Rescores existing Uni-Dock poses. CPU-only. ~1.5 sec/compound.
- **Evidence**: Won CACHE Challenge #1 prospectively (7M screened, Kd=56uM hit). Published for DENV NS2B-NS3 (JPCB 2024). DUD-E median AUC 0.795 vs Vina 0.745. LIT-PCBA EF1% 2.58 vs Vina 1.10. Independent 2025 benchmark: outperformed Vina in 8/10 targets, 25/30 EF comparisons.
- **License**: Apache 2.0
- **Research file**: `docs/architecture/research-findings/04-gnina.md`

### 2. SCORCH2 — Second Rescorer

- **What**: XGBoost-based consensus rescoring (Advanced Science 2025, IF ~15). Two models (SC2-PB on PDBbind, SC2-PS on PDBScreen) combined. Uses 492 BINANA/ECIF/Kier features + 59 RDKit descriptors.
- **Integration**: Convert SDF to PDBQT. Feature extraction ~100-180/sec (CPU). Inference: 53K complexes in 0.29 sec.
- **Evidence**: DEKOIS 2.0 unseen targets EF0.5%=18.94, EF1%=18.14. Highest enrichment at all EF levels. DUD-E unseen targets EF0.5%=13.71.
- **Limitation**: Discriminates active/decoy, NOT binding affinity (Spearman Rs = 0.377).
- **License**: Not specified (GitHub: LinCompbio/SCORCH2)
- **Research file**: `docs/architecture/research-findings/05-scorch2-luna-pharmaconet.md`

### 3. ECR — Score Fusion

- **What**: Exponential Consensus Ranking. P(i) = (1/sigma) * sum_j exp(-r_ij / sigma). Rewards compounds ranking well in even one scorer.
- **Integration**: ~50 lines Python. Implementation: dockECR (GitHub: rochoa85/dockECR).
- **Evidence**: Houston & Walkinshaw 2019: ECR earned 23 points vs Z-score 16, RbN 12, RbV 4, RbR 2. RRF excluded as "noisy random numbers."
- **Research file**: `docs/architecture/research-findings/09-consensus-scoring-rrf-ifp-cascade.md`

### 4. ProLIF — Structural Filter

- **What**: Interaction fingerprints — encodes which protein residues each pose contacts (H-bonds, hydrophobic, pi-stacking, salt bridges). Compares docked poses against crystal structure reference contacts.
- **Integration**: `pip install prolif`. CPU-only, seconds per compound.
- **Evidence**: IFP scoring "outperformed conventional scoring functions" for native-like pose identification.
- **License**: Apache 2.0
- **Research file**: `docs/architecture/research-findings/09-consensus-scoring-rrf-ifp-cascade.md`

### 5. Protenix — Structure Prediction

- **What**: Open-source AlphaFold 3 reimplementation (ByteDance). For NS4B (no crystal structure available).
- **Integration**: `pip install protenix`. RunPod A100/H100. ~20 min per prediction.
- **Evidence**: PoseBusters ~77% RMSD <2A (matches AF3). First open model to outperform AF3 across diverse benchmarks.
- **License**: Apache 2.0
- **Research file**: `docs/architecture/research-findings/07-af3-protenix-mmgbsa.md`

### 6. Boltz-2 — Co-Folding + Affinity (optional)

- **What**: AlphaFold3-class diffusion + PairFormer affinity head. Predicts protein-ligand complex AND binding affinity (unique among co-folding tools). For induced-fit analysis and optional enrichment.
- **Integration**: `pip install boltz[cuda]`. RunPod A100 (48GB+). ~20 sec/compound.
- **Evidence**: MF-PCBA AUROC ~0.81, EF@0.5%=18.4. FEP+ Pearson r=0.62. Won CASP16. BUT: independent evaluations show no correlation in top-100 (arXiv 2603.05532).
- **License**: MIT
- **Research file**: `docs/architecture/research-findings/01-boltz2.md`

---

## Pipeline Flow

```
738 MAGNOLIA COMPOUNDS x 8 DENV TARGETS
                |
     Stage 1: UNI-DOCK (pose generation, GPU, minutes)
     Output: SDF files with 3D poses. Vina scores = reference only.
                |
     Stage 2: GNINA --score_only (CNN rescoring, CPU, ~4 hrs total)
     Output: CNN_VS score per pose.
                |
     Stage 3: SCORCH2 (XGBoost rescoring, CPU, seconds)
     Output: SCORCH2 probability score per pose.
                |
     Stage 4: ECR FUSION (Vina + CNN_VS + SCORCH2)
     Output: single consensus rank per compound per target. Top 100-200 pass.
                |
     Stage 5: ProLIF IFP FILTER (CPU, seconds)
     "Does this pose touch catalytic residues?" Removes wrong-site binders.
                |
     Stage 6: UNI-GBSA (MM-GBSA, minutes/compound)
     Top 50-100 per target. Actual dG kcal/mol + per-residue decomposition.
                |
     Stage 7: BOLTZ-2 (optional, top 20-50)
     Additional affinity signal, not primary ranking.
                |
     FINAL: Top 20-50 per target -> Thesis Chapter 4
```

**Three orthogonal scoring paradigms in consensus:**
1. Empirical (Vina) — handwritten physics formula
2. CNN-learned (GNINA) — 3D convolutional neural network
3. Feature-engineered ML (SCORCH2) — XGBoost on structural interaction descriptors

---

## Validation Strategy

Each new scorer must demonstrate AUC > 0.50 on ultra-matched decoys to prove it adds binding-specific discrimination beyond molecular properties (DEC-035 threshold).

## Cost Estimate

| Component | Compute | Cost |
|-----------|---------|------|
| Uni-Dock (all compounds, all targets) | <1 GPU-hour | $0.80 |
| GNINA rescoring (all targets) | ~24 CPU-hours | $5-10 |
| SCORCH2 rescoring | <1 GPU-hour | $0.80 |
| MM-GBSA (top 100/target x 8) | ~20 GPU-hours | $20 |
| Boltz-2 (top 200 x 8, optional) | ~9 GPU-hours | $9 |
| Protenix NS4B | ~2 GPU-hours | $2 |
| **Total** | **~57 GPU-hours** | **~$40-50** |



## Pipeline Flow

```
738 MAGNOLIA COMPOUNDS x 8 DENV TARGETS
                |
     Stage 1: UNI-DOCK (pose generation, GPU, minutes)
     Output: SDF files with 3D poses. Vina scores = reference only.
                |
     Stage 2: GNINA --score_only (CNN rescoring, CPU, ~4 hrs total)
     Output: CNN_VS score per pose.
                |
     Stage 3: SCORCH2 (XGBoost rescoring, CPU, seconds)
     Output: SCORCH2 probability score per pose.
                |
     Stage 4: ECR FUSION (Vina + CNN_VS + SCORCH2)
     Output: single consensus rank per compound per target. Top 100-200 pass.
                |
     Stage 5: ProLIF IFP FILTER (CPU, seconds)
     "Does this pose touch catalytic residues?" Removes wrong-site binders.
                |
     Stage 6: UNI-GBSA (MM-GBSA, minutes/compound)
     Top 50-100 per target. Actual dG kcal/mol + per-residue decomposition.
                |
     FINAL: Top 20-50 per target -> Thesis Chapter 4
```
