"""Phase 6: Export — final outputs, build manifest, PRISMA flow JSON.

Produces:
  - build_manifest.json   (software versions, source URLs, query dates, counts)
  - prisma_flow.json      (for thesis figure generation)
  - Verifies all expected output files exist
"""

from __future__ import annotations

import csv
import json
import logging
import platform
import sys
import time
from pathlib import Path

from bbb_database_stc.config import OUTPUT_DIR, RAW_DIR, SOURCE_REGISTRY

log = logging.getLogger(__name__)


def _get_rdkit_version() -> str:
    try:
        import rdkit
        return rdkit.__version__
    except ImportError:
        return "not installed"


def _get_python_version() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def _count_csv_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with open(path, encoding="utf-8") as f:
        return sum(1 for _ in csv.DictReader(f))


def _load_meta_files() -> dict[str, dict]:
    metas = {}
    for meta_path in sorted(RAW_DIR.glob("*.meta.json")):
        try:
            with open(meta_path) as f:
                metas[meta_path.stem.replace(".meta", "")] = json.load(f)
        except Exception:
            pass
    return metas


def run(
    output_dir: Path | None = None,
    validation_result: dict | None = None,
    build_elapsed: float = 0.0,
) -> dict:
    output_dir = output_dir or OUTPUT_DIR
    log.info("=== Phase 6: Export ===")

    db_path = output_dir / "magnolia_bbb_database.csv"
    prov_path = output_dir / "magnolia_bbb_provenance.csv"
    rej_path = output_dir / "magnolia_bbb_rejected.csv"

    db_count = _count_csv_rows(db_path)
    prov_count = _count_csv_rows(prov_path)
    rej_count = _count_csv_rows(rej_path)

    metas = _load_meta_files()

    source_info = {}
    for name, sc in SOURCE_REGISTRY.items():
        meta = metas.get(name, {})
        source_info[name] = {
            "enabled": sc.enabled,
            "tier": sc.tier,
            "license": sc.license,
            "url": sc.url,
            "status": meta.get("status", "not_run" if sc.enabled else "disabled"),
            "record_count": meta.get("record_count", 0),
            "query_timestamp": meta.get("timestamp", ""),
            "elapsed_seconds": meta.get("elapsed_seconds", 0),
        }

    manifest = {
        "database": "BBB Database STC",
        "version": "2.0",
        "description": "Systematic phytochemical database for genus Magnolia",
        "build_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "build_elapsed_seconds": round(build_elapsed, 1),
        "environment": {
            "python": _get_python_version(),
            "rdkit": _get_rdkit_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "outputs": {
            "database": {
                "path": db_path.name,
                "unique_compounds": db_count,
            },
            "provenance": {
                "path": prov_path.name,
                "records": prov_count,
            },
            "rejected": {
                "path": rej_path.name,
                "records": rej_count,
            },
        },
        "sources": source_info,
    }

    if validation_result:
        manifest["validation"] = {
            "valid": validation_result.get("valid", False),
            "must_have_found": validation_result.get("must_have", {}).get("found", 0),
            "must_have_total": validation_result.get("must_have", {}).get("total", 0),
            "evidence_tiers": validation_result.get("evidence_tiers", {}),
        }

    manifest_path = output_dir / "build_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, default=str)
    log.info("Wrote %s", manifest_path.name)

    if validation_result and "prisma" in validation_result:
        prisma_path = output_dir / "prisma_flow.json"
        with open(prisma_path, "w") as f:
            json.dump(validation_result["prisma"], f, indent=2, default=str)
        log.info("Wrote %s", prisma_path.name)

    expected = [db_path, prov_path, rej_path, manifest_path]
    missing = [p for p in expected if not p.exists()]
    if missing:
        log.warning("Missing output files: %s", [p.name for p in missing])

    log.info("Export complete: %d compounds, %d provenance records, %d rejected",
             db_count, prov_count, rej_count)
    return {
        "database_compounds": db_count,
        "provenance_records": prov_count,
        "rejected_records": rej_count,
        "manifest": str(manifest_path),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = run()
    print(json.dumps(result, indent=2))
