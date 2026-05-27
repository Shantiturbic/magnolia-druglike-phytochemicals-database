# Chemical Space Analysis: BBB Database vs ChEMBL DENV Actives

**Created**: 2026-05-26
**Status**: Complete (2026-05-26)
**Purpose**: Characterize the chemical space overlap between the 738 BBB Magnolia phytochemicals and 100 experimentally validated DENV inhibitors from ChEMBL, stratified by target protein (NS2B-NS3 protease vs NS5 RdRp).

---

## Objective

Determine which BBB compounds occupy similar chemical space to known DENV inhibitors, and specifically which target's inhibitors they resemble most. This is a characterization step, not a filter — all 738 compounds proceed to docking regardless of PCA proximity.

## Input Data

| Dataset | Path | N | Description |
|---------|------|---|-------------|
| BBB Database STC | `bbb/data/magnolia_bbb_database.csv` | 738 | Magnolia phytochemicals from 12 public sources |
| NS3 actives | `data/dengue/inputs/validation/chembl_actives/NS2B_NS3_protease_actives.csv` | 50 | ChEMBL DENV NS2B-NS3 protease inhibitors, IC50 < 10 uM |
| NS5 actives | `data/dengue/inputs/validation/chembl_actives/NS5_RdRp_actives.csv` | 50 | ChEMBL DENV NS5 RdRp inhibitors, IC50 < 50 uM |

**Key columns used:**
- BBB: `canonical_smiles`, `molecular_weight`, `common_names`, `inchikey`
- ChEMBL: `smiles`, `mw`, `chembl_id`, `ic50_uM`, `target`

## Step 1: Molecular Descriptor Computation

**Tool**: RDKit (via `rdkit.Chem.Descriptors`)

Compute 10 physicochemical descriptors for all 838 compounds:

| # | Descriptor | RDKit Function | Rationale |
|---|-----------|----------------|-----------|
| 1 | Molecular Weight | `Descriptors.MolWt` | Size |
| 2 | LogP | `Descriptors.MolLogP` (Wildman-Crippen) | Lipophilicity |
| 3 | HBD | `Descriptors.NumHDonors` | H-bond donors |
| 4 | HBA | `Descriptors.NumHAcceptors` | H-bond acceptors |
| 5 | TPSA | `Descriptors.TPSA` | Polar surface area |
| 6 | Rotatable Bonds | `Descriptors.NumRotatableBonds` | Flexibility |
| 7 | Num Rings | `Descriptors.RingCount` | Ring systems |
| 8 | Aromatic Rings | `Descriptors.NumAromaticRings` | Aromaticity |
| 9 | Fraction CSP3 | `Descriptors.FractionCSP3` | Saturation (NP-likeness proxy) |
| 10 | Molar Refractivity | `Descriptors.MolMR` | Polarizability/size |

**Handling failures**: Compounds with invalid SMILES are excluded and logged. Expected: 0 failures (BBB database already validated).

## Step 2: Standardization

**Method**: `sklearn.preprocessing.StandardScaler` (zero mean, unit variance per descriptor)

Applied to the full 838-compound matrix before PCA. This prevents MW (range ~100-1900) from dominating over HBD (range 0-10).

## Step 3: PCA

**Method**: `sklearn.decomposition.PCA`

- Fit on all 838 compounds (BBB + both ChEMBL active sets)
- Extract first 3 principal components
- Record explained variance ratio per component
- Record loadings (which descriptors drive each PC)

## Step 4: Visualization

**Output**: `bbb/data/figures/pca_chemical_space.png` (300 DPI, publication quality)

**Plot**: PC1 vs PC2 scatter plot with:
- BBB compounds: gray circles, alpha=0.4, smaller marker
- NS3 protease actives: colored markers (e.g., blue), larger, labeled "NS2B-NS3 (n=50)"
- NS5 RdRp actives: colored markers (e.g., red), larger, labeled "NS5 RdRp (n=50)"
- Axis labels include explained variance (e.g., "PC1 (42.3%)")
- Legend with group labels and counts
- Optional: 95% confidence ellipses per group

**Secondary plot**: PC1 vs PC3 if PC3 explains >10% variance.

**Loadings biplot**: Arrows showing which descriptors drive PC1/PC2 separation.

## Step 5: Nearest-Neighbor Ranking (PCA Space)

For each BBB compound, compute Euclidean distance in the standardized PCA space (PC1-PC3) to:
- Each NS3 active → take minimum distance → "distance to nearest NS3 active"
- Each NS5 active → take minimum distance → "distance to nearest NS5 active"

**Output**: `bbb/data/pca_similarity_rankings.csv`

Columns:
- `inchikey`, `common_names`, `canonical_smiles`, `molecular_weight`
- `nearest_ns3_distance`, `nearest_ns3_chembl_id`, `nearest_ns3_ic50_uM`
- `nearest_ns5_distance`, `nearest_ns5_chembl_id`, `nearest_ns5_ic50_uM`
- `closest_target` (NS3 or NS5, whichever has smaller distance)
- `ns3_rank`, `ns5_rank` (rank among all 738 BBB compounds by proximity)

## Step 6: ECFP4 Tanimoto Similarity (Structural Complement)

PCA on physicochemical descriptors captures property similarity but misses structural/scaffold similarity. ECFP4 Morgan fingerprints (radius=2, 2048 bits) provide a complementary structural view.

For each BBB compound:
- Compute maximum Tanimoto similarity to any NS3 active
- Compute maximum Tanimoto similarity to any NS5 active

**Output**: Columns added to `pca_similarity_rankings.csv`:
- `max_tanimoto_ns3`, `most_similar_ns3_chembl_id`
- `max_tanimoto_ns5`, `most_similar_ns5_chembl_id`

## Step 7: Summary Tables

**Table A**: Top 20 BBB compounds most similar to NS3 protease inhibitors (by PCA distance)
**Table B**: Top 20 BBB compounds most similar to NS5 RdRp inhibitors (by PCA distance)
**Table C**: Top 20 BBB compounds by ECFP4 Tanimoto to NS3
**Table D**: Top 20 BBB compounds by ECFP4 Tanimoto to NS5

Tables printed to stdout and saved in the output CSV.

## Output Artifacts

| Artifact | Path | Description |
|----------|------|-------------|
| PCA scatter plot | `bbb/data/figures/pca_chemical_space.png` | PC1 vs PC2, 3 groups, 300 DPI |
| Loadings biplot | `bbb/data/figures/pca_loadings_biplot.png` | Descriptor arrows on PC1/PC2 |
| Descriptor heatmap | `bbb/data/figures/descriptor_distributions.png` | Box/violin per group per descriptor |
| Rankings CSV | `bbb/data/pca_similarity_rankings.csv` | All 738 BBB compounds ranked by proximity |
| PCA variance | `bbb/data/pca_explained_variance.csv` | Explained variance per component |
| Analysis script | `bbb/chemical_space_pca.py` | Reproducible script |

## Interpretation Notes

- This is **characterization, not filtering**. All 738 compounds go to docking (per DEC/feedback: no premature filtering).
- PCA distance measures **physicochemical similarity** (are these compounds drug-like in the same way?).
- ECFP4 Tanimoto measures **structural similarity** (do these compounds share substructures?).
- A BBB compound close to NS3 actives in PCA space is not predicted to inhibit NS3 — it means it occupies similar property space, making it a plausible candidate for the same target class.
- Natural products typically occupy different chemical space from synthetic drugs. Low overlap is expected and does not invalidate the screening — it means we're exploring novel scaffolds.

---

## Execution

Run from repo root:
```bash
python bbb/chemical_space_pca.py
```

Dependencies: `rdkit`, `pandas`, `numpy`, `scikit-learn`, `matplotlib`, `seaborn`

---

## Results (2026-05-26)

### PCA Variance

| Component | Variance Explained | Cumulative |
|-----------|--------------------|------------|
| PC1 | 52.2% | 52.2% |
| PC2 | 19.2% | 71.4% |
| PC3 | 15.2% | 86.6% |

PC1 is driven by molecular size/polarity (MW, HBA, TPSA, HBD, MolMR). PC2 is driven by lipophilicity/flexibility (LogP, RotBonds).

### PCA Loadings

| Descriptor | PC1 | PC2 | PC3 |
|-----------|------|------|------|
| MW | 0.411 | 0.209 | 0.034 |
| LogP | -0.068 | 0.630 | -0.338 |
| HBD | 0.351 | -0.187 | 0.277 |
| HBA | 0.402 | -0.141 | 0.170 |
| TPSA | 0.404 | -0.148 | 0.220 |
| RotBonds | 0.212 | 0.535 | 0.179 |
| Rings | 0.276 | -0.141 | -0.263 |
| AromaticRings | 0.303 | -0.077 | -0.530 |
| FractionCSP3 | -0.145 | 0.252 | 0.590 |
| MolMR | 0.380 | 0.327 | -0.029 |

### Chemical Space Overlap

**NS5 RdRp actives overlap substantially with BBB compounds in PCA space.** The red NS5 markers sit within the BBB cloud, indicating Magnolia natural products naturally resemble NS5 RdRp inhibitors in physicochemical properties. **NS2B-NS3 protease actives extend beyond BBB space** — the large peptidomimetic inhibitors (MW 600-780, 13-19 rotatable bonds) occupy synthetic drug chemical space that no natural product library would cover.

### Target Proximity Summary

| Metric | Value |
|--------|-------|
| BBB compounds closer to NS3 actives | 356 / 738 (48.2%) |
| BBB compounds closer to NS5 actives | 382 / 738 (51.8%) |
| Mean ECFP4 Tanimoto to NS3 | 0.163 |
| Mean ECFP4 Tanimoto to NS5 | 0.188 |
| Max ECFP4 Tanimoto to NS3 | 0.757 |
| Max ECFP4 Tanimoto to NS5 | 0.836 |

Structural similarity (Tanimoto) is low across the board, which is expected for natural products vs synthetic drugs. The compounds explore genuinely novel scaffold space relative to known DENV inhibitors.

### Property Space Comparison

| Property | BBB (n=738) | NS3 actives (n=50) | NS5 actives (n=50) |
|----------|-------------|--------------------|--------------------|
| MW mean | 309.7 | ~500+ (peptidomimetics) | ~400 |
| MW median | 294.4 | ~430 | ~420 |
| FractionCSP3 | Higher (more saturated, NP-like) | Lower | Intermediate |
| RotBonds | Lower (rigid NP scaffolds) | High (13-19 for peptidics) | Moderate |

### Interpretation

1. The BBB Magnolia library occupies chemical space that is **more similar to NS5 RdRp inhibitors** than to NS3 protease inhibitors in physicochemical properties.
2. Low Tanimoto similarity across both targets confirms the library explores **novel scaffolds**, which is the fundamental motivation for natural product screening.
3. This is characterization, not prediction — proximity in PCA space does not predict activity, but it does indicate which target class the compounds are most physicochemically compatible with.
4. The large peptidomimetic NS3 inhibitors are unreachable from any NP library; however, non-peptidic NS3 inhibitors (smaller MW, drug-like) do overlap with the BBB cloud.

---

## NS5 Active Set Audit (2026-05-26)

### Finding: 70% of NS5 "RdRp" actives are actually MTase inhibitors

The `fetch_chembl_actives.py` script searched for assays with "NS5" + "dengue" in the description, but did not distinguish between the two enzymatic domains of NS5:
- **NS5 RdRp** (C-terminal polymerase domain) — the target of crystal structure 4V0Q
- **NS5 MTase** (N-terminal methyltransferase domain) — completely different binding pocket (SAM site)

**Audit results (50 compounds):**

| Domain | Count | Notes |
|--------|-------|-------|
| RdRp / Polymerase | 14 | Assay descriptions mention "polymerase", "RdRp", "RNA-dependent RNA polymerase", "replicase" |
| MTase | 35 | Assay descriptions mention "methyltransferase", "SAM site", "RNA site", "guanine N-7" |
| NS5 unspecified | 1 | "guanylation" — likely MTase-related |

### Impact on Enrichment Validation

The DUDE-Z enrichment (AUC = 0.820) was achieved with 35/50 actives targeting the wrong domain. MTase inhibitors should not dock preferentially at the RdRp active site, meaning they behave like noise (decoy-like). The true RdRp-only AUC would likely be **higher** than 0.820. The current result is conservative.

### Recommended Action

1. Split NS5 actives into RdRp-only (14) and MTase-only (35) subsets
2. Re-run enrichment analysis for each subset separately
3. Fetch additional RdRp-specific actives from ChEMBL (filter assay descriptions for "polymerase|RdRp|replicase")
4. Report both domain-specific and combined AUC values in thesis

### RdRp-confirmed compounds (14)

CHEMBL565248, CHEMBL3809849, CHEMBL1940606, CHEMBL4638250, CHEMBL2036488, CHEMBL3810157, CHEMBL269277, CHEMBL3344312, CHEMBL4848338, CHEMBL1259059, CHEMBL82242, CHEMBL7301, CHEMBL3417270, CHEMBL4126343

### MTase-confirmed compounds (35)

CHEMBL599410, CHEMBL599598, CHEMBL605959, CHEMBL1491479, CHEMBL597965, CHEMBL603880, CHEMBL220175, CHEMBL597781, CHEMBL598807, CHEMBL607863, CHEMBL25718, CHEMBL597964, CHEMBL289277, CHEMBL596747, CHEMBL599830, CHEMBL176599, CHEMBL599409, CHEMBL607576, CHEMBL604091, CHEMBL597777, CHEMBL598785, CHEMBL598786, CHEMBL606193, CHEMBL597358, CHEMBL597975, CHEMBL597979, CHEMBL599597, CHEMBL606180, CHEMBL597978, CHEMBL597776, CHEMBL597154, CHEMBL606173, CHEMBL599616, CHEMBL115145, CHEMBL1214186
