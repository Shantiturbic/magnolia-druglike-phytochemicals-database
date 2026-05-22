# BBB Database STC -- Code Architecture Plan

**Date:** 2026-05-21

---

## Directory Structure

```
pipeline/data_prep/bbb_database_stc/
  __init__.py
  config.py                  # Single source of truth for ALL parameters
  build.py                   # Master orchestrator: --phase, --dry-run, --only
  BBB_DATABASE_STC_METHODOLOGY.md   # Thesis-grade methodology
  CODE_ARCHITECTURE.md       # This file
  
  collectors/
    __init__.py
    base.py                  # BaseCollector ABC + RawCompound dataclass
    lotus_wikidata.py        # Tier 1: SPARQL (refactored from v1, tested: 1,198 records)
    coconut.py               # Tier 1: bulk CSV cross-ref (refactored, tested: 2,727 records)
    knapsack.py              # Tier 1: web scraping (refactored, tested: 526 records)
    pubchem_taxonomy.py      # Tier 2: NCBI taxonomy discovery (REWRITTEN)
    chembl_magnolia.py       # Tier 2: bioactivity (from v1, needs testing)
    npatlas.py               # Tier 1: NP Atlas API (from v1, needs testing)
    npass.py                 # Tier 1: bulk download (from v1, needs testing)
    dr_duke.py               # Tier 3: ethnobotany (from v1, needs testing)
    literature_miner.py      # Tier 4: PubMed + PMC + Claude (refactored)
    # Disabled skeletons (enabled=False in config.py):
    tcmsp.py                 # Down as of 2026-05-21
    cmaup.py                 # 404 as of 2026-05-21
    foodb.py                 # Negligible coverage
    imppat.py                # Negligible coverage
  
  phases/
    __init__.py
    standardize.py           # Phase 3: name resolution + RDKit + dedup + rejection log
    enrich.py                # Phase 4: descriptors + NP Classifier + drug-likeness
    validate.py              # Phase 5: must-have check + atlas comparison + PRISMA
    export.py                # Phase 6: final CSVs + build_manifest.json
  
  utils/
    __init__.py
    chem.py                  # RDKit helpers + inclusion/exclusion filters
    http.py                  # Rate-limited HTTP with retry + exponential backoff
    taxonomy.py              # POWO-backed species registry + synonym resolution
```

Output at `bbb/`:
```
magnolia_bbb_database.csv
magnolia_bbb_provenance.csv
magnolia_bbb_species.csv
magnolia_bbb_rejected.csv
build_manifest.json
prisma_flow.json
raw/
  {collector_name}.csv        # One per collector
  {collector_name}.meta.json  # Metadata per collector
  .cache/                     # Bulk downloads (gitignored)
```

---

## config.py -- What Goes In It

### Taxonomic parameters
- TAXONOMY_AUTHORITY, TAXONOMY_TREATMENT, GENUS_WIKIDATA_QID, NCBI_TAXONOMY_ID
- MAGNOLIA_SPECIES_QIDS dict (moved from lotus_wikidata.py)
- DR_ENDEMIC_SPECIES, MAJOR_STUDIED_SPECIES (moved from taxonomy.py)
- TCM_HERB_NAMES, SYNONYM_MAP (moved from taxonomy.py)

### Inclusion/exclusion thresholds
- MW_MIN = 100.0, MW_MAX = 1500.0, HEAVY_ATOM_MIN = 5
- EXCLUDE_INORGANIC, EXCLUDE_PRIMARY_METABOLITES
- PRIMARY_METABOLITE_INCHIKEYS frozenset

### Source registry
```python
@dataclass(frozen=True)
class SourceConfig:
    name: str
    tier: int              # 1-4
    license: str
    url: str
    unique_contribution: str
    enabled: bool
    fallback: str
```

### Evidence tier enum
```python
class EvidenceTier(Enum):
    GOLD = "gold"
    SILVER = "silver"
    BRONZE = "bronze"
    PROVISIONAL = "provisional"
```

### Known compound names
KNOWN_MAGNOLIA_COMPOUNDS -- single canonical list (currently duplicated in 4 files).
Used for COCONUT name matching and NER dictionary seeding. NOT for PubChem search.

### Rate limits, timeouts, paths
All cache paths, output paths, API delay values.

---

## Code Triage: What to Keep, Refactor, Rewrite, Drop

### KEEP (copy with minor changes)
- `utils/chem.py` -- Add inclusion/exclusion filter functions that reference config.py thresholds
- `utils/http.py` -- No changes needed

### REFACTOR (copy + modify)

**collectors/base.py:**
- RawCompound: add `evidence_tier`, `query_term`, `query_date` fields. Drop `confidence`.
- BaseCollector: add `source_config` property from config.py registry
- Call `_write_meta()` in `run()` (already defined, currently never called)

**collectors/lotus_wikidata.py:**
- Species QIDs from config.py (not hardcoded)
- Set evidence_tier = "gold"

**collectors/coconut.py:**
- Extract NP Classifier columns (np_classifier_pathway, _superclass, _class) into RawCompound.extra
- Name fragment list from config.py KNOWN_MAGNOLIA_COMPOUNDS

**collectors/knapsack.py:**
- Search terms from config.py species registry
- Flag needs_structure_resolution = True

**collectors/literature_miner.py:**
- Build NER dictionary dynamically from Phase 1 raw CSVs (not hardcoded)
- Phase 2 runs AFTER Phase 1

**phases/standardize.py (from standardize.py):**
- Add inclusion/exclusion filters from config.py
- Output rejected_compounds.csv with rejection reasons (for PRISMA flow)
- InChIKey first-14-chars dedup option

**phases/enrich.py (from enrich.py):**
- Use NP Classifier data from COCONUT cross-ref first
- Fall back to name-based heuristic only as last resort
- Replace provenance_score with evidence tier system

**phases/validate.py (from validate.py):**
- InChIKey-based atlas comparison (not SMILES)
- PRISMA flow numbers output
- Must-have compound check from config

### REWRITE

**collectors/pubchem_taxonomy.py:**
- Old: searches 88 hardcoded compound names (presupposes findings)
- New: NCBI Taxonomy ID 3408 taxonomy-linked discovery
- Finds ALL compounds PubChem associates with genus Magnolia
- Evidence tier: SILVER

**build.py (from run_full_build.py):**
- Phase orchestration with --phase flag
- --dry-run checks source availability
- Generates build_manifest.json with software versions, timestamps, counts, errors

### DROP FROM ACTIVE BUILD (keep as disabled skeletons)
- tcmsp.py -- enabled=False in config
- cmaup.py -- enabled=False
- foodb.py -- enabled=False
- imppat.py -- enabled=False

---

## Execution Flow

```
build.py --phase all
  |
  Phase 0: SETUP
  |  - Validate config.py
  |  - Check output directories exist
  |  - If --dry-run: test each enabled source, report, exit
  |
  Phase 1: COLLECT
  |  - For each enabled source in config.SOURCE_REGISTRY:
  |    - Instantiate collector
  |    - collector.run() -> raw/{name}.csv + raw/{name}.meta.json
  |    - Log: source, record count, time, errors
  |  - All collectors independent (no interdependencies)
  |
  Phase 2: LITERATURE MINING
  |  - Load compound names from all Phase 1 raw CSVs -> build NER dictionary
  |  - Run literature_miner with dynamic dictionary
  |  - Output: raw/literature_miner.csv + raw/literature_miner.meta.json
  |
  Phase 3: STANDARDIZE
  |  - Load all raw/*.csv
  |  - Name resolution (for records without SMILES)
  |  - RDKit standardization pipeline
  |  - Inclusion/exclusion filtering
  |  - InChIKey deduplication
  |  - Evidence tier assignment
  |  - Output: magnolia_bbb_database.csv, magnolia_bbb_provenance.csv, magnolia_bbb_rejected.csv
  |
  Phase 4: ENRICH
  |  - RDKit descriptors
  |  - NP Classifier (COCONUT data -> API fallback -> heuristic fallback)
  |  - Drug-likeness (Lipinski, Veber)
  |  - Update magnolia_bbb_database.csv with enrichment columns
  |
  Phase 5: VALIDATE
  |  - Must-have compound check (13 compounds)
  |  - Atlas comparison (InChIKey-based)
  |  - PRISMA flow data
  |  - Per-source contribution stats
  |  - Evidence tier distribution
  |  - Output: validation_report.json
  |
  Phase 6: EXPORT
  |  - Write magnolia_bbb_species.csv
  |  - Write build_manifest.json
  |  - Write prisma_flow.json
  |  - Print summary to stdout
```

---

## V1 Test Results (for reference)

Collectors that ran successfully against live sources:
- LOTUS/Wikidata: 1,198 compound-species pairs
- PubChem (name-based, to be replaced): 90 compounds
- COCONUT (cross-reference): 2,727 matches (2,628 InChIKey + 99 name)
- KNApSAcK: 526 records (names only, no SMILES)

After standardization + dedup: 634 unique compounds
All 13 must-have compounds found.

Cached data:
- COCONUT bulk CSV: 743 MB in .cache/ (reusable)
- Raw CSVs from 4 collectors (will be regenerated)
