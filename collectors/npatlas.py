"""NP Atlas collector: curated natural products atlas with DOI references.

Searches by organism name for Magnolia and Magnoliaceae. Primarily covers
microbial NPs but includes endophyte-derived compounds from Magnolia hosts.

Evidence tier: GOLD (curated NP atlas with DOI provenance and species attribution).
"""

from __future__ import annotations

import logging

from bbb_database_stc.collectors.base import BaseCollector, RawCompound
from bbb_database_stc.utils.http import post_json
from bbb_database_stc.utils.taxonomy import normalize_species
from bbb_database_stc.config import EvidenceTier

log = logging.getLogger(__name__)

NPATLAS_API = "https://www.npatlas.org/api/v1"


class NPAtlasCollector(BaseCollector):
    name = "npatlas"
    description = "NP Atlas: curated NP atlas with DOI references (organism search)"

    def collect(self) -> list[RawCompound]:
        records: list[RawCompound] = []
        seen_ids: set[str] = set()

        search_terms = ["Magnolia", "Magnoliaceae"]

        for term in search_terms:
            log.info("NP Atlas search (POST): '%s'", term)
            try:
                data = post_json(
                    f"{NPATLAS_API}/compounds/basicSearch",
                    data={"query": term, "type": "organism", "limit": 10000},
                    delay=1.0,
                    timeout=60,
                )

                items = data if isinstance(data, list) else data.get("compounds", [])

                magnolia_items = [
                    item for item in items
                    if self._is_magnolia_related(item)
                ]

                for item in magnolia_items:
                    npaid = str(item.get("npaid", item.get("id", "")))
                    if npaid in seen_ids:
                        continue
                    seen_ids.add(npaid)

                    smiles = item.get("smiles", item.get("canonical_smiles", ""))
                    if not smiles:
                        continue

                    organism = ""
                    org_data = item.get("origin_organism", item.get("organism", {}))
                    if isinstance(org_data, dict):
                        genus = org_data.get("genus", "")
                        species = org_data.get("species", "")
                        organism = f"{genus} {species}".strip()
                    elif isinstance(org_data, str):
                        organism = org_data

                    doi = item.get("original_doi", "")
                    if not doi:
                        ref = item.get("original_reference", item.get("reference", {}))
                        if isinstance(ref, dict):
                            doi = ref.get("doi", "")

                    records.append(RawCompound(
                        compound_name=item.get("original_name", item.get("name", "")),
                        canonical_smiles=smiles,
                        inchi=item.get("inchi", ""),
                        inchikey=item.get("inchikey", ""),
                        molecular_formula=item.get("mol_formula", item.get("molecular_formula", "")),
                        source_db="NPAtlas",
                        source_id=npaid,
                        species=normalize_species(organism) if organism else "",
                        doi=doi,
                        evidence_tier=EvidenceTier.GOLD.value,
                        query_term=f"organism={term}",
                        query_date=self._query_date,
                    ))

                log.info("  '%s': %d items returned, %d Magnolia-related, %d with SMILES",
                         term, len(items), len(magnolia_items),
                         sum(1 for i in magnolia_items if i.get("smiles")))

            except Exception as e:
                log.warning("NP Atlas search '%s' failed: %s", term, e)

        log.info("NP Atlas total: %d records", len(records))
        return records

    def _is_magnolia_related(self, item: dict) -> bool:
        org = item.get("origin_organism", item.get("organism", {}))
        if isinstance(org, dict):
            genus = org.get("genus", "").lower()
            if "magnolia" in genus or "michelia" in genus or "talauma" in genus:
                return True
            family = org.get("family", "").lower()
            if "magnoliaceae" in family:
                return True
        elif isinstance(org, str):
            if "magnolia" in org.lower():
                return True
        name = item.get("original_name", "").lower()
        if "magnol" in name or "honoki" in name:
            return True
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    collector = NPAtlasCollector()
    path = collector.run()
    print(f"Output: {path}")
