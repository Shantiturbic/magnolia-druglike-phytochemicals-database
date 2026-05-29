"""NPASS 3.0 collector: Natural Product Activity & Species Source.

Downloads three files from NPASS 3.0 (2026 release):
  1. Species info (taxonomy) — to identify Magnolia/Michelia/Talauma org IDs
  2. Species-compound pairs — to get compound IDs for those organisms
  3. Structure file — SMILES/InChI/InChIKey for each compound

Evidence tier: GOLD (curated NP database with species-level attribution + PMID refs).

Reference: NPASS database update 2026, Nucleic Acids Res (2026).
"""

from __future__ import annotations

import csv
import io
import logging

from bbb_database_stc.collectors.base import BaseCollector, RawCompound
from bbb_database_stc.utils.http import get_text
from bbb_database_stc.utils.taxonomy import normalize_species, is_magnolia_genus
from bbb_database_stc.config import EvidenceTier, OLD_GENUS_NAMES

log = logging.getLogger(__name__)

NPASS_BASE = "https://bidd.group/NPASS/downloadFiles"
NPASS_SPECIES_INFO_URL = f"{NPASS_BASE}/NPASS3.0_species_info.txt"
NPASS_SPECIES_PAIRS_URL = f"{NPASS_BASE}/NPASS3.0_naturalproducts_species_pair.txt"
NPASS_STRUCTURES_URL = f"{NPASS_BASE}/NPASS3.0_naturalproducts_structure.txt"

MAGNOLIA_SEARCH_TERMS = (
    ["magnolia", "michelia", "talauma", "manglietia", "liriodendron"]
    + [g.lower() for g in OLD_GENUS_NAMES]
)

FAMILY_ID = "3401"  # NCBI Taxonomy family ID for Magnoliaceae


class NPASSCollector(BaseCollector):
    name = "npass"
    description = "NPASS 3.0: natural product activity and species source (bulk download, 2026 release)"

    def collect(self) -> list[RawCompound]:
        log.info("Phase 1: Downloading NPASS 3.0 species taxonomy...")
        magnolia_org_ids = self._find_magnolia_org_ids()
        if not magnolia_org_ids:
            log.warning("No Magnolia/Magnoliaceae organisms found in NPASS species info")
            return []
        log.info("Found %d Magnolia-family organism IDs", len(magnolia_org_ids))

        log.info("Phase 2: Downloading species-compound pairs...")
        compound_map = self._get_compound_pairs(magnolia_org_ids)
        if not compound_map:
            log.warning("No compound-species pairs found for Magnolia organisms")
            return []
        log.info("Found %d unique compound IDs across %d species",
                 len(compound_map), len(magnolia_org_ids))

        log.info("Phase 3: Downloading structure data...")
        structures = self._get_structures(set(compound_map.keys()))
        log.info("Loaded structures for %d / %d compounds",
                 len(structures), len(compound_map))

        records: list[RawCompound] = []
        for np_id, entries in compound_map.items():
            struct = structures.get(np_id, {})
            smiles = struct.get("smiles", "")
            inchi = struct.get("inchi", "")
            inchikey = struct.get("inchikey", "")

            for entry in entries:
                records.append(RawCompound(
                    compound_name=entry.get("name", ""),
                    canonical_smiles=smiles,
                    inchi=inchi,
                    inchikey=inchikey,
                    source_db="NPASS",
                    source_id=np_id,
                    species=entry["species"],
                    plant_part=entry.get("plant_part", ""),
                    doi=entry.get("doi", ""),
                    evidence_tier=EvidenceTier.GOLD.value,
                    query_term=f"org_id={entry.get('org_id', '')}",
                    query_date=self._query_date,
                ))

        log.info("NPASS 3.0 total: %d records (%d with SMILES, %d with InChIKey)",
                 len(records),
                 sum(1 for r in records if r.canonical_smiles),
                 sum(1 for r in records if r.inchikey))
        return records

    def _find_magnolia_org_ids(self) -> dict[str, str]:
        """Download species_info and find all Magnoliaceae organism IDs."""
        org_ids: dict[str, str] = {}
        try:
            text = get_text(NPASS_SPECIES_INFO_URL, delay=2.0, timeout=180)
            reader = csv.DictReader(io.StringIO(text), delimiter="\t")

            for row in reader:
                org_id = row.get("org_id", "")
                species_name = row.get("org_name", "")
                family_id = row.get("family_tax_id", "")

                if not org_id:
                    continue

                is_match = False

                if family_id == FAMILY_ID:
                    is_match = True
                elif any(term in species_name.lower() for term in MAGNOLIA_SEARCH_TERMS):
                    is_match = True
                elif is_magnolia_genus(species_name):
                    is_match = True

                if is_match:
                    normalized = normalize_species(species_name) if species_name else ""
                    org_ids[org_id] = normalized

        except Exception as e:
            log.error("NPASS species info download failed: %s", e)

        return org_ids

    def _get_compound_pairs(self, org_ids: dict[str, str]) -> dict[str, list[dict]]:
        """Download species-compound pairs and filter for our organism IDs."""
        compound_map: dict[str, list[dict]] = {}
        try:
            text = get_text(NPASS_SPECIES_PAIRS_URL, delay=2.0, timeout=180)
            reader = csv.DictReader(io.StringIO(text), delimiter="\t")

            for row in reader:
                org_id = row.get("org_id", "")
                np_id = row.get("np_id", "")

                if not org_id or not np_id:
                    continue
                if org_id not in org_ids:
                    continue

                species = org_ids[org_id]
                plant_part = row.get("org_isolation_part", "")
                ref_id = row.get("ref_id", "")
                ref_type = row.get("ref_id_type", "")

                doi = ""
                if ref_type == "DOI":
                    doi = ref_id
                elif ref_type == "PMID" and ref_id:
                    doi = f"PMID:{ref_id}"

                entry = {
                    "species": species,
                    "org_id": org_id,
                    "plant_part": plant_part if plant_part != "n.a." else "",
                    "doi": doi if doi != "n.a." else "",
                    "name": "",
                }

                if np_id not in compound_map:
                    compound_map[np_id] = []
                compound_map[np_id].append(entry)

        except Exception as e:
            log.error("NPASS species-compound pairs download failed: %s", e)

        return compound_map

    def _get_structures(self, needed_ids: set[str]) -> dict[str, dict]:
        """Download structure file and extract SMILES/InChI/InChIKey for needed compounds."""
        structures: dict[str, dict] = {}
        try:
            text = get_text(NPASS_STRUCTURES_URL, delay=2.0, timeout=180)
            reader = csv.DictReader(io.StringIO(text), delimiter="\t")

            for row in reader:
                np_id = row.get("np_id", "")
                if np_id not in needed_ids:
                    continue

                structures[np_id] = {
                    "smiles": row.get("SMILES", ""),
                    "inchi": row.get("InChI", ""),
                    "inchikey": row.get("InChIKey", ""),
                }

        except Exception as e:
            log.error("NPASS structure download failed: %s", e)

        return structures


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    collector = NPASSCollector()
    path = collector.run()
    print(f"Output: {path}")
