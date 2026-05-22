"""BBB Database STC: Master build orchestrator.

Usage:
    cd pipeline/data_prep
    python -m bbb_database_stc.build                         # full build
    python -m bbb_database_stc.build --phase collect          # collection only
    python -m bbb_database_stc.build --phase standardize      # standardize only
    python -m bbb_database_stc.build --phase enrich           # enrich only
    python -m bbb_database_stc.build --phase validate         # validate only
    python -m bbb_database_stc.build --phase export           # export only
    python -m bbb_database_stc.build --dry-run                # check source availability
    python -m bbb_database_stc.build --only lotus_wikidata    # single collector
    python -m bbb_database_stc.build --no-llm                 # skip literature LLM
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from bbb_database_stc.config import SOURCE_REGISTRY, OUTPUT_DIR, RAW_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

COLLECTOR_CLASSES = {
    "lotus_wikidata": "bbb_database_stc.collectors.lotus_wikidata:LOTUSCollector",
    "coconut": "bbb_database_stc.collectors.coconut:COCONUTCollector",
    "knapsack": "bbb_database_stc.collectors.knapsack:KNApSAcKCollector",
    "pubchem_taxonomy": "bbb_database_stc.collectors.pubchem_taxonomy:PubChemTaxonomyCollector",
    "chembl_magnolia": "bbb_database_stc.collectors.chembl_magnolia:ChEMBLMagnoliaCollector",
    "npatlas": "bbb_database_stc.collectors.npatlas:NPAtlasCollector",
    "npass": "bbb_database_stc.collectors.npass:NPASSCollector",
    "dr_duke": "bbb_database_stc.collectors.dr_duke:DrDukeCollector",
    "literature_miner": "bbb_database_stc.collectors.literature_miner:LiteratureMinerCollector",
}


def _import_collector(dotpath: str):
    module_path, class_name = dotpath.rsplit(":", 1)
    import importlib
    mod = importlib.import_module(module_path)
    return getattr(mod, class_name)


def dry_run():
    """Check that all enabled sources are reachable."""
    import urllib.request
    import urllib.error

    log.info("=== DRY RUN: checking source availability ===")
    results = {}

    for name, sc in SOURCE_REGISTRY.items():
        if not sc.enabled:
            results[name] = {"status": "disabled"}
            continue

        try:
            req = urllib.request.Request(
                sc.url,
                method="HEAD",
                headers={"User-Agent": "BBB-MagnoliaDB/2.0 (dry-run)"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                results[name] = {"status": "ok", "http": resp.status}
                log.info("  %-20s OK (%d)", name, resp.status)
        except urllib.error.HTTPError as e:
            results[name] = {"status": "http_error", "http": e.code}
            log.warning("  %-20s HTTP %d", name, e.code)
        except Exception as e:
            results[name] = {"status": "error", "error": str(e)}
            log.warning("  %-20s FAIL: %s", name, e)

    ok = sum(1 for v in results.values() if v["status"] == "ok")
    total_enabled = sum(1 for v in results.values() if v["status"] != "disabled")
    log.info("Dry run: %d/%d enabled sources reachable", ok, total_enabled)
    return results


def phase_collect(
    collector_names: list[str] | None = None,
    use_llm: bool = True,
) -> dict[str, dict]:
    log.info("=" * 60)
    log.info("  PHASE 1+2: COLLECTION")
    log.info("=" * 60)

    enabled = {
        name: path for name, path in COLLECTOR_CLASSES.items()
        if SOURCE_REGISTRY.get(name, None) and SOURCE_REGISTRY[name].enabled
    }

    if collector_names:
        enabled = {k: v for k, v in enabled.items() if k in collector_names}
        if not enabled:
            log.error("No matching enabled collectors for: %s", collector_names)
            return {}

    results = {}
    for name, dotpath in enabled.items():
        try:
            cls = _import_collector(dotpath)
            if name == "literature_miner":
                collector = cls(use_llm=use_llm)
            else:
                collector = cls()
            log.info("\n>>> [%s] %s", name, collector.description)
            path = collector.run()
            with open(path) as f:
                count = sum(1 for _ in f) - 1
            results[name] = {"status": "ok", "records": count, "path": str(path)}
        except Exception as e:
            log.error("[%s] FAILED: %s", name, e)
            results[name] = {"status": "error", "error": str(e)}

    log.info("\n" + "-" * 50)
    log.info("  COLLECTION SUMMARY")
    log.info("-" * 50)
    total = 0
    for name, info in results.items():
        if info["status"] == "ok":
            log.info("  %-25s %5d records", name, info["records"])
            total += info["records"]
        else:
            log.info("  %-25s FAILED: %s", name, info.get("error", ""))
    log.info("  %-25s %5d total", "TOTAL", total)

    return results


def phase_standardize() -> dict:
    log.info("\n" + "=" * 60)
    log.info("  PHASE 3: STANDARDIZE & DEDUPLICATE")
    log.info("=" * 60)

    from bbb_database_stc.phases.standardize import run
    return run()


def phase_enrich() -> dict:
    log.info("\n" + "=" * 60)
    log.info("  PHASE 4: ENRICHMENT")
    log.info("=" * 60)

    from bbb_database_stc.phases.enrich import run
    return run()


def phase_validate() -> dict:
    log.info("\n" + "=" * 60)
    log.info("  PHASE 5: VALIDATION")
    log.info("=" * 60)

    from bbb_database_stc.phases.validate import run
    return run()


def phase_export(validation_result: dict | None = None, elapsed: float = 0.0) -> dict:
    log.info("\n" + "=" * 60)
    log.info("  PHASE 6: EXPORT")
    log.info("=" * 60)

    from bbb_database_stc.phases.export import run
    return run(validation_result=validation_result, build_elapsed=elapsed)


def main():
    parser = argparse.ArgumentParser(
        description="BBB Database STC: Systematic Phytochemical Database Builder",
    )
    parser.add_argument(
        "--phase",
        choices=["collect", "standardize", "enrich", "validate", "export", "all"],
        default="all",
    )
    parser.add_argument("--only", nargs="*", help="Run only specific collectors")
    parser.add_argument("--no-llm", action="store_true", help="Skip literature LLM extraction")
    parser.add_argument("--dry-run", action="store_true", help="Check source availability only")
    args = parser.parse_args()

    start = time.time()

    log.info("=" * 60)
    log.info("  BBB DATABASE STC")
    log.info("  Systematic Phytochemical Database for Genus Magnolia")
    log.info("=" * 60)
    log.info("  Phase:    %s", args.phase)
    log.info("  Dry run:  %s", args.dry_run)
    if args.only:
        log.info("  Only:     %s", ", ".join(args.only))
    log.info("")

    if args.dry_run:
        dry_run()
        return

    validation_result = None

    if args.phase in ("collect", "all"):
        phase_collect(collector_names=args.only, use_llm=not args.no_llm)

    if args.phase in ("standardize", "all"):
        phase_standardize()

    if args.phase in ("enrich", "all"):
        phase_enrich()

    if args.phase in ("validate", "all"):
        validation_result = phase_validate()

    if args.phase in ("export", "all"):
        elapsed = time.time() - start
        phase_export(validation_result=validation_result, elapsed=elapsed)

    elapsed = time.time() - start
    log.info("\n" + "=" * 60)
    log.info("  BUILD COMPLETE in %.1f minutes", elapsed / 60)
    log.info("=" * 60)


if __name__ == "__main__":
    main()
