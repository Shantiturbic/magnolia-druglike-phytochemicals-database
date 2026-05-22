"""NPASS 2.0 collector: Natural Product Activity & Species Source.

Bulk downloads two TSV files from NPASS:
  1. Species-source relationships (filtered for Magnolia)
  2. Compound properties (SMILES lookup)

Evidence tier: GOLD (curated NP database with species-level attribution).
"""

from __future__ import annotations

import csv
import io
import logging

from bbb_database_stc.collectors.base import BaseCollector, RawCompound
from bbb_database_stc.utils.http import get_text
from bbb_database_stc.utils.taxonomy import normalize_species, is_magnolia_genus
from bbb_database_stc.config import EvidenceTier

log = logging.getLogger(__name__)

NPASS_SPECIES_URL = "https://bidd.group/NPASS/downloadFiles/NPASSv2.0_compounds_speciesSource.txt"
NPASS_PROPS_URL = "https://bidd.group/NPASS/downloadFiles/NPASSv2.0_compounds_properties.txt"


class NPASSCollector(BaseCollector):
    name = "npass"
    description = "NPASS 2.0: natural product activity and species source (bulk download)"

    def collect(self) -> list[RawCompound]:
        log.info("Downloading NPASS species-source data...")
        species_data = self._download_species_source()
        if not species_data:
            log.warning("No Magnolia entries in NPASS species-source file")
            return []

        log.info("Found %d Magnolia compound IDs. Downloading properties...",
                 len(species_data))
        smiles_map = self._download_smiles_map()
        log.info("Loaded SMILES for %d NPASS compounds", len(smiles_map))

        records: list[RawCompound] = []
        for npass_id, entries in species_data.items():
            smiles = smiles_map.get(npass_id, "")
            for entry in entries:
                records.append(RawCompound(
                    compound_name=entry["name"],
                    canonical_smiles=smiles,
                    source_db="NPASS",
                    source_id=npass_id,
                    species=entry["species"],
                    evidence_tier=EvidenceTier.GOLD.value,
                    query_term="species_source~magnolia",
                    query_date=self._query_date,
                ))

        log.info("NPASS total: %d records (%d with SMILES)",
                 len(records), sum(1 for r in records if r.canonical_smiles))
        return records

    def _download_species_source(self) -> dict[str, list[dict]]:
        result: dict[str, list[dict]] = {}
        try:
            text = get_text(NPASS_SPECIES_URL, delay=2.0, timeout=120)
            reader = csv.DictReader(io.StringIO(text), delimiter="\t")
            for row in reader:
                species = row.get("species_source", row.get("Species_Source", ""))
                if not species:
                    continue
                if not is_magnolia_genus(species) and "magnolia" not in species.lower():
                    continue

                npass_id = row.get("NPASS_ID", row.get("npass_id", ""))
                name = row.get("compound_name", row.get("Compound_Name", ""))
                if not npass_id:
                    continue

                normalized = normalize_species(species)
                if npass_id not in result:
                    result[npass_id] = []
                result[npass_id].append({"name": name, "species": normalized})

        except Exception as e:
            log.warning("NPASS species-source download failed: %s", e)

        return result

    def _download_smiles_map(self) -> dict[str, str]:
        result: dict[str, str] = {}
        try:
            text = get_text(NPASS_PROPS_URL, delay=2.0, timeout=120)
            reader = csv.DictReader(io.StringIO(text), delimiter="\t")
            for row in reader:
                npass_id = row.get("NPASS_ID", row.get("npass_id", ""))
                smiles = row.get("SMILES", row.get("smiles", ""))
                if npass_id and smiles:
                    result[npass_id] = smiles
        except Exception as e:
            log.warning("NPASS properties download failed: %s", e)

        return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    collector = NPASSCollector()
    path = collector.run()
    print(f"Output: {path}")
