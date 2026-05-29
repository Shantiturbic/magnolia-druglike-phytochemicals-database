# BBB v2.1 — Robustness & Representativeness Assessment

**Date:** 2026-05-29
**Database version:** v2.1 (1,997 compounds, 11 sources, 79 species QIDs)
**Purpose:** Evaluate BBB fitness for the thesis claim: identifying Magnolia DR phytochemicals with anti-DENV potential in silico.

---

## Database Profile

| Metric | Value |
|--------|-------|
| Unique compounds | 1,997 |
| Species with compound data | 134 of 372 POWO-accepted (36%) |
| Sources queried | 11 (COCONUT, NPASS, LOTUS/Wikidata, KNApSAcK, ChEMBL, PubChem, NPAtlas, PubMed NER, PMC fulltext, Semantic Scholar NER, Literature_Curated) |
| Evidence tier: gold | 1,886 (94.4%) |
| Confirmed by 2+ sources | 1,900 (95.1%) |
| Provenance records | 14,844 |
| Taxonomic scope | Genus Magnolia s.l. (sensu Figlar & Nooteboom 2004) |
| Subgenera represented | Magnolia, Yulania, Talauma, Gynopodium, Michelia |
| Infrageneric additions (v2.1) | Subsect. Dugandiodendron (14 spp.), subsect. Cubenses (9 spp.) |

## Defensible Claims

1. **"Largest systematic phytochemical database for genus Magnolia."** No published equivalent exists at this scale. 1,997 compounds from 11 sources, standardized by RDKit canonicalization, deduplicated by InChIKey connectivity layer.

2. **"Genus-wide screening of Magnolia chemical diversity against DENV targets."** The compounds represent the known chemical space of the genus across all subgenera.

3. **"Chemotaxonomic rationale supports extrapolation to understudied Caribbean species."** Shared compounds between D. argyrotrichum (subsect. Dugandiodendron, Colombia) and T. ovata (sect. Talauma, Brazil) demonstrate phytochemical coherence within subg. Talauma. Parthenolide, dihydroguaiaretic acid, and austrobailignan-6 are shared across continental boundaries. Aporphine alkaloids are the family signature (N-acetylanonaine in D. argyrotrichum; dicentrine/nordicentrine/arcabucoine in T. arcabucoana).

## Identified Gaps

### Gap 1: Zero compounds from DR target species (CRITICAL)

M. pallescens, M. domingensis, M. hamorii, M. emarginata, M. ekmanii — all zero directly attributed compounds. The thesis screens genus-wide compounds but the target species have never been phytochemically investigated. The entire approach rests on chemotaxonomic inference: that Caribbean Magnolia spp. produce metabolites consistent with the genus profile (neolignans, aporphine alkaloids, sesquiterpene lactones).

**Mitigation:** This is inherent to the "in silico first" design. The thesis explicitly positions itself as generating hypotheses for future wet-lab validation.

**Recommendation:** Pilot phytochemical extraction of M. pallescens (most accessible DR species) as the single highest-impact next step.

### Gap 2: Extreme geographic/taxonomic sampling bias

| Region | Compound-species pairs | % of total |
|--------|----------------------|------------|
| East Asian / TCM | ~1,683 | 52.5% |
| North American | ~281 | 8.8% |
| SE Asian (Michelia) | ~400 | 12.5% |
| Neotropical (subg. Talauma) | 117 | 3.7% |
| Other / unresolved | ~723 | 22.5% |

M. officinalis alone contributes 395 compounds (20% of all data). The chemical space going to docking is dominated by honokiol/magnolol/biphenyl neolignan scaffolds from Asian TCM research. This may not reflect the chemodiversity of Caribbean species.

**Mitigation:** The bias reflects the state of the field (2025 Phytochemistry Reviews: "phytochemical investigations of Central and South American Magnolia spp. have yet to be undertaken"). The database captures what exists.

**Recommendation:** Acknowledge explicitly in the thesis. Frame the Neotropical representation as a gap in the literature, not in the database.

### Gap 3: Minimal data for subsect. Dugandiodendron (nearest relatives)

Only 8 compound-species pairs for the DR species' closest continental relatives (~14 Ma divergence). All from one lab (Cuca/Guzman, UNAL Bogota), one species (D. argyrotrichum), published 2005-2010. No follow-up in 15 years.

Key papers:
- Guzman & Cuca 2008, Rev. Col. Quimica 37(3). SciELO: S0120-28042008000300002
- Guzman et al. 2010, J Antimicrob Chemother 65(10):2101-2107. DOI: 10.1093/jac/dkq313
- Puertas, Mesa & Saez 2005, Naturwissenschaften 92(8):381-384. PMID: 16049689
- Corredor-Barinas & Cuca 2011, Nat Prod Res 25(16):1497-1504. DOI: 10.1080/14786410903205146

**Mitigation:** Manual curation (v2.1) added 6 compounds from the Guzman/Cuca papers, including 3-methoxynordomesticine (anti-TB MurE inhibitor, completely absent from all NP databases).

**Recommendation:** Resume phytochemical investigation of D. argyrotrichum and other subsect. Dugandiodendron species. Prioritize antiviral screening of existing isolates.

### Gap 4: Sparse compound class annotations

77% of compounds (1,535/1,997) are unclassified by name-based heuristics. The database lacks systematic NPC/ClassyFire annotations. Without scaffold-level classification, the chemotaxonomic argument cannot be quantified ("X% of Magnolia alkaloids are aporphines").

**Recommendation:** Run NPClassifier or ClassyFire on all 1,997 canonical SMILES. Add pathway, superclass, and class annotations as enrichment columns.

### Gap 5: No bioactivity data integrated

ChEMBL contributes 70 compounds with bioactivity metadata but IC50/EC50/Ki values are not stored in the database. No pre-filtering by antiviral activity, no SAR context for docking hit interpretation.

**Recommendation:** Query ChEMBL and BindingDB for dose-response data on all 1,997 InChIKeys. Prioritize antiviral, anti-DENV, anti-flaviviral, and protease/polymerase inhibition assays. Store as enrichment layer.

### Gap 6: NAPRALERT and SciFinder inaccessible

These are the two databases most likely to contain Dugandiodendron entries from the Colombian literature. Both require institutional access. The manual curation partially compensates.

**Recommendation:** Request institutional NAPRALERT access through INTEC library. Run systematic query for all Magnoliaceae entries.

### Gap 7: No endophyte chemistry

NPAtlas contributed only 3 compounds. Magnolia endophytic fungi and bacteria produce bioactive metabolites that may be misattributed or missed in organism-specific queries.

**Recommendation:** Low priority for thesis scope. Note as future direction for comprehensive Magnolia chemical ecology.

## Summary

The BBB v2.1 is robust for its stated purpose: a systematic, reproducible, genus-wide phytochemical compilation for virtual screening. Its gaps are limitations of the field (no one has studied DR Magnolia chemistry), not of the methodology. Gaps 4 and 5 (compound classification and bioactivity integration) are addressable computationally and would strengthen the analysis. The remaining gaps (1-3, 6-7) are recommendations for future experimental work.
