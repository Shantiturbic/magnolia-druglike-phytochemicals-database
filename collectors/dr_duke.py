"""Dr. Duke's Phytochemical Database collector (USDA, public domain).

Bulk CSV download from USDA Ag Data Commons, filtered by genus Magnolia.
Contains compound names, activities, plant parts, and concentrations.
No SMILES — structures resolved in Phase 3 (standardize) via PubChem.

Evidence tier: BRONZE (ethnobotanical data, names only, no structures).
"""

from __future__ import annotations

import csv
import io
import logging
import os
import tempfile
import urllib.request
import zipfile

from bbb_database_stc.collectors.base import BaseCollector, RawCompound
from bbb_database_stc.utils.http import get_text
from bbb_database_stc.utils.taxonomy import normalize_species
from bbb_database_stc.config import CACHE_DIR, EvidenceTier

log = logging.getLogger(__name__)

DUKE_BULK_URL = "https://data.nal.usda.gov/system/files/Duke-Source-CSV.zip"


class DrDukeCollector(BaseCollector):
    name = "dr_duke"
    description = "Dr. Duke's Phytochemical DB (USDA): public domain ethnobotany"

    def collect(self) -> list[RawCompound]:
        try:
            log.info("Downloading Dr. Duke's bulk CSV bundle...")
            records = self._download_bulk()
        except Exception as e:
            log.warning("Bulk download failed: %s. Trying web fallback...", e)
            records = self._search_web()

        log.info("Dr. Duke total: %d records", len(records))
        return records

    def _download_bulk(self) -> list[RawCompound]:
        records: list[RawCompound] = []
        seen: set[str] = set()

        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        zip_path = CACHE_DIR / "duke_source_csv.zip"

        if not (zip_path.exists() and zip_path.stat().st_size > 100_000):
            log.info("Downloading %s...", DUKE_BULK_URL)
            req = urllib.request.Request(
                DUKE_BULK_URL,
                headers={"User-Agent": "BBB-MagnoliaDB/2.0 (thesis research)"},
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                with open(zip_path, "wb") as f:
                    while True:
                        chunk = resp.read(1024 * 1024)
                        if not chunk:
                            break
                        f.write(chunk)
            log.info("Downloaded: %.1f MB", zip_path.stat().st_size / 1e6)
        else:
            log.info("Using cached Dr. Duke ZIP: %.1f MB", zip_path.stat().st_size / 1e6)

        with zipfile.ZipFile(zip_path, "r") as zf:
            csv_files = [n for n in zf.namelist() if n.endswith(".csv")]
            log.info("ZIP contains: %s", csv_files)

            for csv_name in csv_files:
                with zf.open(csv_name) as cf:
                    text = cf.read().decode("utf-8", errors="replace")
                    reader = csv.DictReader(io.StringIO(text))
                    for row in reader:
                        genus = row.get("GENUS", row.get("Genus", "")).strip()
                        plant = row.get("PLANT", row.get("Plant", "")).strip()

                        is_magnolia = (
                            genus.lower() == "magnolia"
                            or "magnolia" in plant.lower()
                        )
                        if not is_magnolia:
                            continue

                        chemical = row.get("CHEMICAL", row.get("Chemical", "")).strip()
                        if not chemical:
                            continue

                        sp = row.get("SPECIES", row.get("Species", "")).strip()
                        if sp:
                            species_name = f"Magnolia {sp.lower()}"
                        else:
                            species_name = "Magnolia sp."

                        part = row.get("PART", row.get("Part", "")).strip()
                        activity = row.get("ACTIVITY", row.get("Activity", "")).strip()
                        conc = row.get("CONCENTRATION", row.get("Concentration", "")).strip()

                        pair_key = f"{chemical}:{species_name}:{part}"
                        if pair_key in seen:
                            continue
                        seen.add(pair_key)

                        extra = {}
                        if activity:
                            extra["activity"] = activity
                        if conc:
                            extra["concentration"] = conc

                        records.append(RawCompound(
                            compound_name=chemical,
                            source_db="DrDuke",
                            source_id="",
                            species=normalize_species(species_name),
                            plant_part=part,
                            evidence_tier=EvidenceTier.BRONZE.value,
                            query_term="genus=Magnolia",
                            query_date=self._query_date,
                            extra=extra,
                        ))

        return records

    def _search_web(self) -> list[RawCompound]:
        records: list[RawCompound] = []
        search_terms = [
            "Magnolia officinalis", "Magnolia grandiflora",
            "Magnolia virginiana", "Magnolia obovata",
        ]

        for term in search_terms:
            try:
                html = get_text(
                    "https://phytochem.nal.usda.gov/phytochem/plants/list",
                    params={"q": term},
                    delay=3.0,
                    timeout=60,
                )
                import re
                compounds = re.findall(
                    r'class="chemical-name"[^>]*>([^<]+)<', html
                )
                for name in compounds:
                    name = name.strip()
                    if name:
                        records.append(RawCompound(
                            compound_name=name,
                            source_db="DrDuke",
                            species=term,
                            evidence_tier=EvidenceTier.PROVISIONAL.value,
                            query_term=f"web_search={term}",
                            query_date=self._query_date,
                        ))
            except Exception as e:
                log.warning("Dr. Duke web search '%s' failed: %s", term, e)

        return records


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    collector = DrDukeCollector()
    path = collector.run()
    print(f"Output: {path}")
