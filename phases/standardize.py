"""Phase 3: Compound resolution, standardization, deduplication, and filtering.

Reads all raw collector CSVs from RAW_DIR, then:
  1. Resolves name-only records (KNApSAcK, Dr. Duke) via PubChem
  2. Standardizes: parse SMILES → sanitize → strip salts → neutralize → canonical
  3. Applies inclusion/exclusion filters (MW, heavy atoms, inorganic, primary metabolites)
  4. Deduplicates by InChIKey connectivity layer (first 14 chars)
  5. Assigns evidence tiers (GOLD/SILVER/BRONZE/PROVISIONAL)

Outputs:
  - magnolia_bbb_database.csv   (one row per unique compound)
  - magnolia_bbb_provenance.csv (one row per compound-source pair)
  - magnolia_bbb_rejected.csv   (filtered compounds with rejection reasons — for PRISMA)
"""

from __future__ import annotations

import csv
import json
import logging
import time
import urllib.parse
from collections import defaultdict
from pathlib import Path
from typing import Optional

from bbb_database_stc.config import (
    RAW_DIR, OUTPUT_DIR, EvidenceTier, SOURCE_REGISTRY,
)
from bbb_database_stc.utils.chem import (
    standardize_smiles, check_inclusion, inchikey_connectivity,
)
from bbb_database_stc.utils.http import get_json
from bbb_database_stc.utils.taxonomy import normalize_species

log = logging.getLogger(__name__)

DB_FIELDS = [
    "inchikey", "inchikey_connectivity", "canonical_smiles", "inchi",
    "iupac_name", "common_names", "molecular_formula", "molecular_weight",
    "evidence_tier", "source_count", "source_list",
    "species_list", "species_count",
    "doi_refs", "reference_count",
]

PROV_FIELDS = [
    "inchikey", "inchikey_connectivity", "source_db", "source_id",
    "species_reported", "species_accepted", "plant_part", "doi",
    "evidence_tier", "query_term", "query_date",
]

REJECTED_FIELDS = [
    "compound_name", "canonical_smiles", "inchikey", "source_db",
    "species", "rejection_reason",
]

GOLD_SOURCES = frozenset({"LOTUS_Wikidata", "KNApSAcK", "NPAtlas", "NPASS"})


def resolve_name_to_smiles(name: str) -> Optional[str]:
    if not name:
        return None
    try:
        encoded = urllib.parse.quote(name)
        url = (
            f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"
            f"{encoded}/property/CanonicalSMILES/JSON"
        )
        data = get_json(url, delay=0.3, timeout=15)
        props = data.get("PropertyTable", {}).get("Properties", [])
        if props:
            p = props[0]
            return (p.get("CanonicalSMILES")
                    or p.get("ConnectivitySMILES")
                    or p.get("SMILES", "")
                    or None)
    except Exception:
        pass
    return None


def load_raw_records() -> list[dict]:
    records = []
    for csv_path in sorted(RAW_DIR.glob("*.csv")):
        try:
            with open(csv_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                count = 0
                for row in reader:
                    row["_source_file"] = csv_path.stem
                    records.append(row)
                    count += 1
                log.info("Loaded %d records from %s", count, csv_path.name)
        except Exception as e:
            log.warning("Failed to load %s: %s", csv_path.name, e)
    return records


def assign_evidence_tier(sources: set[str], doi_count: int) -> str:
    gold_count = sum(1 for s in sources if s in GOLD_SOURCES)
    if gold_count >= 1 and len(sources) >= 2:
        return EvidenceTier.GOLD.value
    if gold_count >= 1:
        return EvidenceTier.GOLD.value
    if len(sources) >= 2 or (len(sources) >= 1 and doi_count >= 1):
        return EvidenceTier.SILVER.value
    if len(sources) >= 1:
        return EvidenceTier.BRONZE.value
    return EvidenceTier.PROVISIONAL.value


def run(
    raw_dir: Path | None = None,
    output_dir: Path | None = None,
) -> dict:
    raw_dir = raw_dir or RAW_DIR
    output_dir = output_dir or OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    log.info("=== Phase 3: Standardize & Deduplicate ===")
    records = load_raw_records()
    if not records:
        log.warning("No raw records found in %s", raw_dir)
        return {"raw": 0, "unique": 0, "rejected": 0, "provenance": 0}

    compounds: dict[str, dict] = {}
    provenance: list[dict] = []
    rejected: list[dict] = []
    resolve_cache: dict[str, Optional[str]] = {}
    stats = {
        "raw": len(records),
        "no_smiles_no_name": 0,
        "unresolvable_name": 0,
        "unparseable_smiles": 0,
        "filtered": 0,
    }

    for rec in records:
        smiles = rec.get("canonical_smiles", "").strip()
        name = rec.get("compound_name", "").strip()

        if not smiles and name:
            if name not in resolve_cache:
                resolve_cache[name] = resolve_name_to_smiles(name)
            smiles = resolve_cache[name] or ""

        if not smiles and not name:
            stats["no_smiles_no_name"] += 1
            continue
        if not smiles:
            stats["unresolvable_name"] += 1
            rejected.append({
                "compound_name": name,
                "canonical_smiles": "",
                "inchikey": "",
                "source_db": rec.get("source_db", ""),
                "species": rec.get("species", ""),
                "rejection_reason": "unresolvable_name",
            })
            continue

        std = standardize_smiles(smiles)
        if std is None:
            stats["unparseable_smiles"] += 1
            rejected.append({
                "compound_name": name,
                "canonical_smiles": smiles,
                "inchikey": "",
                "source_db": rec.get("source_db", ""),
                "species": rec.get("species", ""),
                "rejection_reason": "unparseable_smiles",
            })
            continue

        passes, reason = check_inclusion(std.canonical_smiles, std.inchikey)
        if not passes:
            stats["filtered"] += 1
            rejected.append({
                "compound_name": name,
                "canonical_smiles": std.canonical_smiles,
                "inchikey": std.inchikey,
                "source_db": rec.get("source_db", ""),
                "species": rec.get("species", ""),
                "rejection_reason": reason,
            })
            continue

        ik_conn = inchikey_connectivity(std.inchikey)
        ik = std.inchikey

        species_reported = rec.get("species", "").strip()
        species_accepted = normalize_species(species_reported) if species_reported else ""

        prov_row = {
            "inchikey": ik,
            "inchikey_connectivity": ik_conn,
            "source_db": rec.get("source_db", rec.get("_source_file", "")),
            "source_id": rec.get("source_id", ""),
            "species_reported": species_reported,
            "species_accepted": species_accepted,
            "plant_part": rec.get("plant_part", ""),
            "doi": rec.get("doi", ""),
            "evidence_tier": rec.get("evidence_tier", EvidenceTier.BRONZE.value),
            "query_term": rec.get("query_term", ""),
            "query_date": rec.get("query_date", ""),
        }
        provenance.append(prov_row)

        if ik_conn not in compounds:
            compounds[ik_conn] = {
                "inchikey": ik,
                "inchikey_connectivity": ik_conn,
                "canonical_smiles": std.canonical_smiles,
                "inchi": std.inchi,
                "molecular_formula": std.molecular_formula,
                "molecular_weight": std.molecular_weight,
                "common_names": set(),
                "sources": set(),
                "species": set(),
                "doi_refs": set(),
            }

        entry = compounds[ik_conn]
        if name:
            entry["common_names"].add(name.lower())
        src = rec.get("source_db", rec.get("_source_file", ""))
        if src:
            entry["sources"].add(src)
        if species_accepted and species_accepted != "Magnolia sp.":
            entry["species"].add(species_accepted)
        doi = rec.get("doi", "")
        if doi:
            entry["doi_refs"].add(doi)

    log.info(
        "Standardized: %d unique compounds from %d records "
        "(%d rejected, %d unresolved names, %d unparseable)",
        len(compounds), len(records), len(rejected),
        stats["unresolvable_name"], stats["unparseable_smiles"],
    )

    db_rows = []
    for ik_conn, entry in sorted(compounds.items()):
        tier = assign_evidence_tier(entry["sources"], len(entry["doi_refs"]))
        db_rows.append({
            "inchikey": entry["inchikey"],
            "inchikey_connectivity": ik_conn,
            "canonical_smiles": entry["canonical_smiles"],
            "inchi": entry["inchi"],
            "iupac_name": "",
            "common_names": "|".join(sorted(entry["common_names"])),
            "molecular_formula": entry["molecular_formula"],
            "molecular_weight": entry["molecular_weight"],
            "evidence_tier": tier,
            "source_count": len(entry["sources"]),
            "source_list": "|".join(sorted(entry["sources"])),
            "species_list": "|".join(sorted(entry["species"])),
            "species_count": len(entry["species"]),
            "doi_refs": "|".join(sorted(entry["doi_refs"])),
            "reference_count": len(entry["doi_refs"]),
        })

    rep_ik = {ik_conn: entry["inchikey"] for ik_conn, entry in compounds.items()}
    for prov_row in provenance:
        prov_row["inchikey"] = rep_ik.get(
            prov_row["inchikey_connectivity"], prov_row["inchikey"]
        )

    db_path = output_dir / "magnolia_bbb_database.csv"
    _write_csv(db_rows, db_path, DB_FIELDS)

    prov_path = output_dir / "magnolia_bbb_provenance.csv"
    _write_csv(provenance, prov_path, PROV_FIELDS)

    rej_path = output_dir / "magnolia_bbb_rejected.csv"
    _write_csv(rejected, rej_path, REJECTED_FIELDS)

    result = {
        "raw": len(records),
        "resolved_names": len(resolve_cache),
        "unique": len(db_rows),
        "provenance": len(provenance),
        "rejected": len(rejected),
        "rejection_breakdown": _rejection_breakdown(rejected),
        "evidence_tiers": _tier_breakdown(db_rows),
    }
    log.info("Output: %s (%d compounds)", db_path.name, len(db_rows))
    log.info("Output: %s (%d records)", prov_path.name, len(provenance))
    log.info("Output: %s (%d rejected)", rej_path.name, len(rejected))
    return result


def _write_csv(rows: list[dict], path: Path, fields: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _rejection_breakdown(rejected: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for r in rejected:
        counts[r.get("rejection_reason", "unknown")] += 1
    return dict(counts)


def _tier_breakdown(rows: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for r in rows:
        counts[r.get("evidence_tier", "unknown")] += 1
    return dict(counts)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = run()
    print(json.dumps(result, indent=2))
