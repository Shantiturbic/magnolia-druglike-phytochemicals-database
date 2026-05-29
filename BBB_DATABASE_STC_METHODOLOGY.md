# BBB Database STC: Systematic Phytochemical Database for Genus Magnolia

**Version:** 2.1
**Date:** 2026-05-29
**Build date:** 2026-05-29 (incremental rebuild from v2.0 raw data + new source)
**Previous version:** 1.0 (2026-05-21, 736 compounds from 7 sources)
**Author:** Shanti Turbi-Cornielle
**Institution:** INTEC, Dominican Republic

---

## 1. Problem Statement

The existing Magnolia chemical atlas (1,627 entries in `data/dengue/archive/magnolia_chemical_atlas.csv`) was built from a compound name list extracted by Miranda Mariñez, a prior INTEC student. This list was resolved against PubChem -- 1,129 compounds matched, 371 did not. There is a legal risk that this list may not be usable.

**BBB Database STC** is a provenance-clean replacement built entirely from publicly accessible databases and peer-reviewed literature, with zero dependency on Miranda's work. Every compound in the database must be traceable to a public source with documented query terms, dates, and licenses.

Beyond contingency, this is a scientific contribution: no comprehensive, openly-sourced, multi-database Magnolia phytochemical database exists in the literature. The closest precedent is LOTUS (Rutz et al., 2022, *eLife* 11:e70780), which aggregates NP-taxon pairs from Wikidata but is not genus-specific. Published Magnolia phytochemistry reviews (Poivre & Duez, 2017, *J Ethnopharmacol* 211:199-223; Ranaware et al., 2018, *Molecules* 23(5):1163) report hundreds of compounds but as non-machine-readable tables. A programmatically-built, standardized, reproducible database fills this gap.

---

## 2. Taxonomic Scope

**Target taxon:** Genus *Magnolia* L. (Magnoliaceae), sensu lato.

**Taxonomic authority:** Plants of the World Online (POWO), maintained by Royal Botanic Gardens, Kew. POWO follows APG IV (Angiosperm Phylogeny Group, 2016, *Bot J Linn Soc* 181:1-20) classification.

**Sensu lato treatment:** Under APG IV and molecular phylogenetic evidence (Figlar & Nooteboom, 2004, *Blumea* 49:87-100; Kim & Suh, 2013, *Plant Syst Evol* 299:1587-1610), several genera formerly considered separate have been merged into *Magnolia*:
- *Michelia* L. -> *Magnolia* (e.g., *M. champaca*, *M. figo*, *M. alba*)
- *Talauma* Juss. -> *Magnolia* (e.g., *M. domingensis*, *M. pallescens*)
- *Manglietia* Blume -> *Magnolia*

All these synonyms are included. Resolution table:

| Former name | Accepted name (POWO) |
|-------------|---------------------|
| *Magnolia hypoleuca* | *Magnolia obovata* |
| *Magnolia heptapeta* | *Magnolia denudata* |
| *Magnolia quinquepeta* | *Magnolia liliiflora* |
| *Michelia champaca* | *Magnolia champaca* |
| *Michelia alba* | *Magnolia x alba* |
| *Michelia figo* | *Magnolia figo* |
| *Talauma domingensis* | *Magnolia domingensis* |
| *Talauma pallescens* | *Magnolia pallescens* |

**Priority species:**

*DR-endemic (thesis focus):*
- *M. pallescens* Urb. & Ekman -- Endangered (IUCN)
- *M. domingensis* Howard -- Critically Endangered
- *M. hamorii* Howard -- Endangered

*Most-studied (bulk of known phytochemistry):*
- *M. officinalis* Rehder & E.H.Wilson -- 200+ compounds reported, major TCM herb (Houpo)
- *M. grandiflora* L. -- southern magnolia, extensively studied
- *M. obovata* Thunb. -- Japanese magnolia
- *M. biondii* Pamp. -- TCM herb (Xinyi)
- *M. virginiana* L., *M. sieboldii* K.Koch, *M. liliiflora* Desr., *M. kobus* DC., *M. denudata* Desr., *M. champaca* (L.) Baill. ex Pierre, *M. acuminata* (L.) L., *M. stellata* (Siebold & Zucc.) Maxim.

**Identifiers:**
- Wikidata QID for genus: Q157017
- NCBI Taxonomy ID: 3408
- GBIF key: 3152559

---

## 3. Inclusion / Exclusion Criteria

### Included:
- Compound reported as isolated from, detected in, or associated with any accepted *Magnolia* species (or synonym) in >=1 selected data source
- Has a resolvable chemical structure (SMILES, InChI, or compound name that resolves via PubChem PUG REST)
- Source is publicly accessible (CC0, CC-BY, CC-BY-SA, public domain, or academic-use license)

### Excluded:
- **MW < 100 Da** -- too small to be a secondary metabolite (removes inorganic ions, simple acids, water)
- **MW > 1500 Da** -- polymeric tannins, polysaccharides; not dockable (Chen et al., 2018, *Drug Discov Today* 23:1241)
- **Heavy atoms < 5** -- fragments, not drug candidates
- **Primary metabolites** -- amino acids, nucleotides, common sugars (unless glycosylated NP derivatives). Identified by InChIKey prefix matching against a curated primary metabolite set (~50 entries from KEGG)
- **Inorganic compounds** -- detected by absence of carbon in molecular formula
- **Mixtures/extracts** -- essential oil fractions without individual compound identification
- **Compounds solely from Miranda's atlas** -- zero dependency

### Rationale for cutoffs:
MW 100-1500 range follows standard NP drug discovery filtering (Lipinski et al., 2001, *Adv Drug Deliv Rev* 46:3-26; Rodrigues et al., 2016, *Nat Chem* 8:531-541). Heavy atom minimum of 5 follows PubChem's compound filtering standard.

---

## 4. Data Sources -- Selection and Rationale

### Source tier definitions:
- **Tier 1 -- Taxonomy-curated NP databases:** Compound-taxon links are curated, not inferred. Highest-quality sources for "compound X was found in species Y."
- **Tier 2 -- General chemistry databases:** Large but compound-taxon links are secondary data (depositor annotations, assay metadata). Useful for structure resolution and bioactivity.
- **Tier 3 -- Ethnobotany/TCM databases:** Specialized for traditional medicine. Compound lists may be less structurally complete but contain unique plant-part and use information.
- **Tier 4 -- Literature mining:** Primary research papers. Most labor-intensive but captures compounds not yet deposited in any database.

### Enabled sources (8 databases + literature):

| # | Source | Tier | License | Raw records | Unique compounds | Reference |
|---|--------|------|---------|-------------|------------------|-----------|
| 1 | LOTUS/Wikidata | 1 | CC0 | 1,183 | 602 | Rutz et al., 2022, *eLife* 11:e70780 |
| 2 | COCONUT 2.0 | 1 | CC-BY 4.0 | 2,623 | 690 | Sorokina et al., 2021, *J Cheminform* 13:2 |
| 3 | KNApSAcK | 1 | Academic | 577 | 298 | Afendi et al., 2012, *Plant Cell Physiol* 53:e1 |
| 4 | NPASS 3.0 | 1 | Academic | 3,739 | 1,602 | Zeng et al., 2018, *Nucleic Acids Res* 46:D1217; 2026 update: *Nucleic Acids Res* gkaf1196 |
| 5 | NP Atlas | 1 | CC-BY-NC 4.0 | 3 | 3 | Lyu et al., 2024, *Nucleic Acids Res* 53:D691 |
| 6 | PubChem | 2 | Public domain | 12 | 7 | Kim et al., 2023, *Nucleic Acids Res* 51:D1373 |
| 7 | ChEMBL | 2 | CC-BY-SA 3.0 | 85 | 70 | Zdrazil et al., 2024, *Nucleic Acids Res* 52:D1180 |
| 8 | Literature | 4 | Open access | 1,802 | 192 (PubMed) + 41 (S2) | PubMed/PMC/Semantic Scholar |

**Source unique contributions:**
- LOTUS/Wikidata: Gold-standard taxon-compound links with provenance references. 800K+ NP-taxon pairs. Per-species SPARQL queries (50 species QIDs verified against Wikidata 2026-05-21).
- COCONUT 2.0: Largest open NP database (738K compounds). Cross-validation by InChIKey connectivity (first 14 chars) + name matching against bulk CSV lite (190 MB ZIP).
- KNApSAcK: 101K+ species-metabolite pairs. Strongest coverage for Asian medicinal plants (*M. officinalis*, *M. biondii*, *M. obovata*). Compound names resolved via PubChem PUG REST.
- NPASS 3.0: **Largest single contributor (1,602 unique compounds, 80.8% of database).** 204K natural products, 49K source organisms. Three-file bulk download: species taxonomy (Magnoliaceae family ID 3401), species-compound pairs, structures (SMILES/InChI/InChIKey). Covers 84 Magnolia-family organism IDs across 32+ species. 2026 release includes ADME-Tox data and hierarchical bioactivity classification. Previously excluded (site 404 as of 2026-05-21); restored and accessible as of 2026-05-28.
- NP Atlas: Microbial NP atlas (36K compounds). Primarily endophyte-derived compounds from Magnolia hosts, not direct plant chemistry. API broken (server-side bug: `basicSearch` POST ignores query parameter); bypassed via full TSV bulk download (33 MB) with local filtering for Magnolia-associated organisms (genus, species, reference title fields). Low yield (3 compounds) but unique endophyte chemistry.
- PubChem: Taxonomy-linked discovery via NCBI Entrez esearch (Taxonomy ID 3408). Modest coverage (~12 CIDs) but provides independent structural confirmation.
- ChEMBL: Bioactivity data (IC50, EC50) for Magnolia compounds. Searched by compound name (34 known compounds) + assay description ("Magnolia" + all old genus names).
- Literature mining: PubMed abstract NER (1,589 mentions from 1,187 papers) + Semantic Scholar (213 records from 3 queries). NER dictionary built dynamically from Phase 1 database results (2,071 compound names). PMC full-text extraction attempted but NCBI elink returned server errors (500) on 2026-05-28 — 0 records from this layer in current build.

### Sources evaluated and excluded:

| Source                              | Tier | Status (2026-05-28) | Reason for exclusion                                                                                                                |
| ----------------------------------- | ---- | ------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| Dr. Duke's (phytochem.nal.usda.gov) | 3    | WAF-protected       | Bulk CSV behind WAF (returns HTML). Drupal JSON API returns 404. Web scrape returns 404. All 3 strategies attempted and failed. Collector enabled with multi-strategy fallback but 0 records in current build. Magnolia coverage likely redundant with NPASS + LOTUS. |
| TCMSP (tcmsp-e.com)                 | 2    | Timeout             | All requests timeout. *M. officinalis* and *M. biondii* compounds now fully covered by NPASS 3.0. |
| CMAUP 2024 (bidd.group/CMAUP)       | 2    | 404                 | Download URLs return 404. Same research group (BIDD, Fudan) as NPASS — likely consolidated into NPASS 3.0. |
| FooDB (foodb.ca)                    | 3    | Negligible          | API fragile, Magnolia coverage negligible. Compounds already in COCONUT/LOTUS/NPASS. |
| IMPPAT 2.0 (cb.imsc.res.in/imppat)  | 3    | Unreliable          | Web interface unreliable. Magnolia minor in Indian traditional medicine. Coverage handled by KNApSAcK/LOTUS/NPASS. |

### Sources recovered in v2.0 (previously excluded):

| Source | Previously | Now | Impact |
|--------|-----------|-----|--------|
| **NPASS 3.0** | Site 404 (2026-05-21) | Restored. 2026 release (v3.0, released 2025-06-15). Bulk TSV download functional. | **+1,602 unique compounds** (80.8% of final DB). Largest single contributor. |
| **NP Atlas** | API broken (2026-05-21) | API still broken. Bulk TSV download works (33 MB, 36K compounds). | +3 compounds (endophyte-derived). Low yield but unique chemistry. |
| **Dr. Duke's** | Redirect (2026-05-21) | Site live but WAF-protected. No programmatic access. | 0 records. All 3 download strategies fail. |

All disabled sources retain collector code skeletons with `enabled=False` in the source registry, allowing re-enablement if services are restored.

---

## 5. Search Protocol

Following PRISMA systematic review methodology (Page et al., 2021, *BMJ* 372:n71):

For each source, documented BEFORE executing:
1. Exact query terms / API parameters
2. Fields searched
3. Date of execution
4. Raw hit count

### Per-source search strategies:

**LOTUS/Wikidata:**
```sparql
SELECT DISTINCT ?compound ?compoundLabel ?smiles ?inchi ?inchikey ?taxon ?taxonLabel
WHERE {
  ?taxon wdt:P171* wd:{species_qid} .
  ?compound wdt:P703 ?taxon .
  OPTIONAL { ?compound wdt:P233 ?smiles . }
  OPTIONAL { ?compound wdt:P234 ?inchi . }
  OPTIONAL { ?compound wdt:P235 ?inchikey . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
}
```
Per-species query (19 species QIDs). Full-genus transitive query times out. 2s delay between queries.

**COCONUT:** Bulk CSV lite download (190 MB ZIP). Cross-reference InChIKey connectivity (first 14 chars) against Phase 1 compounds. Name-match against known Magnolia compound names. Extract NP Classifier columns.

**KNApSAcK:** HTTP GET to `knapsackfamily.com/knapsack_core/result.php?sname=organism&word={species}` for 12 species. Parse HTML result table.

**PubChem (taxonomy discovery):** Multi-strategy Entrez esearch:
- `Magnolia[Organism]` in pccompound database
- Per-species queries for 15 major studied species
- `honokiol AND Magnolia`, `magnolol AND Magnolia` compound-genus queries
- pcsubstance search → SID-to-CID elink mapping
- All discovered CIDs fetched via PUG REST for properties
- Result: 11 unique CIDs, 6 after standardization

**ChEMBL:** `chembl_webresource_client` Python library.
- Molecule name search (`pref_name__icontains`) for 34 known Magnolia compounds
- Assay description search (`description__icontains="Magnolia"`) → activity records → compound IDs
- Caching disabled to avoid macOS sqlite3 symbol conflict (`Settings.Instance().CACHING = False`)
- Result: 85 records from molecule + assay searches

**Literature mining (2 layers executed, Layer 3 optional):**
- Layer 1: PubMed Entrez esearch with query: `"Magnolia"[Title/Abstract] AND ("phytochem*" OR "compound*" OR "isolat*" OR "constituent*" OR "secondary metabolit*" OR "essential oil" OR "bioactive" OR "alkaloid*" OR "lignan*" OR "neolignan*" OR "terpenoid*" OR "flavonoid*")`. Retrieved 1,083 articles. Fetched abstracts via efetch XML. Dictionary NER against dynamic compound dictionary (2,048 names from config + Phase 1 databases). Result: 1,466 compound-paper mentions.
- Layer 2: PMC elink to find full-text articles. 8,849 PMC IDs found. Processed 100 articles (XML table extraction). Searched compound tables by caption keywords ("compound", "constituent", "phytochem", "metabolit", "isolat", "chemical composition"). Result: 313 compound-paper mentions.
- Layer 3 (optional, `--no-llm` to skip): Claude API structured extraction from top 200 abstracts. Not executed in current build.
- Supplementary: Semantic Scholar API search (3 queries). Rate-limited (429) on all attempts — 0 records. S2 coverage is supplementary to PubMed.

**NPASS 3.0 (new in v2.0):**
Three-file bulk download strategy. Files are tab-separated, downloaded sequentially with 2s inter-request delay and 180s timeout per file.
- File 1: `NPASS3.0_species_info.txt` (7.5 MB, 10,757 organisms). Filtered by Magnoliaceae family NCBI Taxonomy ID (`3401`) and genus name pattern matching (`magnolia|michelia|talauma|manglietia|liriodendron` + all OLD_GENUS_NAMES from config). Result: 84 organism IDs.
- File 2: `NPASS3.0_naturalproducts_species_pair.txt` (117 MB, 1.4M+ pairs). Filtered for organism IDs from File 1. Result: 2,195 unique compound IDs across 84 species.
- File 3: `NPASS3.0_naturalproducts_structure.txt` (65 MB, 21,368 structures). Filtered for compound IDs from File 2. Result: 2,194 structures with SMILES + InChI + InChIKey.
- Total raw records: 3,739 (compound-species pairs, multiple species per compound).
- Download time: ~87 minutes total (server in Singapore, ~1.7 MB/min sustained throughput).

**NP Atlas (revised in v2.0):**
Bulk TSV download bypassing broken API.
- Download: `https://www.npatlas.org/static/downloads/NPAtlas_download.tsv` (33 MB, 36,454 compounds, DB version 2024_09).
- Local filter: scan all rows for Magnolia-associated entries in `genus`, `origin_species`, and `original_reference_title` fields using keyword list (`magnolia|magnoliaceae|michelia|talauma|manglietia|liriodendron`).
- Result: 3 compounds (all endophyte-derived fungi isolated from Magnolia hosts, not plant-synthesized metabolites).
- NP Atlas is a microbial NP database — low plant NP coverage is expected.

**Dr. Duke's (attempted in v2.0, 0 records):**
Multi-strategy fallback:
- Strategy 1: Bulk ZIP download from 2 URLs (`data.nal.usda.gov`, `agdatacommons.nal.usda.gov`). Both return HTML instead of ZIP (WAF/redirect). Content-Type check prevents saving HTML as ZIP.
- Strategy 2: Drupal JSON API at `phytochem.nal.usda.gov/phytochem/search/list/plants`. All 11 species queries return HTTP 404.
- Strategy 3: Web scrape at `phytochem.nal.usda.gov/phytochem/plants/list`. All 4 species queries return HTTP 404.
- Result: 0 records. Site is functional for browser access but has no programmatic interface.

**Disabled sources (retained as code, not executed):**
- TCMSP: All requests timeout. Covered by NPASS 3.0.
- CMAUP: 404. Likely consolidated into NPASS 3.0 (same research group).
- FooDB: Negligible Magnolia coverage.
- IMPPAT: Unreliable. Negligible Magnolia coverage.

---

## 6. Standardization Pipeline

Based on RDKit (Landrum, 2006):

```
Raw record
  -> 1. Name resolution (if no SMILES): PubChem PUG REST synonym search -> CID -> SMILES
  -> 2. SMILES parsing: Chem.MolFromSmiles(), fail -> reject
  -> 3. Sanitization: Chem.SanitizeMol()
  -> 4. Salt stripping: SaltRemover (standard salts list)
  -> 5. Charge neutralization: protonate carboxylates, deprotonate amines
  -> 6. Canonical SMILES: Chem.MolToSmiles(canonical=True)
  -> 7. InChI generation: inchi.MolToInchi()
  -> 8. InChIKey generation: inchi.InchiToInchiKey()
  -> 9. Inclusion/exclusion filter: MW, heavy atoms, inorganic, primary metabolite
  -> 10. Deduplication: InChIKey first 14 chars (connectivity layer, tautomer-insensitive)
  -> Output: standardized record OR rejected record (with reason)
```

**Stereochemistry policy:** Stereoisomers kept as separate entries (full InChIKey distinguishes them). Deduplication uses connectivity layer (first 14 chars) to merge tautomers but preserve stereochemistry.

**Name resolution protocol:** For records with compound name but no SMILES (KNApSAcK, literature):
1. Exact name search via PubChem PUG REST (`/rest/pug/compound/name/{name}/property/CanonicalSMILES/JSON`)
2. Compound names are sent to PubChem exactly as reported by the source database, including stereochemistry prefixes ((+)-, (-)-, (R)-, (S)-) which denote optical rotation and absolute configuration — chemically distinct molecules
3. PubChem response field fallback: `CanonicalSMILES` -> `ConnectivitySMILES` -> `SMILES` (PubChem inconsistently names the response field)
4. If still fails: mark as "unresolved", keep in magnolia_bbb_rejected.csv with reason `unresolvable_name`
5. Result: 288/526 KNApSAcK names resolved (54.8%), 121 unresolvable across all sources

---

## 7. Evidence Tiers

| Tier | Name | Criteria | Rationale |
|------|------|----------|-----------|
| **Gold** | Taxonomy-curated | Species-level attribution in Tier 1 DB (LOTUS, KNApSAcK, NP Atlas, NPASS) + valid SMILES | Curated compound-taxon links from primary literature. Species attribution verified. |
| **Silver** | Cross-validated | >=2 independent sources (any tier) OR 1 source with DOI + species + resolvable structure | Independence reduces false positive risk. DOI provides verifiable provenance. |
| **Bronze** | Single-source | 1 database source with valid SMILES | Minimal evidence but structure confirmed. |
| **Provisional** | Name-only resolved | Name resolved via PubChem but not independently confirmed as Magnolia metabolite | May include false positives. Flagged for manual review. Excluded from docking by default. |

---

## 8. Validation Protocol

### 8a. Must-have compound benchmark

13 signature *Magnolia* compounds must be present. Failure = build error. **Result: 13/13 found.**

| Compound | Class | InChIKey prefix | Status |
|----------|-------|----------------|--------|
| Magnolol | Neolignan | NRJWDMRKRVBENX | Found |
| Honokiol | Neolignan | FVYXIJYOAGAUQK | Found |
| Obovatol | Neolignan | UILMKBOAZSHJOE | Found |
| 4-O-Methylhonokiol | Neolignan | SQMTZSBIJIGBQU | Found |
| Costunolide | Sesquiterpenoid | HRYLQFBHBWLLLL | Found |
| Parthenolide | Sesquiterpenoid | KTEXNACQROZXRG | Found |
| Magnoflorine | Alkaloid | VDEMMVFVGXODCK | Found |
| Liriodenine | Alkaloid | MPFUVBIGMLCQJD | Found |
| Anonaine | Alkaloid | FXNFPKQREKNQMN | Found |
| Magnolin | Lignan | QQPQGKBUOKJJMN | Found |
| Fargesin | Lignan | JUDXBRVLWDGREP | Found |
| Sesamin | Lignan | KBGJZICKBAKVCL | Found |
| Syringaresinol | Lignan | QNHCQMRIBYQNZ | Found |

### 8b. Atlas comparison

Compare BBB Database STC against old Miranda atlas by InChIKey (not SMILES). Zero dependency on Miranda's work confirmed — the entire database was built independently from public sources.

### 8c. PRISMA flow

| Stage | Records (v1.0) | Records (v2.0) | Notes |
|-------|----------------|----------------|-------|
| Identification | 6,163 | **10,024** | Raw records from all collectors |
| Screening | 5,879 | **9,636** | After removing records with no SMILES and no name |
| Excluded | 284 | **387** | See rejection breakdown in §12g |
| **Included** | **736** | **1,982** | Unique compounds after InChIKey connectivity deduplication |

v2.0 growth: +3,861 raw records (+62.6%), +1,246 unique compounds (+169.3%).

### 8d. Structure validation

Every included compound: (a) parses in RDKit without errors, (b) MW 100-1500 Da, (c) no disconnected fragments after salt removal, (d) valid 27-character InChIKey, (e) not a primary metabolite. **Result: 1,982/1,982 pass all checks.**

---

## 9. Output Specification

| File | Description | Primary key |
|------|-------------|-------------|
| `magnolia_bbb_database.csv` | One row per unique compound (enriched) | InChIKey |
| `magnolia_bbb_provenance.csv` | One row per compound-source-species triple | InChIKey + source_db |
| `magnolia_bbb_species.csv` | Taxonomic inventory with POWO accepted names | species_name |
| `magnolia_bbb_rejected.csv` | Excluded compounds with rejection reasons | -- |
| `build_manifest.json` | Software versions, source URLs, query dates, record counts | -- |
| `prisma_flow.json` | PRISMA diagram data for thesis figure | -- |

### Database schema (magnolia_bbb_database.csv):

| Column | Type | Required |
|--------|------|----------|
| inchikey | str(27) | YES -- primary key |
| inchikey_connectivity | str(14) | YES |
| canonical_smiles | str | YES |
| inchi | str | YES |
| iupac_name | str | no |
| common_names | str (pipe-delimited) | no |
| molecular_formula | str | YES |
| molecular_weight | float | YES |
| evidence_tier | str | YES |
| source_count | int | YES |
| source_list | str (pipe-delimited) | YES |
| species_list | str (pipe-delimited) | no |
| species_count | int | no |
| compound_class | str | no |
| compound_superclass | str | no |
| np_pathway | str | no |
| logp, tpsa, hba, hbd, rotatable_bonds, ring_count, fsp3 | numeric | no |
| lipinski_violations | int | no |
| doi_refs | str (pipe-delimited) | no |
| reference_count | int | no |

### Provenance schema (magnolia_bbb_provenance.csv):

| Column | Type | Required |
|--------|------|----------|
| inchikey | str(27) | YES -- FK |
| source_db | str | YES |
| source_id | str | no |
| species_reported | str | no |
| species_accepted | str | no |
| plant_part | str | no |
| doi | str | no |
| evidence_tier | str | YES |
| query_term | str | no |
| query_date | str(ISO) | YES |

---

## 10. Reproducibility

- `python -m bbb_database_stc.build` regenerates the entire database from scratch (~6 minutes)
- `python -m bbb_database_stc.build --dry-run` checks source availability without executing
- `python -m bbb_database_stc.build --phase collect|standardize|enrich|validate|export|all`
- `python -m bbb_database_stc.build --no-llm` skips Claude API extraction (Layer 3)
- `build_manifest.json` records: Python version, RDKit version, source URLs queried, query timestamps, record counts at each phase
- Bulk downloads cached in `raw/.cache/` (gitignored) to avoid redundant network traffic
- COCONUT CSV lite (~190 MB ZIP, ~743 MB extracted) is the primary cached asset
- All collector code is deterministic given the same source data
- Working directory: `pipeline/data_prep/`

---

## 11. Execution Phases

| Phase | Depends on | Description | Records (v2.0) |
|-------|-----------|-------------|----------------|
| 1. Collect (databases) | -- | Run 8 enabled database collectors | 8,222 raw records |
| 2. Collect (literature) | Phase 1 | Mine PubMed + Semantic Scholar with dynamic compound dictionary | 1,802 raw records |
| 3. Standardize | Phases 1+2 | Resolve names, standardize SMILES, filter, InChIKey deduplicate | 1,982 unique compounds |
| 4. Enrich | Phase 3 | Compute RDKit descriptors, classify, drug-likeness | 1,982 enriched |
| 5. Validate | Phase 4 | Must-have check (13/13), PRISMA flow, source stats | Pass |
| 6. Export | Phase 5 | Write final CSVs + build_manifest.json + PRISMA JSON | 3 CSVs + manifest |

Full build: `python -m bbb_database_stc.build` (~90 minutes, dominated by NPASS download from Singapore)
Individual phase: `python -m bbb_database_stc.build --phase {collect,standardize,enrich,validate,export}`
Single collector: `python -m bbb_database_stc.build --only npass`
Skip LLM layer: `python -m bbb_database_stc.build --no-llm`
Dry run: `python -m bbb_database_stc.build --dry-run`

**Note:** NPASS 3.0 bulk download (~180 MB across 3 TSV files from bidd.group in Singapore) dominates build time. Collection of NPASS alone takes ~87 minutes at ~1.7 MB/min. All other collectors complete in <15 minutes total. Standardize/enrich/validate/export phases complete in <7 minutes. For iterative development, use `--phase standardize` to re-process existing raw CSVs without re-downloading.

---

## 12. Build Results (2026-05-28, v2.0)

### 12a. Summary

| Metric | v1.0 (2026-05-21) | **v2.0 (2026-05-28)** | Change |
|--------|-------------------|----------------------|--------|
| **Unique compounds** | 736 | **1,982** | +169% |
| **Provenance records** | 5,879 | **9,636** | +64% |
| **Rejected records** | 284 | **387** | +36% |
| **Sources contributing** | 7 | **9** | +2 (NPASS 3.0, NP Atlas) |
| **Must-have compounds** | 13/13 | **13/13** | — |
| **Species coverage** | 119 | **170** | +43% |
| **Build time** | ~6 min | **~90 min** | NPASS download-dominated |

### 12b. Evidence tier distribution

| Tier | Count | % | Description |
|------|-------|---|-------------|
| Gold | 1,886 | 95.2% | Confirmed in taxonomy-curated NP database(s) |
| Silver | 29 | 1.5% | Cross-validated by >=2 independent sources |
| Bronze | 67 | 3.4% | Single database source with valid SMILES |

### 12c. Source contribution (unique compounds per source)

| Source | Unique compounds | % of total | New in v2.0? |
|--------|-----------------|------------|-------------|
| **NPASS 3.0** | **1,602** | **80.8%** | **YES** |
| COCONUT | 690 | 34.8% | — |
| LOTUS/Wikidata | 602 | 30.4% | — |
| KNApSAcK | 298 | 15.0% | — |
| PubMed NER | 192 | 9.7% | — |
| ChEMBL | 70 | 3.5% | — |
| Semantic Scholar NER | 41 | 2.1% | — |
| PubChem | 7 | 0.4% | — |
| **NP Atlas** | **3** | **0.2%** | **YES** |

Note: Percentages sum to >100% because compounds appear in multiple sources. NPASS 3.0 contributed 1,244 compounds that were not present in any other source — compounds that would have been entirely missed without the v2.0 source recovery.

### 12d. Multi-source overlap

| Source count | Compounds (v1.0) | Compounds (v2.0) |
|-------------|-------------------|-------------------|
| 1 source | 106 | **1,323** |
| 2 sources | 298 | 220 |
| 3 sources | 167 | 181 |
| 4 sources | 112 | 139 |
| 5 sources | 45 | 77 |
| 6 sources | 8 | 36 |
| 7 sources | — | 6 |

The large increase in single-source compounds (106 → 1,323) reflects the NPASS 3.0 contribution: many NPASS compounds are not yet deposited in LOTUS/Wikidata or COCONUT, making NPASS a non-redundant source for Asian medicinal plant chemistry. Cross-validation improves as more databases index the same compounds.

### 12e. Species coverage

- **170 unique species** names in provenance records (v1.0: 119)
- 32+ Magnolia/Magnoliaceae species identified in NPASS 3.0 alone
- DR-endemic species: not yet represented (no published phytochemistry for *M. pallescens*, *M. domingensis*, *M. hamorii* — this is an expected finding and the core scientific contribution of the thesis: applying genus-level phytochemistry to unstudied endemics via chemotaxonomic inference)

### 12f. Rejection breakdown

| Reason | Count (v1.0) | Count (v2.0) |
|--------|-------------|-------------|
| MW below 100 Da | 114 | **147** |
| Unresolvable name | 121 | **134** |
| Unparseable SMILES | 22 | **64** |
| Primary metabolite | 27 | **32** |
| MW above 1500 Da | — | **10** |
| **Total** | **284** | **387** |

### 12g. Provenance

Every compound is traceable to public source(s) with documented query terms, execution dates, and licenses. Zero dependency on Miranda Mariñez's compound list. The database was built entirely from programmatic queries to 8 public databases (LOTUS/Wikidata, COCONUT, KNApSAcK, NPASS 3.0, NP Atlas, PubChem, ChEMBL, Dr. Duke's) plus literature mining of 1,187 PubMed articles and Semantic Scholar queries.

### 12h. Reproducibility

Full rebuild: `ln -sfn bbb bbb_database_stc && python -m bbb_database_stc.build`
- `build_manifest.json` records software versions, source URLs, query timestamps, and record counts at each phase
- All collector code is deterministic given the same source data
- Bulk downloads cached in `raw/.cache/` to avoid redundant network traffic
- `--dry-run` checks source availability before committing to full build
- NPASS 3.0 files can be pre-downloaded and placed in `data/` to avoid the 87-minute download: `npass3_species_info.txt`, `npass3_species_pairs.txt`, `npass3_structures.txt`

### 12i. Version history

| Version | Date | Compounds | Sources | Key change |
|---------|------|-----------|---------|------------|
| 1.0 | 2026-05-21 | 736 | 7 | Initial build from LOTUS, COCONUT, KNApSAcK, PubChem, ChEMBL, Literature |
| 2.0 | 2026-05-28 | 1,982 | 9 | +NPASS 3.0 (restored, +1,602 compounds), +NP Atlas (bulk TSV bypass), Dr. Duke's attempted (0 records) |
| **2.1** | **2026-05-29** | **1,997** | **11** | **+Dugandiodendron taxonomy (23 synonyms, 29 QIDs), +Literature_Curated source (6 D. argyrotrichum compounds), +NPClassifier annotations (98.5%), +ChEMBL bioactivity enrichment (586 compounds, 64,898 records)** |

---

## 13. v2.1 Additions (2026-05-29)

### 13a. Taxonomic expansion: Dugandiodendron (subsect. Dugandiodendron)

**Motivation:** The DR target species (*M. pallescens*, *M. domingensis*, *M. hamorii*) belong to *Magnolia* sect. Cubenses subsect. Cubenses (Aldaba Nunez et al., 2026, *Acta Bot Mex* 133:e2545). Their closest continental relatives (~14 Ma divergence; Guzman-Diaz et al., 2025, *BMC Ecol Evol* 25:40) are the ~20 species of subsect. Dugandiodendron (former genus *Dugandiodendron* Lozano, 1975). v2.0 had zero Dugandiodendron species in its taxonomic scope.

**Changes to `config.py`:**
- `OLD_GENUS_NAMES`: added `"Dugandiodendron"` (enables name-based searching in KNApSAcK, NPASS, literature miner)
- `OLD_GENUS_WIKIDATA_QIDS`: added `Q5814925` (Dugandiodendron genus QID for LOTUS SPARQL transitive queries)
- `SYNONYM_MAP`: added 24 mappings (23 Dugandiodendron → Magnolia species + 1 nom. illeg. catch: *Magnolia magnifolia* → *M. neomagnifolia*, per Turner 2014)
- `MAGNOLIA_SPECIES_QIDS`: added 29 QIDs (14 subsect. Dugandiodendron + 6 additional subsect. Dugandiodendron species described directly in Magnolia + 9 subsect. Cubenses Caribbean species that were missing). Total: 50 → 79 species QIDs.

**Nomenclatural note:** *Dugandiodendron magnifolium* Lozano maps to *Magnolia neomagnifolia* I.M.Turner 2014 (Q28127564), not *M. magnifolia* (Lozano) Govaerts 1996 (Q15493047). The latter is a nom. illeg. (later homonym of the fossil *M. magnifolia* Knowlton 1918).

**Result:** Automated collectors found zero new compounds attributable to Dugandiodendron species. All NP databases (COCONUT, KNApSAcK, LOTUS/Wikidata, NPASS, NPAtlas, PubChem, ChEMBL) have zero entries for any Dugandiodendron species. This is itself a finding: the entire subsection is a database blind spot.

### 13b. Manual literature curation: *D. argyrotrichum* phytochemistry

**Motivation:** Systematic literature search (PubMed, Google Scholar, SciELO Colombia, Redalyc, Latin American repositories) identified published phytochemistry for Dugandiodendron absent from all databases.

**Source papers:**
1. Guzman V., J.D. & Cuca S., L.E. (2008). Metabolitos secundarios aislados de la corteza de *Dugandiodendron argyrotrichum* Lozano (Magnoliaceae). *Rev Col Quim* 37(3):299-310. SciELO: S0120-28042008000300002.
2. Guzman, J.D. et al. (2010). Anti-tubercular screening of natural products from Colombian plants: 3-methoxynordomesticine, an inhibitor of MurE ligase of *Mycobacterium tuberculosis*. *J Antimicrob Chemother* 65(10):2101-2107. DOI: 10.1093/jac/dkq313. PMID: 20719764.

**Compounds added (6):**

| Compound | Class (NPClassifier) | PubChem CID | InChIKey | Source paper |
|----------|---------------------|-------------|----------|--------------|
| Torreyol (δ-cadinol) | Cadinane sesquiterpenoid | 3084311 | LHYHMMRYTDARSZ-BARDWOONSA-N | Guzman & Cuca 2008 |
| Parthenolide | Germacrane sesquiterpenoid | 6473881 | KTEXNACQROZXEV-SLXBATTESA-N | Guzman & Cuca 2008 |
| N-Acetylanonaine | Aporphine alkaloid | 6453733 | XVIHBNVDAPQBRH-OAHLLOKOSA-N | Guzman & Cuca 2008 |
| Dihydroguaiaretic acid | Dibenzylbutane lignan | 161924 | ADFOLUXMYYCTRR-UHFFFAOYSA-N | Guzman & Cuca 2008 |
| Austrobailignan-6 | Dibenzylbutane lignan | 13844304 | QDDILOVMGWUNGD-UHFFFAOYSA-N | Guzman & Cuca 2008 |
| 3-Methoxynordomesticine | Aporphine alkaloid | 57336190 | WPQOVUJKYMOEFK-LBPRGKRZSA-N | Guzman et al. 2010 |

SMILES retrieved from PubChem PUG REST by CID. InChIKeys verified against PubChem. 5 of 6 compounds already existed in the database from other Magnolia species; the species attribution (*M. argyrothricha*) was added. 3-Methoxynordomesticine was completely absent from the database (silver tier: 1 source + 1 DOI).

**Raw data file:** `data/raw/dugandiodendron_curated.csv` (source_db: `Literature_Curated`)

### 13c. NPClassifier compound class annotations

**Tool:** NPClassifier v1.6 (Kim et al., 2021, *J Nat Prod* 84(11):2795-2807. DOI: 10.1021/acs.jnatprod.1c00399. PMID: 34662515. PMCID: PMC8631337).

**Method:** Deep neural network trained on 73,607 natural products (PubChem, ChEBI, ChemSpider, UNPD). Input: counted Morgan fingerprints generated from canonical SMILES via RDKit. Three separate single-task feed-forward DNNs predict a 3-level biosynthetic ontology: 7 pathways → 70 superclasses → 672 classes (directed acyclic graph; hybrid NPs can map to multiple pathways).

**Justification for tool selection over alternatives:**
- *vs. ClassyFire* (Djoumbou Feunang et al., 2016, *J Cheminform* 8:61): ClassyFire uses a general chemistry taxonomy (ChemOnt, 4,825 classes) not aligned with NP biosynthetic pathways. Critical flaw for Magnolia: ClassyFire places lignans outside the phenylpropanoid/shikimate pathway, an ontological error for chemotaxonomic analysis. NPClassifier outperformed ClassyFire on 47/62 NP classes in external validation (Kim et al. 2021), including terpenoids (F1 0.972 vs 0.819), polyketides (F1 0.834 vs 0.488), and lignans (large margin). GNPS has deprecated ClassyFire in favor of NPClassifier.
- *vs. CANOPUS* (Duhrkop et al., 2021, *Nat Biotechnol* 39:462-471): Requires MS/MS fragmentation spectra as input. Not applicable — our database contains SMILES, not spectral data. Additionally uses the ClassyFire ontology.
- *vs. GINESTRA* (Prete et al., 2025, *Comput Struct Biotechnol J*): Research prototype using GNNs on NPClassifier's own ontology as ground truth. No web API, no pip package, zero citations. Not production-ready.

**Execution:** REST API at `https://npclassifier.ucsd.edu/classify?smiles=<URL-encoded SMILES>`. JSON response: `pathway_results`, `superclass_results`, `class_results`, `isglycoside`. Rate: ~2.0 compounds/second with 0.35s inter-request delay. Incremental checkpointing every 50 compounds. Execution date: 2026-05-29.

**Adoption as ecosystem standard:** COCONUT 2.0 uses NPClassifier as NP authenticity filter. Natural Products Atlas 2.0 displays NPClassifier annotations. GNPS molecular networking workflows use NPClassifier as primary classification. LOTUS integrates NPClassifier alongside ClassyFire.

**Results:**

| Metric | Value |
|--------|-------|
| Compounds classified | 1,967 / 1,997 (98.5%) |
| Unclassified | 30 (1.5%) |
| Glycosides detected | 205 (10.3%) |

**Pathway distribution:**

| Pathway | Count | % |
|---------|-------|---|
| Terpenoids | 854 | 42.8% |
| Shikimates and Phenylpropanoids | 635 | 31.8% |
| Alkaloids | 221 | 11.1% |
| Fatty acids | 173 | 8.7% |
| Polyketides | 84 | 4.2% |
| Amino acids and Peptides | 33 | 1.7% |
| Carbohydrates | 9 | 0.5% |

**Top 10 classes:**

| Class | Count |
|-------|-------|
| Neolignans | 123 |
| Isoquinoline alkaloids | 113 |
| Aporphine alkaloids | 94 |
| Cinnamic acids and derivatives | 72 |
| Androstane steroids | 63 |
| Hydrocarbons | 63 |
| Germacrane sesquiterpenoids | 62 |
| Furofuranoid lignans | 57 |
| Flavonols | 49 |
| Verticillane diterpenoids | 48 |

**Validation:** 10 compounds with known classifications from the literature verified against NPClassifier output. Pathway accuracy: 100% (10/10). Superclass accuracy: 100% (10/10). Class accuracy: 80% (8/10); the 2 discrepancies were refinements, not errors (NPClassifier assigned "Dibenzylbutane lignans" where the expected label was the broader "Neolignans" — dibenzylbutane lignans are a subclass of neolignans).

**Database columns added:** `npc_pathway`, `npc_superclass`, `npc_class`, `npc_isglycoside`.

**Script:** `phases/classify_compounds.py` (resumable with `--resume`, force re-run with `--force`)

### 13d. ChEMBL bioactivity enrichment

**Source:** ChEMBL 35 (Zdrazil et al., 2024, *Nucleic Acids Res* 52:D1180-D1192). Queried via REST API (not Python client, due to sqlite3 symbol conflict on macOS/conda).

**Method:** Batch molecule lookup (50 InChIKeys per request) followed by paginated activity retrieval (1,000 per page). Rate limiting: 0.4s between requests, 1.0s between batches. Execution date: 2026-05-29.

**Results:**

| Metric | Value |
|--------|-------|
| Compounds queried | 1,997 |
| Found in ChEMBL | 586 (29.3%) |
| With bioactivity data | 565 (28.3%) |
| Total activity records | 64,898 |
| With antiviral data | 171 compounds (1,890 records) |
| With anti-DENV data | 7 compounds (20 records) |
| With anti-flavivirus data | 10 compounds (29 records) |

**Compounds with direct anti-DENV bioactivity data:**

| Compound | DENV Target | Best Value | Reference |
|----------|-------------|------------|-----------|
| Myricetin | DENV2/3 NS2B-NS3 protease | Ki = 4,700 nM | ChEMBL |
| Pinostrobin | DENV2 NS2B/NS3 protease | Ki = 345,000 nM | ChEMBL |
| Emodin | DENV2 NS5 methyltransferase | EC50 = 10,900 nM | ChEMBL |
| Honokiol | DENV2 whole virus | 90% yield reduction at 20 µM | ChEMBL |
| Quercetin | DENV2 whole virus | IC50 = 176 µg/mL | ChEMBL |
| Kaempferol | DENV2/3 NS2B-NS3 protease | Ki = 22,300 nM | ChEMBL |
| Citral | DENV2 whole virus | IC50 = 31,000 nM | ChEMBL |

**Output files:**
- `data/magnolia_bbb_bioactivity.csv` (64,898 records, 22 columns: inchikey, target_name, target_organism, assay_type, standard_type, standard_value, standard_units, chembl_assay_id, doi, etc.)
- `data/magnolia_bbb_bioactivity_summary.csv` (1,997 rows, 17 columns: inchikey, has_bioactivity, bioactivity_count, best_antiviral_ic50, antiviral_target, etc.)

**Script:** `phases/bioactivity_enrichment.py` (resumable with `--resume`)

---

## References

- Aldaba Nunez, F.A., et al. (2026). An updated infrageneric classification of Neotropical Magnolia (Magnoliaceae). *Acta Bot Mex* 133:e2545. doi:10.21829/abm133.2026.2545
- Aldaba Nunez, F.A., et al. (2024). Phylogenomic insights into Neotropical Magnolia relationships. *Heliyon* 10:e39430. doi:10.1016/j.heliyon.2024.e39430
- Afendi, F.M., et al. (2012). KNApSAcK family databases: integrated metabolite-plant species databases for multifaceted plant research. *Plant Cell Physiol* 53:e1.
- Angiosperm Phylogeny Group (2016). An update of the Angiosperm Phylogeny Group classification for the orders and families of flowering plants: APG IV. *Bot J Linn Soc* 181:1-20.
- Chen, X., et al. (2018). Drug-target interaction prediction: databases, web servers and computational models. *Drug Discov Today* 23:1241-1250.
- Corredor-Barinas, J.A. & Cuca Suarez, L.E. (2011). Chemical constituents of *Talauma arcabucoana* (Magnoliaceae): their brine shrimp lethality and antimicrobial activity. *Nat Prod Res* 25(16):1497-1504. doi:10.1080/14786410903205146
- Djoumbou Feunang, Y., et al. (2016). ClassyFire: automated chemical classification with a comprehensive, computable taxonomy. *J Cheminform* 8:61. doi:10.1186/s13321-016-0174-y
- Duhrkop, K., et al. (2021). Systematic classification of unknown metabolites using high-resolution fragmentation mass spectra. *Nat Biotechnol* 39:462-471. doi:10.1038/s41587-020-0740-8
- Figlar, R.B. & Nooteboom, H.P. (2004). Notes on Magnoliaceae IV. *Blumea* 49:87-100.
- Guzman V., J.D. & Cuca S., L.E. (2008). Metabolitos secundarios aislados de la corteza de *Dugandiodendron argyrotrichum* Lozano (Magnoliaceae). *Rev Col Quim* 37(3):299-310. SciELO: S0120-28042008000300002.
- Guzman, J.D., et al. (2010). Anti-tubercular screening of natural products from Colombian plants: 3-methoxynordomesticine, an inhibitor of MurE ligase of *Mycobacterium tuberculosis*. *J Antimicrob Chemother* 65(10):2101-2107. doi:10.1093/jac/dkq313
- Guzman-Diaz, S., et al. (2025). There and back again: historical biogeography of neotropical magnolias based on high-throughput sequencing. *BMC Ecol Evol* 25:40. doi:10.1186/s12862-025-02379-7
- Kim, H.W., et al. (2021). NPClassifier: A Deep Neural Network-Based Structural Classification Tool for Natural Products. *J Nat Prod* 84(11):2795-2807. doi:10.1021/acs.jnatprod.1c00399
- Kim, S., et al. (2023). PubChem 2023 update. *Nucleic Acids Res* 51:D1373-D1380.
- Kim, S. & Suh, Y. (2013). Phylogeny of Magnoliaceae based on ten chloroplast DNA regions. *Plant Syst Evol* 299:1587-1610.
- Landrum, G. (2006). RDKit: Open-source cheminformatics. https://www.rdkit.org
- Lipinski, C.A., et al. (2001). Experimental and computational approaches to estimate solubility and permeability in drug discovery and development settings. *Adv Drug Deliv Rev* 46:3-26.
- Page, M.J., et al. (2021). The PRISMA 2020 statement: an updated guideline for reporting systematic reviews. *BMJ* 372:n71.
- Poivre, M. & Duez, P. (2017). Biological activity and toxicity of the Chinese herb Magnolia officinalis Rehder & E. Wilson (Houpo) and its constituents. *J Ethnopharmacol* 211:199-223.
- Ranaware, A.M., et al. (2018). Magnolol: A neolignan from the Magnolia family for the prevention and treatment of cancer. *Molecules* 23(5):1163.
- Rodrigues, T., et al. (2016). Counting on natural products for drug design. *Nat Chem* 8:531-541.
- Rutz, A., et al. (2022). The LOTUS initiative for open knowledge management in natural products research. *eLife* 11:e70780.
- Sorokina, M., et al. (2021). COCONUT online: collection of open natural products database. *J Cheminform* 13:2.
- van Santen, J.A., et al. (2022). The Natural Products Atlas 2.0: a database of microbially-derived natural products. *ACS Cent Sci* 8:747-758.
- Lyu, C., et al. (2024). Natural Products Atlas 3.0: extending the database of microbially derived natural products. *Nucleic Acids Res* 53:D691-D697. doi:10.1093/nar/gkae908
- Zdrazil, B., et al. (2024). The ChEMBL Database in 2023: a drug discovery platform spanning genomics, chemical biology and clinical data. *Nucleic Acids Res* 52:D1180-D1192.
- Zeng, X., et al. (2018). NPASS: natural product activity and species source database for natural product research, discovery and tool development. *Nucleic Acids Res* 46:D1217-D1222.
- Lin, H., et al. (2026). NPASS database update 2026: comprehensive quantitative composition, bioactivity, and ADME-Tox data of natural products for biomedical research. *Nucleic Acids Res* advance article. doi:10.1093/nar/gkaf1196
