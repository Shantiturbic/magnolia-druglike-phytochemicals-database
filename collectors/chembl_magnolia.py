"""ChEMBL collector: bioactivity data for Magnolia-derived compounds.

Searches ChEMBL for:
  1. Molecules matching known Magnolia compound names (from config)
  2. Assays with "Magnolia" in the description

Requires: chembl_webresource_client (pip install chembl_webresource_client)
Evidence tier: SILVER (general chemistry DB with bioactivity, not taxonomy-curated NP).
"""

from __future__ import annotations

import logging

from bbb_database_stc.collectors.base import BaseCollector, RawCompound
from bbb_database_stc.config import (
    KNOWN_MAGNOLIA_COMPOUNDS, OLD_GENUS_NAMES, EvidenceTier,
)

log = logging.getLogger(__name__)


class ChEMBLMagnoliaCollector(BaseCollector):
    name = "chembl_magnolia"
    description = "ChEMBL: bioactivity data for Magnolia-associated compounds"

    def collect(self) -> list[RawCompound]:
        try:
            from chembl_webresource_client.settings import Settings
            Settings.Instance().CACHING = False
            from chembl_webresource_client.new_client import new_client
        except ImportError:
            log.error("chembl_webresource_client not installed — "
                      "pip install chembl_webresource_client")
            return []
        except Exception as e:
            log.error("ChEMBL client init failed: %s", e)
            return []

        records: list[RawCompound] = []
        seen_ids: set[str] = set()

        records.extend(self._search_by_name(new_client, seen_ids))
        records.extend(self._search_assays(new_client, seen_ids))

        log.info("ChEMBL total: %d records", len(records))
        return records

    def _search_by_name(self, client, seen_ids: set[str]) -> list[RawCompound]:
        records: list[RawCompound] = []
        molecule = client.molecule

        for name in KNOWN_MAGNOLIA_COMPOUNDS:
            log.info("ChEMBL molecule search: '%s'", name)
            try:
                results = molecule.filter(
                    pref_name__icontains=name
                ).only([
                    "molecule_chembl_id", "pref_name",
                    "molecule_structures",
                    "molecule_properties",
                ])

                for mol in results:
                    chembl_id = mol.get("molecule_chembl_id", "")
                    if chembl_id in seen_ids:
                        continue
                    seen_ids.add(chembl_id)

                    structs = mol.get("molecule_structures") or {}
                    smiles = structs.get("canonical_smiles", "")
                    if not smiles:
                        continue

                    props = mol.get("molecule_properties") or {}

                    records.append(RawCompound(
                        compound_name=mol.get("pref_name", name),
                        canonical_smiles=smiles,
                        inchi=structs.get("standard_inchi", ""),
                        inchikey=structs.get("standard_inchi_key", ""),
                        molecular_formula=props.get("full_molformula", ""),
                        molecular_weight=float(props.get("full_mwt", 0) or 0),
                        source_db="ChEMBL",
                        source_id=chembl_id,
                        species="Magnolia sp.",
                        evidence_tier=EvidenceTier.SILVER.value,
                        query_term=f"pref_name__icontains={name}",
                        query_date=self._query_date,
                    ))

            except Exception as e:
                log.warning("ChEMBL search '%s' failed: %s", name, e)

        return records

    def _search_assays(self, client, seen_ids: set[str]) -> list[RawCompound]:
        records: list[RawCompound] = []

        assay_terms = ["Magnolia"] + OLD_GENUS_NAMES
        for assay_term in assay_terms:
            records.extend(self._search_assays_for_term(client, seen_ids, assay_term))

        return records

    def _search_assays_for_term(self, client, seen_ids: set[str], term: str) -> list[RawCompound]:
        records: list[RawCompound] = []
        log.info("ChEMBL: searching assays mentioning '%s'...", term)
        try:
            assay = client.assay
            activity = client.activity

            assay_results = assay.filter(
                description__icontains=term
            ).only(["assay_chembl_id"])

            for a in assay_results:
                aid = a.get("assay_chembl_id", "")
                if not aid:
                    continue

                acts = activity.filter(
                    assay_chembl_id=aid
                ).only([
                    "molecule_chembl_id", "canonical_smiles",
                    "standard_type", "standard_value", "standard_units",
                ])

                for act in acts:
                    mid = act.get("molecule_chembl_id", "")
                    if mid in seen_ids:
                        continue
                    seen_ids.add(mid)

                    smiles = act.get("canonical_smiles", "")
                    if not smiles:
                        continue

                    extra = {}
                    st = act.get("standard_type", "")
                    sv = act.get("standard_value")
                    su = act.get("standard_units", "")
                    if st and sv is not None:
                        extra["bioactivity"] = f"{st}={sv} {su}".strip()

                    records.append(RawCompound(
                        compound_name="",
                        canonical_smiles=smiles,
                        source_db="ChEMBL",
                        source_id=mid,
                        species="Magnolia sp.",
                        evidence_tier=EvidenceTier.SILVER.value,
                        query_term=f"assay:{aid}",
                        query_date=self._query_date,
                        extra=extra,
                    ))

        except Exception as e:
            log.warning("ChEMBL assay search failed: %s", e)

        return records


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    collector = ChEMBLMagnoliaCollector()
    path = collector.run()
    print(f"Output: {path}")
