"""Systematic compound class annotation via NPClassifier REST API.

Classifies all compounds in magnolia_bbb_database.csv using the UCSD
NPClassifier (https://npclassifier.ucsd.edu/) REST endpoint.

Produces three new columns per compound:
  - npc_pathway      (e.g., "Terpenoids", "Alkaloids")
  - npc_superclass   (e.g., "Sesquiterpenoids", "Lignans")
  - npc_class        (e.g., "Germacrane sesquiterpenoids")

Also records:
  - npc_isglycoside  (boolean flag from NPClassifier)

Design decisions:
  - Uses existing compound_class/compound_superclass/np_pathway columns as-is
    (does NOT overwrite them). The npc_* columns are authoritative NPClassifier
    output; the old columns are heuristic/curated.
  - Saves progress incrementally to a checkpoint JSON so the run can be
    resumed after interruption.
  - Rate-limits requests to ~3/s to be respectful of the public API.
  - Compounds whose SMILES fail classification get empty npc_* fields.
  - Multi-label results (e.g., two pathways) are pipe-delimited: "A|B".

Usage:
    python phases/classify_compounds.py                  # full run
    python phases/classify_compounds.py --dry-run        # test with 10 compounds
    python phases/classify_compounds.py --resume         # resume from checkpoint
    python phases/classify_compounds.py --force          # ignore checkpoint, redo all
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:
    print("ERROR: 'requests' package required. Install with: pip install requests")
    sys.exit(1)

log = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
DB_PATH = DATA_DIR / "magnolia_bbb_database.csv"
CHECKPOINT_PATH = DATA_DIR / "npc_classification_checkpoint.json"

# ── NPClassifier API ──────────────────────────────────────────────────────
NPC_URL = "https://npclassifier.ucsd.edu/classify"
REQUEST_TIMEOUT = 60  # seconds
DELAY_BETWEEN_REQUESTS = 0.35  # ~2.8 req/s, conservative for public API
MAX_RETRIES = 3
RETRY_BACKOFF = 5  # seconds base; doubles each retry

# ── Output columns ────────────────────────────────────────────────────────
NPC_COLUMNS = ["npc_pathway", "npc_superclass", "npc_class", "npc_isglycoside"]


def classify_smiles(smiles: str, session: requests.Session) -> dict[str, str]:
    """Query NPClassifier for a single SMILES string.

    Returns a dict with keys: npc_pathway, npc_superclass, npc_class, npc_isglycoside.
    On failure, all values are empty strings.
    """
    if not smiles or not smiles.strip():
        return {col: "" for col in NPC_COLUMNS}

    for attempt in range(MAX_RETRIES):
        try:
            resp = session.get(
                NPC_URL,
                params={"smiles": smiles},
                timeout=REQUEST_TIMEOUT,
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "npc_pathway": "|".join(data.get("pathway_results", [])),
                    "npc_superclass": "|".join(data.get("superclass_results", [])),
                    "npc_class": "|".join(data.get("class_results", [])),
                    "npc_isglycoside": str(data.get("isglycoside", False)),
                }
            elif resp.status_code == 500:
                # Invalid SMILES or server-side parse error — not retryable
                log.warning("NPClassifier 500 for SMILES: %.60s (invalid?)", smiles)
                return {col: "" for col in NPC_COLUMNS}
            elif resp.status_code == 429:
                # Rate limited
                wait = RETRY_BACKOFF * (2 ** attempt)
                log.warning("Rate limited (429). Waiting %ds...", wait)
                time.sleep(wait)
                continue
            else:
                log.warning(
                    "NPClassifier HTTP %d for SMILES: %.60s (attempt %d/%d)",
                    resp.status_code, smiles, attempt + 1, MAX_RETRIES,
                )
        except requests.exceptions.Timeout:
            log.warning("Timeout for SMILES: %.60s (attempt %d/%d)", smiles, attempt + 1, MAX_RETRIES)
        except requests.exceptions.ConnectionError:
            wait = RETRY_BACKOFF * (2 ** attempt)
            log.warning("Connection error. Waiting %ds...", wait)
            time.sleep(wait)
        except (requests.exceptions.RequestException, json.JSONDecodeError) as exc:
            log.warning("Request error for SMILES %.60s: %s", smiles, exc)

        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_BACKOFF * (2 ** attempt))

    log.error("Failed after %d retries for SMILES: %.60s", MAX_RETRIES, smiles)
    return {col: "" for col in NPC_COLUMNS}


def load_checkpoint() -> dict[str, dict[str, str]]:
    """Load classification checkpoint (InChIKey -> NPC results)."""
    if CHECKPOINT_PATH.exists():
        try:
            with open(CHECKPOINT_PATH, encoding="utf-8") as f:
                data = json.load(f)
            log.info("Loaded checkpoint with %d entries", len(data))
            return data
        except (json.JSONDecodeError, IOError) as exc:
            log.warning("Corrupt checkpoint file, starting fresh: %s", exc)
    return {}


def save_checkpoint(checkpoint: dict[str, dict[str, str]]) -> None:
    """Save classification checkpoint atomically."""
    tmp = CHECKPOINT_PATH.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, ensure_ascii=False)
    tmp.replace(CHECKPOINT_PATH)


def run(
    dry_run: bool = False,
    resume: bool = True,
    force: bool = False,
    batch_size: int = 50,
) -> dict[str, Any]:
    """Classify all compounds and write updated CSV.

    Args:
        dry_run: Only process first 10 compounds (for testing).
        resume: Use checkpoint to skip already-classified compounds.
        force: Ignore checkpoint and re-classify everything.
        batch_size: Save checkpoint every N compounds.

    Returns:
        Summary statistics dict.
    """
    if not DB_PATH.exists():
        log.error("Database not found: %s", DB_PATH)
        return {"error": f"File not found: {DB_PATH}"}

    # Load database
    with open(DB_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        original_fields = list(reader.fieldnames or [])
        rows = list(reader)
    log.info("Loaded %d compounds from %s", len(rows), DB_PATH.name)

    # Build output fieldnames: add NPC columns after np_pathway if not present
    output_fields = list(original_fields)
    npc_to_add = [col for col in NPC_COLUMNS if col not in output_fields]
    if npc_to_add:
        if "np_pathway" in output_fields:
            insert_pos = output_fields.index("np_pathway") + 1
            for i, col in enumerate(npc_to_add):
                output_fields.insert(insert_pos + i, col)
        else:
            output_fields.extend(npc_to_add)

    # Load or reset checkpoint
    if force:
        checkpoint: dict[str, dict[str, str]] = {}
        log.info("Force mode: ignoring checkpoint")
    elif resume:
        checkpoint = load_checkpoint()
    else:
        checkpoint = {}

    # Determine which compounds need classification
    if dry_run:
        rows_to_process = rows[:10]
        log.info("DRY RUN: processing first 10 compounds only")
    else:
        rows_to_process = rows

    session = requests.Session()
    session.headers.update({"User-Agent": "Magnolia-BBB-Classifier/1.0 (thesis research)"})

    classified_count = 0
    skipped_count = 0
    failed_count = 0
    total = len(rows_to_process)

    start_time = time.time()

    for i, row in enumerate(rows_to_process):
        inchikey = row.get("inchikey", "")
        smiles = row.get("canonical_smiles", "")

        # Check checkpoint
        if inchikey in checkpoint:
            cached = checkpoint[inchikey]
            for col in NPC_COLUMNS:
                row[col] = cached.get(col, "")
            skipped_count += 1
            continue

        # Classify
        result = classify_smiles(smiles, session)
        for col in NPC_COLUMNS:
            row[col] = result.get(col, "")

        # Track success/failure
        if result.get("npc_pathway"):
            classified_count += 1
        else:
            failed_count += 1

        # Cache result
        if inchikey:
            checkpoint[inchikey] = result

        # Progress logging
        done = i + 1
        if done % 25 == 0 or done == total:
            elapsed = time.time() - start_time
            rate = done / elapsed if elapsed > 0 else 0
            eta_s = (total - done) / rate if rate > 0 else 0
            eta_min = eta_s / 60
            log.info(
                "  [%d/%d] classified=%d skipped=%d failed=%d (%.1f/s, ETA: %.1f min)",
                done, total, classified_count, skipped_count, failed_count,
                rate, eta_min,
            )

        # Save checkpoint periodically
        if done % batch_size == 0:
            save_checkpoint(checkpoint)
            log.info("  Checkpoint saved (%d entries)", len(checkpoint))

        # Rate limit
        time.sleep(DELAY_BETWEEN_REQUESTS)

    # For compounds not in rows_to_process (if dry_run), ensure NPC columns exist
    if dry_run:
        for row in rows[10:]:
            inchikey = row.get("inchikey", "")
            if inchikey in checkpoint:
                cached = checkpoint[inchikey]
                for col in NPC_COLUMNS:
                    row[col] = cached.get(col, "")
            else:
                for col in NPC_COLUMNS:
                    row.setdefault(col, "")

    # Final checkpoint save
    save_checkpoint(checkpoint)

    # Write updated CSV
    output_path = DB_PATH if not dry_run else DATA_DIR / "magnolia_bbb_database_npc_test.csv"
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=output_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    elapsed_total = time.time() - start_time

    result_summary = {
        "total_compounds": len(rows),
        "processed": total,
        "classified_new": classified_count,
        "skipped_from_checkpoint": skipped_count,
        "failed": failed_count,
        "success_rate": f"{(classified_count / max(classified_count + failed_count, 1)) * 100:.1f}%",
        "elapsed_seconds": round(elapsed_total, 1),
        "output_file": str(output_path),
        "checkpoint_entries": len(checkpoint),
    }

    log.info("=== Classification complete ===")
    for k, v in result_summary.items():
        log.info("  %s: %s", k, v)

    return result_summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Classify Magnolia compounds using NPClassifier API",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Test with first 10 compounds only; writes to _npc_test.csv",
    )
    parser.add_argument(
        "--resume", action="store_true", default=True,
        help="Resume from checkpoint (default: true)",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Ignore checkpoint and re-classify all compounds",
    )
    parser.add_argument(
        "--batch-size", type=int, default=50,
        help="Save checkpoint every N compounds (default: 50)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-5s %(message)s",
        datefmt="%H:%M:%S",
    )

    result = run(
        dry_run=args.dry_run,
        resume=args.resume,
        force=args.force,
        batch_size=args.batch_size,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
