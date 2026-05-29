"""NP Atlas collector: curated microbial natural products atlas.

Strategy: Download the full TSV bulk export (36K compounds) and filter locally
for Magnolia-associated organisms (endophytic fungi, bacteria isolated from
Magnolia hosts). The API's basicSearch endpoint is broken (server-side bug:
ignores query parameter), so we bypass it entirely with the bulk download.

NP Atlas is primarily MICROBIAL NPs — plant-derived compounds are rare here.
The value is endophyte chemistry: fungi/bacteria isolated FROM Magnolia species
that produce unique metabolites not synthesized by the plant itself.

Evidence tier: GOLD (curated NP atlas with DOI provenance per compound).

Reference: Lyu et al., 2024, Nucleic Acids Res 53:D691 (NP Atlas 3.0).
"""

from __future__ import annotations

import csv
import io
import logging

from bbb_database_stc.collectors.base import BaseCollector, RawCompound
from bbb_database_stc.utils.http import get_text
from bbb_database_stc.utils.taxonomy import normalize_species
from bbb_database_stc.config import EvidenceTier

log = logging.getLogger(__name__)

NPATLAS_TSV_URL = "https://www.npatlas.org/static/downloads/NPAtlas_download.tsv"

MAGNOLIA_KEYWORDS = [
    "magnolia", "magnoliaceae", "michelia", "talauma",
    "manglietia", "liriodendron",
]


class NPAtlasCollector(BaseCollector):
    name = "npatlas"
    description = "NP Atlas: microbial NP atlas, bulk TSV filtered for Magnolia-associated organisms"

    def collect(self) -> list[RawCompound]:
        log.info("Downloading NP Atlas full TSV (~33 MB)...")
        try:
            text = get_text(NPATLAS_TSV_URL, delay=2.0, timeout=300)
        except Exception as e:
            log.error("NP Atlas download failed: %s", e)
            return []

        log.info("Parsing and filtering for Magnolia-associated entries...")
        records: list[RawCompound] = []
        seen_ids: set[str] = set()

        reader = csv.DictReader(io.StringIO(text), delimiter="\t")
        total_rows = 0
        for row in reader:
            total_rows += 1
            if not self._is_magnolia_associated(row):
                continue

            npaid = row.get("npaid", "")
            if npaid in seen_ids:
                continue
            seen_ids.add(npaid)

            smiles = row.get("compound_smiles", "")
            if not smiles:
                continue

            genus = row.get("genus", "")
            species = row.get("origin_species", "")
            organism = f"{genus} {species}".strip() if genus else species

            doi = row.get("original_reference_doi", "")
            name = row.get("compound_name", "")
            inchi = row.get("compound_inchi", "")
            inchikey = row.get("compound_inchikey", "")
            mw_str = row.get("compound_molecular_weight", "0")
            formula = row.get("compound_molecular_formula", "")

            try:
                mw = float(mw_str)
            except (ValueError, TypeError):
                mw = 0.0

            records.append(RawCompound(
                compound_name=name,
                canonical_smiles=smiles,
                inchi=inchi,
                inchikey=inchikey,
                molecular_formula=formula,
                molecular_weight=mw,
                source_db="NPAtlas",
                source_id=npaid,
                species=normalize_species(organism) if organism else "",
                doi=doi,
                evidence_tier=EvidenceTier.GOLD.value,
                query_term="bulk_tsv_filter~magnolia_associated",
                query_date=self._query_date,
            ))

        log.info("NP Atlas: scanned %d rows, found %d Magnolia-associated compounds",
                 total_rows, len(records))
        return records

    def _is_magnolia_associated(self, row: dict) -> bool:
        """Check if this compound is associated with Magnolia in any field."""
        genus = row.get("genus", "").lower()
        species = row.get("origin_species", "").lower()
        ref_title = row.get("original_reference_title", "").lower()

        combined = f"{genus} {species} {ref_title}"
        return any(kw in combined for kw in MAGNOLIA_KEYWORDS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    collector = NPAtlasCollector()
    path = collector.run()
    print(f"Output: {path}")
