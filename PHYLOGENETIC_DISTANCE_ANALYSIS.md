# Phylogenetic Distance Analysis: DR Endemic Magnolia vs. Well-Studied Congeners

**Date:** 2026-05-21
**Source data:** Veltjen et al. (2022) Mol Phylogenet Evol 167:107359, Appendix D (gene trees) and Appendix E (pairwise distance matrices)
**Purpose:** Quantify how phylogenetically similar the three Dominican Republic endemic Magnolia species are to the well-studied congeners whose phytochemistry populates the BBB database.

---

## 1. Key Finding

The three DR endemic species (M. pallescens, M. domingensis, M. hamorii) belong to **subsection Cubenses** — a Caribbean-endemic clade within section Talauma. The well-studied phytochemistry species (M. obovata, M. grandiflora, M. biondii, M. kobus, M. virginiana) are in entirely different sections of the genus (Rhytidospermum, Magnolia, Yulania). The genetic divergence between DR endemics and well-studied species ranges from **1.2% to 2.4%** across 11 gene regions, representing an estimated **~54 Mya of divergence** (Nie et al. 2008).

This distance is significant but not prohibitive for chemotaxonomic inference. Genus-level compound classes (lignans, neolignans, aporphine alkaloids, sesquiterpenes) are broadly conserved across Magnolia, though species-specific compound profiles can vary.

---

## 2. Phylogenetic Placement of DR Species

From Appendix D gene trees (Bayesian inference, branch lengths = expected substitutions per site):

### Chloroplast tree (D1: 6 concatenated regions, 8,409 bp)

```
                    ┌── AURICULATA (M. fraseri)
                    ├── MACROPHYLLA (M. dealbata, M. macrophylla)
                    ├── OYAMA (M. sieboldii, M. wilsonii)
                    ├── RHYTIDOSPERMUM (M. tripetala, M. obovata)
                    ├── KMERIA (M. kwangsiensis)
                    ├── GYNOPODIUM (M. nitida, M. kachirachirai)
                    ├── MICHELIA (M. compressa, M. doltsopa, M. figo)
                    ├── TULIPASTRUM (M. acuminata)
                    ├── YULANIA (M. kobus, M. zenii, M. biondii)
              ┌─────├── MANGLIETIA (M. decidua, M. sapaensis, M. insignis)
              │     ├── MAGNOLIA (M. grandiflora, M. virginiana, ...)
              │     ├── GWILLIMIA (M. delavayi, M. sharpii, M. mayae)
     Liriodendron   │
              │     ├── TALAUMA: mainland
              │     │     ├── M. dodecapetala (Lesser Antilles)
              │     │     ├── M. lacandonica, M. sinacacolinii, M. zoquepopolucae
              │     │     ├── M. orbiculata, M. minor, M. oblongifolia (Cuba)
              │     │     │
              │     ├── DUGANDIODENDRON (M. mahechae, M. lenticellata, M. chimantensis)
              │     │
              │     └── CUBENSES (Caribbean clade, pp=0.91)
              │           ├── M. portoricensis, M. splendens (Puerto Rico)
              │           ├── M. hamorii (DR)
              │           ├── M. domingensis (DR + Haiti)  ← target species
              │           ├── M. emarginata (Haiti)
              │           ├── M. pallescens (DR)           ← target species
              │           ├── M. ekmanii (Haiti)
              │           ├── M. cubensis subsp. cubensis (Cuba)
              │           └── M. cristalensis + M. cubensis subsp. acunae (Cuba)
              └─────
```

### Nuclear gene trees (D2-D6)

The topology varies slightly across nuclear genes, but the DR species consistently cluster within Cubenses. Key observations per gene:

| Gene tree | DR species position | Closest non-Caribbean clade | Notes |
|-----------|--------------------|-----------------------------|-------|
| D1 cpDNA | Cubenses (pp=0.91) | Talauma mainland + Dugandiodendron | Deep within section Talauma |
| D2 AGT1 | Cubenses (pp=1.0) | Talauma mainland | Long branch to all other sections |
| D3 GAI1 | Cubenses (pp=1.0) | MAGNOLIA (2): M. virginiana + M. grandiflora | Closest well-studied clade |
| D4 LEAFY | Cubenses | — | Similar to cpDNA topology |
| D5 PHYA | Cubenses | — | Similar to cpDNA topology |
| D6 SQD1 | Cubenses | — | Similar to cpDNA topology |

---

## 3. Pairwise Genetic Distances

### 3.1 Intra-DR distances (the three endemics relative to each other)

| Pair | Avg divergence | Closest gene (%) | Most distant gene (%) |
|------|---------------|-------------------|----------------------|
| M. hamorii ↔ M. pallescens | **0.12%** | LEAFY (0.00%) | AGT1 (0.70%) |
| M. domingensis ↔ M. pallescens | **0.16%** | trnK (0.04%) | AGT1 (0.43%) |
| M. domingensis ↔ M. hamorii | **0.18%** | SQD1 (0.00%) | AGT1 (0.66%) |

The three DR species are **extremely closely related** — 0.12--0.18% average divergence. For context, this is less genetic distance than between many population-level samples of the same species. They should be expected to share essentially the same secondary metabolite profile.

### 3.2 DR vs. other Caribbean species (subsection Cubenses)

| Caribbean species | Avg distance from DR endemics | Relationship |
|-------------------|------------------------------|--------------|
| M. emarginata (Haiti) | **0.16--0.25%** | Closest non-DR relative |
| M. cristalensis (Cuba) | 0.30--0.36% | Close |
| M. cacuminicola (Cuba) | 0.30--0.36% | Close |
| M. splendens (Puerto Rico) | 0.46--0.52% | Moderate |
| M. portoricensis (Puerto Rico) | 0.47--0.51% | Moderate |
| M. ekmanii (Haiti) | 0.49--0.57% | Moderate |
| M. cubensis (Cuba) | 0.50--0.56% | Moderate |
| M. minor (Cuba) | 1.56--1.63% | Distant (different subsection) |
| M. oblongifolia (Cuba) | 1.58--1.66% | Distant (different subsection) |
| M. orbiculata (Cuba) | 1.61--1.67% | Distant (different subsection) |
| M. dodecapetala (Lesser Antilles) | 1.70--1.77% | Distant (sect. Talauma mainland) |

The Cubenses clade splits into two subgroups: the inner Cubenses (0.2--0.6% from DR) and the Talauma mainland species (1.6--1.8% from DR).

### 3.3 DR vs. well-studied phytochemistry species

Ranked by multi-gene consensus (average % divergence across all available gene regions):

| Rank | Well-studied species | Section | Compounds | Avg divergence from DR |
|------|---------------------|---------|-----------|----------------------|
| 1 | **M. virginiana** | Magnolia | ~15--25 (honokiol, magnolol) | **1.24--1.29%** |
| 2 | **M. grandiflora** | Magnolia | ~76+ (sesquiterpenes, alkaloids) | **1.51--1.64%** |
| 3 | **M. acuminata** | Tulipastrum | ~15--20 (lignans) | **1.67--1.80%** |
| 4 | **M. sieboldii** | Oyama | Lignans, alkaloids | **1.73--1.82%** |
| 5 | **M. obovata** | Rhytidospermum | >100 (honokiol, magnolol, obovatol) | **1.79--1.88%** |
| 6 | **M. kobus** | Yulania | ~30--50 (lignans, coumarins) | **1.97--2.27%** |
| 7 | **M. biondii** | Yulania | ~50--70 (volatiles, lignans) | **2.11--2.44%** |

**M. officinalis** (>200 compounds, the most-studied Magnolia) was **not included** in the Veltjen et al. (2022) taxon sampling. Based on its section (Rhytidospermum, same as M. obovata), its distance to DR species would be comparable to M. obovata (~1.8--1.9%).

### 3.4 Per-gene distances: DR endemics vs. M. grandiflora (closest well-studied with rich phytochemistry)

| Gene region | Type | Alignment length | Distance (substitutions) | Divergence (%) |
|-------------|------|------------------|--------------------------|----------------|
| atpB-rbcL | cpDNA spacer | 838 bp | 4--8 | 0.48--0.95% |
| ndhF | cpDNA gene | 2,104 bp | 6--8 | 0.29--0.38% |
| rbcL | cpDNA gene | 1,368 bp | 7--8 | 0.51--0.58% |
| trnK/matK | cpDNA gene | 2,438 bp | 16--17 | 0.66--0.70% |
| ndhF-rpl32 | cpDNA spacer | 1,205 bp | 28--30 | 2.32--2.49% |
| psbA-trnH | cpDNA spacer | 447 bp | 6--8 | 1.34--1.79% |
| AGT1 | Nuclear | 1,213 bp | 72--77 | 5.94--6.35% |
| GAI1 | Nuclear | 1,150 bp | 11--14 | 0.96--1.22% |
| LEAFY | Nuclear | 499 bp | 8--10 | 1.60--2.00% |
| PHYA | Nuclear | 982 bp | 14--17 | 1.43--1.73% |
| SQD1 | Nuclear | 502 bp | 5--6 | 1.00--1.20% |

AGT1 is the fastest-evolving marker (~6% divergence), making it the most informative for recent divergences within the Caribbean clade. The chloroplast genes are more conserved (0.3--0.7% for coding regions).

---

## 4. Distance Scale Summary

```
Divergence          What it means                     Example
─────────────────────────────────────────────────────────────────
0.0--0.2%           Same species / sibling species     DR endemics to each other
0.2--0.6%           Recent radiation, same clade       DR to other Caribbean Magnolia
1.2--1.3%           Same genus, different sections     DR to M. virginiana (closest)
1.5--1.9%           Same genus, more distant sections  DR to M. grandiflora, M. obovata
2.1--2.4%           Same genus, distant sections       DR to M. biondii, M. kobus
~15--20%            Different genera (outgroup)        DR to Liriodendron
```

```
0.0%    0.5%    1.0%    1.5%    2.0%    2.5%    3.0%
  |───────|───────|───────|───────|───────|───────|
  ├─┤ Intra-DR (0.12-0.18%)
  ├───┤ DR ↔ inner Cubenses (0.16-0.57%)
  │      ├──────┤ DR ↔ outer Talauma (1.56-1.77%)
  │         ├─┤ DR ↔ M. virginiana (1.24-1.29%)
  │           ├──┤ DR ↔ M. grandiflora (1.51-1.64%)
  │             ├──┤ DR ↔ M. obovata (1.79-1.88%)
  │                ├──┤ DR ↔ M. biondii (2.11-2.44%)
  │
  Outgroup (Liriodendron): ~15-20%
```

### 4.1 Evolutionary time context

The 1.2--2.4% divergence to well-studied species represents roughly **30--50 million years** of independent evolution (based on Nie et al. 2008 relaxed clock estimates for initial Magnolioideae divergence at ~54 Mya). The DR species are in section Talauma/subsection Cubenses; the well-studied species are in sections Magnolia, Rhytidospermum, Yulania, and Oyama — all separate lineages that diverged deep in the Eocene.

---

## 5. What This Means for Chemistry

### 5.1 How similar are the DR endemics to well-studied Magnolias?

**Moderately similar — same genus, different sections, separated by tens of millions of years.**

The biosynthetic pathways for the major Magnolia compound classes — biphenyl neolignans (magnolol, honokiol), aporphine alkaloids (liriodenine), sesquiterpene lactones — are encoded by gene families that evolve much more slowly than the neutral markers measured in these distance matrices. These compound classes are found across sections Magnolia, Rhytidospermum, Yulania, and Oyama, which all diverged earlier than 50 Mya. The DR species almost certainly produce some version of the core Magnolia chemotype.

But the *specific* compound profile — which lignans, which alkaloids, at what ratios, and whether there are novel compounds — is unknowable from phylogenetics alone. Species in the same section can have very different secondary metabolite profiles depending on ecological pressures, and the Cubenses clade has been evolving on Caribbean islands in isolation.

### 5.2 Confidence tiers for chemotaxonomic transfer

**High confidence (genus-wide conserved):**
- Biphenyl neolignans (magnolol, honokiol) — present in sections Magnolia, Rhytidospermum, and Oyama; the core Magnolia chemotype
- Aporphine alkaloids (liriodenine, anonaine, roemerine) — found across all Magnolia sections studied
- Sesquiterpene lactones (costunolide, parthenolide) — widespread in Magnolioideae

**Medium confidence (section-level patterns):**
- Lignan dimers (magnolin, fargesin, sesamin) — concentrated in sections Yulania and Michelia, less data for Talauma
- Phenylpropanoids (eugenol, cinnamaldehyde derivatives) — common in sect. Michelia, distribution in Talauma unknown

**Low confidence (species-specific):**
- Specific alkaloid profiles, terpenoid ratios, and novel compounds are likely species-specific
- No Talauma/Cubenses species has EVER been phytochemically profiled — we cannot validate section-level predictions

### 5.3 The inverse relationship problem

The closest well-studied species (M. virginiana, 1.2% divergence) has only ~15--25 reported compounds. The richest phytochemistry references (M. obovata with >100, M. officinalis with >200) are more phylogenetically distant (~1.9% estimated). The species we know most about chemically are the ones most distantly related to our targets within the genus.

### 5.4 Bottom line for the BBB database

The BBB database gives a **plausible candidate pool**, not a predicted metabolome. Genus-wide compounds are reasonable to include. Section-specific compounds from Yulania or Michelia (the most distant sections) are speculative transfers. The database IS the contribution — because no phytochemistry exists for Caribbean Magnolia, the BBB database is a novel chemotaxonomic prediction that can be validated by future wet-lab work.

### 5.5 M. officinalis: the missing reference

M. officinalis accounts for >50% of all known Magnolia compounds but was not included in Veltjen et al. (2022). It belongs to section Rhytidospermum (same as M. obovata), so its distance to DR species is estimated at ~1.8--1.9%. Its signature compounds (magnolol, honokiol, 4-O-methylhonokiol, magnaldehyde) are biphenyl neolignans — a compound class found across the genus, supporting their inclusion in the BBB database.

---

## 6. Raw Data

Pairwise distances for all gene regions saved to: `veltjen_pairwise_distances.json`

### Data source
- **Appendix A** (mmc1): Sample information for 62 taxa across 80 populations
- **Appendix B** (mmc2): Primers for 11 markers
- **Appendix C** (mmc3): GenBank accession numbers for all sequences
- **Appendix D** (mmc4): Bayesian gene trees (D1 chloroplast, D2 AGT1, D3 GAI1, D4 LEAFY, D5 PHYA, D6 SQD1)
- **Appendix E** (mmc5): Pairwise distance matrices for all 11 regions + concatenated chloroplast
- **Appendix F** (mmc6): Partition schemes for phylogenetic analysis
- **Appendix G** (mmc7): BioGeoBEARS biogeographic analysis output

### Citation
Veltjen E, Tessnow TN, Palmarola A, Asselman P, Pérez Obregón RA, Chatrou LW, Olmstead RG, Samain M-S. The evolutionary history of the Caribbean magnolias (Magnoliaceae): Testing species delimitations and biogeographical hypotheses using molecular data. *Molecular Phylogenetics and Evolution*. 2022;167:107359. doi:10.1016/j.ympev.2021.107359
