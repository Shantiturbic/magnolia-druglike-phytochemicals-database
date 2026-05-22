"""PubChem taxonomy collector: discover compounds linked to genus Magnolia.

Uses NCBI Entrez esearch to find PubChem compound records associated with
Magnolia via organism annotation, then fetches full properties via PUG REST.

This is DISCOVERY — we find whatever PubChem associates with Magnolia without
presupposing specific compound names. PubChem's taxonomy coverage for Magnolia
is modest (~7-50 CIDs), but provides independent structural confirmation for
compounds found in other databases.

Evidence tier: SILVER (PubChem has species attribution but is not a curated NP
database; compounds come from depositor submissions).
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request

from bbb_database_stc.collectors.base import BaseCollector, RawCompound
from bbb_database_stc.utils.http import get_json
from bbb_database_stc.config import (
    NCBI_TAXONOMY_ID, MAGNOLIA_SPECIES_QIDS, OLD_GENUS_NAMES,
    SYNONYM_MAP, EvidenceTier,
)

log = logging.getLogger(__name__)

PUG_REST = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
ENTREZ = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


class PubChemTaxonomyCollector(BaseCollector):
    name = "pubchem_taxonomy"
    description = "PubChem: taxonomy-linked compound discovery via Entrez + PUG REST"

    def collect(self) -> list[RawCompound]:
        cids = self._discover_cids()
        if not cids:
            log.warning("No CIDs discovered for genus Magnolia")
            return []

        log.info("Discovered %d unique CIDs, fetching properties...", len(cids))
        return self._fetch_properties(sorted(cids))

    def _discover_cids(self) -> set[int]:
        all_cids: set[int] = set()

        search_terms = [
            ("Magnolia[Organism]", "pccompound"),
            ("honokiol AND Magnolia", "pccompound"),
            ("magnolol AND Magnolia", "pccompound"),
        ]

        for genus in OLD_GENUS_NAMES:
            search_terms.append((f"{genus}[Organism]", "pccompound"))

        all_species = [
            name for name in MAGNOLIA_SPECIES_QIDS.values()
            if name != "Magnolia (genus)" and "var." not in name
        ]
        for sp in all_species:
            search_terms.append((f'"{sp}"', "pccompound"))

        old_binomials = sorted({
            syn for syn in SYNONYM_MAP
            if not syn.startswith("Magnolia ")
        })
        for sp in old_binomials:
            search_terms.append((f'"{sp}"', "pccompound"))

        for term, db in search_terms:
            cids = self._entrez_search(term, db)
            new = len(cids - all_cids)
            all_cids.update(cids)
            if cids:
                log.info("  esearch %s [%s]: %d CIDs (%d new, %d cumul)",
                         term, db, len(cids), new, len(all_cids))
            time.sleep(0.4)

        for substance_term in ["Magnolia"] + OLD_GENUS_NAMES:
            sids = self._entrez_search(substance_term, "pcsubstance", retmax=500)
            if sids:
                log.info("  pcsubstance '%s': %d SIDs, mapping to CIDs...",
                         substance_term, len(sids))
                mapped = self._sids_to_cids(sids)
                new = len(mapped - all_cids)
                all_cids.update(mapped)
                log.info("  SID→CID: %d CIDs (%d new)", len(mapped), new)
                time.sleep(0.4)

        log.info("Total discovered CIDs: %d", len(all_cids))
        return all_cids

    def _entrez_search(self, term: str, db: str, retmax: int = 10000) -> set[int]:
        encoded = urllib.parse.quote(term)
        url = (
            f"{ENTREZ}/esearch.fcgi?db={db}&term={encoded}"
            f"&retmax={retmax}&retmode=json"
        )
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "BBB-MagnoliaDB/2.0"}
            )
            time.sleep(0.4)
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
                ids = data.get("esearchresult", {}).get("idlist", [])
                return {int(x) for x in ids}
        except Exception as e:
            log.debug("Entrez search '%s' in %s failed: %s", term, db, e)
            return set()

    def _sids_to_cids(self, sids: set[int]) -> set[int]:
        cids: set[int] = set()
        sid_list = sorted(sids)

        for i in range(0, len(sid_list), 50):
            batch = sid_list[i:i + 50]
            sid_str = ",".join(str(s) for s in batch)
            url = (
                f"{ENTREZ}/elink.fcgi?dbfrom=pcsubstance&db=pccompound"
                f"&id={sid_str}&retmode=json&linkname=pcsubstance_pccompound"
            )
            try:
                req = urllib.request.Request(
                    url, headers={"User-Agent": "BBB-MagnoliaDB/2.0"}
                )
                time.sleep(0.4)
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode())
                    for ls in data.get("linksets", []):
                        for ldb in ls.get("linksetdbs", []):
                            cids.update(int(x) for x in ldb.get("links", []))
            except Exception as e:
                log.debug("elink batch %d failed: %s", i, e)

        return cids

    def _fetch_properties(self, cids: list[int]) -> list[RawCompound]:
        records: list[RawCompound] = []
        batch_size = 100

        for i in range(0, len(cids), batch_size):
            batch = cids[i:i + batch_size]
            cid_str = ",".join(str(c) for c in batch)
            url = (
                f"{PUG_REST}/compound/cid/{cid_str}/property/"
                "CanonicalSMILES,IsomericSMILES,InChI,InChIKey,"
                "MolecularFormula,MolecularWeight,IUPACName/JSON"
            )

            try:
                data = get_json(url, delay=0.4, timeout=30)
                props_list = data.get("PropertyTable", {}).get("Properties", [])

                for prop in props_list:
                    cid = prop.get("CID", 0)
                    smiles = (
                        prop.get("CanonicalSMILES")
                        or prop.get("SMILES")
                        or prop.get("ConnectivitySMILES")
                        or prop.get("IsomericSMILES", "")
                    )
                    if not smiles:
                        continue

                    records.append(RawCompound(
                        compound_name=prop.get("IUPACName", ""),
                        canonical_smiles=smiles,
                        inchi=prop.get("InChI", ""),
                        inchikey=prop.get("InChIKey", ""),
                        molecular_formula=prop.get("MolecularFormula", ""),
                        molecular_weight=float(prop.get("MolecularWeight", 0) or 0),
                        source_db="PubChem",
                        source_id=str(cid),
                        species="Magnolia sp.",
                        evidence_tier=EvidenceTier.SILVER.value,
                        query_term=f"Entrez_TaxID:{NCBI_TAXONOMY_ID}",
                        query_date=self._query_date,
                    ))

            except Exception as e:
                log.warning("Property fetch failed for batch %d-%d: %s",
                            i, i + len(batch), e)

            if (i + batch_size) % 500 == 0:
                log.info("  Fetched properties for %d/%d CIDs, %d records",
                         min(i + batch_size, len(cids)), len(cids), len(records))

        log.info("PubChem taxonomy: %d compounds from %d CIDs", len(records), len(cids))
        return records


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    collector = PubChemTaxonomyCollector()
    path = collector.run()
    print(f"Output: {path}")
