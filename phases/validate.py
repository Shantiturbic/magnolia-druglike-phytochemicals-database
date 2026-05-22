"""Phase 5: Validation — must-have compounds, PRISMA flow, atlas comparison.

Checks:
  1. Must-have compound benchmark (13 signature Magnolia compounds by InChIKey)
  2. Per-source contribution statistics
  3. Evidence tier distribution
  4. PRISMA flow numbers (for thesis figure)
  5. Old atlas comparison (InChIKey-based, not SMILES)
"""

from __future__ import annotations

import csv
import json
import logging
from collections import Counter, defaultdict
from pathlib import Path

from bbb_database_stc.config import (
    OUTPUT_DIR, RAW_DIR, MUST_HAVE_COMPOUNDS, EvidenceTier,
)

log = logging.getLogger(__name__)

ARCHIVE_DIR = OUTPUT_DIR.parent.parent.parent / "archive"


def _load_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _count_raw_records() -> dict[str, int]:
    counts: dict[str, int] = {}
    for csv_path in sorted(RAW_DIR.glob("*.csv")):
        try:
            with open(csv_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                counts[csv_path.stem] = sum(1 for _ in reader)
        except Exception:
            counts[csv_path.stem] = 0
    return counts


def run(output_dir: Path | None = None) -> dict:
    output_dir = output_dir or OUTPUT_DIR
    db_path = output_dir / "magnolia_bbb_database.csv"
    prov_path = output_dir / "magnolia_bbb_provenance.csv"
    rej_path = output_dir / "magnolia_bbb_rejected.csv"

    bbb = _load_csv(db_path)
    prov = _load_csv(prov_path)
    rejected = _load_csv(rej_path)

    if not bbb:
        log.error("Database not found or empty: %s", db_path)
        return {"valid": False, "error": "no database"}

    log.info("=== Phase 5: Validation ===")
    result: dict = {"valid": True}

    # ── 1. Must-have compound check (by InChIKey prefix) ──
    bbb_ik_prefixes = set()
    bbb_names = set()
    for row in bbb:
        ik = row.get("inchikey", "")
        if ik and len(ik) >= 14:
            bbb_ik_prefixes.add(ik[:14])
        for name in row.get("common_names", "").lower().split("|"):
            bbb_names.add(name.strip())

    must_have_results = {}
    missing_must_have = []
    for compound_name, ik_prefix in MUST_HAVE_COMPOUNDS.items():
        found_ik = ik_prefix in bbb_ik_prefixes
        found_name = compound_name.lower() in bbb_names
        found = found_ik or found_name
        must_have_results[compound_name] = {
            "found": found,
            "by_inchikey": found_ik,
            "by_name": found_name,
        }
        if not found:
            missing_must_have.append(compound_name)

    result["must_have"] = {
        "total": len(MUST_HAVE_COMPOUNDS),
        "found": len(MUST_HAVE_COMPOUNDS) - len(missing_must_have),
        "missing": missing_must_have,
        "details": must_have_results,
    }

    log.info("Must-have compounds: %d/%d found",
             len(MUST_HAVE_COMPOUNDS) - len(missing_must_have),
             len(MUST_HAVE_COMPOUNDS))
    if missing_must_have:
        log.warning("Missing must-haves: %s", missing_must_have)
        result["valid"] = False

    # ── 2. Per-source contribution ──
    source_counter: Counter = Counter()
    for row in bbb:
        for src in row.get("source_list", "").split("|"):
            src = src.strip()
            if src:
                source_counter[src] += 1

    raw_counts = _count_raw_records()
    source_stats = {}
    for src, count in source_counter.most_common():
        source_stats[src] = {
            "unique_compounds": count,
            "raw_records": raw_counts.get(src.lower().replace(" ", "_"), 0),
        }

    result["sources"] = source_stats
    log.info("Source contributions:")
    for src, count in source_counter.most_common():
        log.info("  %-25s %5d unique compounds", src, count)

    # ── 3. Evidence tier distribution ──
    tier_counter: Counter = Counter()
    for row in bbb:
        tier_counter[row.get("evidence_tier", "unknown")] += 1

    result["evidence_tiers"] = dict(tier_counter.most_common())
    log.info("Evidence tiers: %s", dict(tier_counter))

    # ── 4. PRISMA flow ──
    total_raw = sum(raw_counts.values())
    prisma = {
        "identification": {
            "sources_screened": len(raw_counts),
            "records_identified": total_raw,
            "per_source": raw_counts,
        },
        "screening": {
            "records_after_merge": len(prov),
            "duplicates_removed": total_raw - len(prov) if total_raw > len(prov) else 0,
        },
        "eligibility": {
            "records_assessed": len(prov),
            "excluded": len(rejected),
            "exclusion_reasons": dict(Counter(
                r.get("rejection_reason", "unknown") for r in rejected
            )),
        },
        "included": {
            "unique_compounds": len(bbb),
        },
    }
    result["prisma"] = prisma
    log.info("PRISMA: %d identified → %d screened → %d excluded → %d included",
             total_raw, len(prov), len(rejected), len(bbb))

    # ── 5. Atlas comparison ──
    atlas_path = ARCHIVE_DIR / "magnolia_chemical_atlas.csv"
    old_atlas = _load_csv(atlas_path)
    if old_atlas:
        old_ik_prefixes: set[str] = set()
        for row in old_atlas:
            ik = row.get("InChIKey", row.get("inchikey", ""))
            if ik and len(ik) >= 14:
                old_ik_prefixes.add(ik[:14])

        overlap = bbb_ik_prefixes & old_ik_prefixes
        only_old = old_ik_prefixes - bbb_ik_prefixes
        only_new = bbb_ik_prefixes - old_ik_prefixes

        result["atlas_comparison"] = {
            "old_atlas_total": len(old_atlas),
            "old_atlas_with_inchikey": len(old_ik_prefixes),
            "overlap": len(overlap),
            "only_in_old": len(only_old),
            "only_in_new": len(only_new),
            "coverage_pct": round(len(overlap) / len(old_ik_prefixes) * 100, 1)
            if old_ik_prefixes else 0,
        }
        log.info("Atlas comparison: %d overlap, %d only-old, %d new",
                 len(overlap), len(only_old), len(only_new))
    else:
        log.info("Old atlas not found at %s — skipping comparison", atlas_path)

    # ── 6. Basic sanity checks ──
    if len(bbb) < 100:
        log.warning("Suspiciously few compounds: %d", len(bbb))
        result["valid"] = False

    smiles_count = sum(1 for r in bbb if r.get("canonical_smiles"))
    if smiles_count < len(bbb) * 0.9:
        log.warning("%.0f%% of compounds lack SMILES",
                    (1 - smiles_count / len(bbb)) * 100)

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = run()
    print(json.dumps(result, indent=2, default=str))
