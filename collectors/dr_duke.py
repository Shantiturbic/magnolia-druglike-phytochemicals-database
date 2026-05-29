"""Dr. Duke's Phytochemical Database collector (USDA, public domain).

Bulk CSV download from USDA Ag Data Commons, filtered by genus Magnolia.
Contains compound names, activities, plant parts, and concentrations.
No SMILES — structures resolved in Phase 3 (standardize) via PubChem.

Download strategy (2026-05-28):
  1. Try Ag Data Commons direct file download (multiple URLs attempted)
  2. Fall back to phytochem.nal.usda.gov Drupal JSON API
  3. Fall back to web scraping of search results

Evidence tier: BRONZE (ethnobotanical data, names only, no structures).
"""

from __future__ import annotations

import csv
import io
import json
import logging
import os
import tempfile
import urllib.parse
import urllib.request
import zipfile

from bbb_database_stc.collectors.base import BaseCollector, RawCompound
from bbb_database_stc.utils.http import get_text, get_json
from bbb_database_stc.utils.taxonomy import normalize_species
from bbb_database_stc.config import CACHE_DIR, EvidenceTier

log = logging.getLogger(__name__)

DUKE_BULK_URLS = [
    "https://data.nal.usda.gov/system/files/Duke-Source-CSV.zip",
    "https://agdatacommons.nal.usda.gov/ndownloader/articles/24660351/versions/1",
]

DUKE_JSONAPI_BASE = "https://phytochem.nal.usda.gov/jsonapi/node/plant"


class DrDukeCollector(BaseCollector):
    name = "dr_duke"
    description = "Dr. Duke's Phytochemical DB (USDA): public domain ethnobotany"

    def collect(self) -> list[RawCompound]:
        try:
            log.info("Attempting Dr. Duke's bulk CSV download...")
            records = self._download_bulk()
            if records:
                log.info("Dr. Duke bulk download: %d records", len(records))
                return records
        except Exception as e:
            log.warning("Bulk download failed: %s", e)

        log.info("Trying Drupal JSON API fallback...")
        try:
            records = self._search_drupal_api()
            if records:
                log.info("Dr. Duke Drupal API: %d records", len(records))
                return records
        except Exception as e:
            log.warning("Drupal API failed: %s", e)

        log.info("Trying web scrape fallback...")
        records = self._search_web()
        log.info("Dr. Duke total: %d records", len(records))
        return records

    def _download_bulk(self) -> list[RawCompound]:
        records: list[RawCompound] = []
        seen: set[str] = set()

        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        zip_path = CACHE_DIR / "duke_source_csv.zip"

        if not (zip_path.exists() and zip_path.stat().st_size > 100_000):
            downloaded = False
            for url in DUKE_BULK_URLS:
                try:
                    log.info("Trying %s...", url)
                    req = urllib.request.Request(
                        url,
                        headers={"User-Agent": "BBB-MagnoliaDB/2.0 (thesis research)"},
                    )
                    with urllib.request.urlopen(req, timeout=120) as resp:
                        content_type = resp.headers.get("Content-Type", "")
                        if "html" in content_type.lower():
                            log.warning("Got HTML instead of ZIP from %s, skipping", url)
                            continue
                        with open(zip_path, "wb") as f:
                            while True:
                                chunk = resp.read(1024 * 1024)
                                if not chunk:
                                    break
                                f.write(chunk)
                    if zip_path.stat().st_size > 100_000:
                        downloaded = True
                        log.info("Downloaded: %.1f MB from %s", zip_path.stat().st_size / 1e6, url)
                        break
                    else:
                        log.warning("Download too small (%.0f bytes), trying next URL", zip_path.stat().st_size)
                        zip_path.unlink(missing_ok=True)
                except Exception as e:
                    log.warning("Download from %s failed: %s", url, e)
                    zip_path.unlink(missing_ok=True)

            if not downloaded:
                raise RuntimeError("All bulk download URLs failed")
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

    def _search_drupal_api(self) -> list[RawCompound]:
        """Use the Drupal JSON API at phytochem.nal.usda.gov to find Magnolia compounds."""
        records: list[RawCompound] = []
        seen: set[str] = set()

        import time
        search_terms = [
            "Magnolia officinalis", "Magnolia grandiflora",
            "Magnolia virginiana", "Magnolia obovata",
            "Magnolia liliiflora", "Magnolia biondii",
            "Magnolia denudata", "Magnolia kobus",
            "Magnolia acuminata", "Magnolia sieboldii",
            "Magnolia champaca",
        ]

        for term in search_terms:
            try:
                time.sleep(3.0)
                url = f"https://phytochem.nal.usda.gov/phytochem/search/list/plants?type=plant&q={urllib.parse.quote(term)}"
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "BBB-MagnoliaDB/2.0 (thesis research)",
                        "Accept": "application/json, text/html",
                    },
                )
                with urllib.request.urlopen(req, timeout=60) as resp:
                    raw = resp.read().decode("utf-8", errors="replace")

                try:
                    data = json.loads(raw)
                    if isinstance(data, list):
                        for item in data:
                            chem = item.get("chemical", item.get("CHEMICAL", ""))
                            if not chem:
                                continue
                            pair_key = f"{chem}:{term}"
                            if pair_key in seen:
                                continue
                            seen.add(pair_key)
                            records.append(RawCompound(
                                compound_name=chem,
                                source_db="DrDuke",
                                species=normalize_species(term),
                                plant_part=item.get("part", ""),
                                evidence_tier=EvidenceTier.BRONZE.value,
                                query_term=f"drupal_api={term}",
                                query_date=self._query_date,
                            ))
                    log.info("  '%s': %d new compounds", term, len([k for k in seen if term in k]))
                except json.JSONDecodeError:
                    log.warning("  '%s': response is HTML, not JSON — skipping", term)

            except Exception as e:
                log.warning("Dr. Duke Drupal API search '%s' failed: %s", term, e)

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
