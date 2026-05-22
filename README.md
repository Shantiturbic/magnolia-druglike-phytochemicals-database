# Magnolia Drug-Like Phytochemicals Database

Systematic phytochemical database for genus *Magnolia* (sensu lato), built entirely from public sources with full provenance tracking.

**738 unique compounds** from 6 databases (LOTUS/Wikidata, COCONUT, KNApSAcK, PubChem, ChEMBL, PubMed/PMC), covering 50 Wikidata taxa + 11 old genera (Michelia, Talauma, Manglietia, etc.) with synonym resolution via POWO.

## Quick Start

```bash
pip install rdkit   # required for standardization
cd /path/to/this/repo
python -m bbb_database_stc.build          # full build
python -m bbb_database_stc.build --phase collect --only knapsack  # single collector
python -m bbb_database_stc.build --dry-run  # check source availability
```

## Outputs (`data/`)

| File | Description |
|------|-------------|
| `magnolia_bbb_database.csv` | 738 unique compounds (deduplicated, standardized) |
| `magnolia_bbb_provenance.csv` | 6,201 compound-source-species records |
| `magnolia_bbb_rejected.csv` | 330 filtered compounds with rejection reasons |
| `build_manifest.json` | Software versions, query dates, reproducibility metadata |
| `raw/*.csv` | Per-collector raw outputs |

## Methodology

See [BBB_DATABASE_STC_METHODOLOGY.md](BBB_DATABASE_STC_METHODOLOGY.md) for the full thesis-grade methodology document.

## License

Data from public databases under their respective licenses (CC0, CC-BY 4.0, public domain). Code is part of an INTEC undergraduate thesis.
