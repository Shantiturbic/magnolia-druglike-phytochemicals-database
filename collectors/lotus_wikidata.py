"""LOTUS/Wikidata collector: SPARQL for compounds found in genus Magnolia.

Uses P703 (found in taxon) with transitive P171* (parent taxon).
Per-species queries against Wikidata QIDs from config. CC0 license.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.parse
import urllib.request

from bbb_database_stc.collectors.base import BaseCollector, RawCompound
from bbb_database_stc.config import (
    MAGNOLIA_SPECIES_QIDS, OLD_GENUS_WIKIDATA_QIDS,
    EvidenceTier, SPARQL_TIMEOUT, SPARQL_INTER_QUERY_DELAY,
)

log = logging.getLogger(__name__)

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

SPECIES_QUERY_TEMPLATE = """
SELECT DISTINCT ?compound ?compoundLabel ?smiles ?inchi ?inchikey ?taxon ?taxonLabel
WHERE {{
  ?taxon wdt:P171* wd:{species_qid} .
  ?compound wdt:P703 ?taxon .
  OPTIONAL {{ ?compound wdt:P233 ?smiles . }}
  OPTIONAL {{ ?compound wdt:P234 ?inchi . }}
  OPTIONAL {{ ?compound wdt:P235 ?inchikey . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
}}
"""


class LOTUSCollector(BaseCollector):
    name = "lotus_wikidata"
    description = "LOTUS/Wikidata SPARQL: compounds found in genus Magnolia (CC0)"

    def collect(self) -> list[RawCompound]:
        all_records: list[RawCompound] = []
        seen_pairs: set[str] = set()

        all_qids = dict(MAGNOLIA_SPECIES_QIDS)
        for qid, genus_name in OLD_GENUS_WIKIDATA_QIDS.items():
            if qid not in all_qids:
                all_qids[qid] = genus_name

        for qid, taxon_name in all_qids.items():
            log.info("SPARQL query: %s (%s)", taxon_name, qid)
            query = SPECIES_QUERY_TEMPLATE.format(species_qid=qid)
            results = self._run_sparql(query)

            for row in results:
                compound_name = row.get("compoundLabel", {}).get("value", "")
                smiles = row.get("smiles", {}).get("value", "")
                inchi_val = row.get("inchi", {}).get("value", "")
                inchikey_val = row.get("inchikey", {}).get("value", "")
                species = row.get("taxonLabel", {}).get("value", "")
                wikidata_id = row.get("compound", {}).get("value", "").split("/")[-1]

                if not smiles and not inchi_val:
                    continue

                pair_key = f"{wikidata_id}:{species}"
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                all_records.append(RawCompound(
                    compound_name=compound_name,
                    canonical_smiles=smiles,
                    inchi=inchi_val,
                    inchikey=inchikey_val,
                    source_db="LOTUS_Wikidata",
                    source_id=wikidata_id,
                    species=species,
                    evidence_tier=EvidenceTier.GOLD.value,
                    query_term=f"P703/P171* wd:{qid}",
                    query_date=self._query_date,
                ))

            log.info("  %s: %d cumulative records", taxon_name, len(all_records))
            time.sleep(SPARQL_INTER_QUERY_DELAY)

        log.info("LOTUS/Wikidata total: %d compound-species pairs", len(all_records))
        return all_records

    def _run_sparql(self, query: str) -> list[dict]:
        params = urllib.parse.urlencode({"query": query, "format": "json"})
        url = f"{SPARQL_ENDPOINT}?{params}"
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/sparql-results+json",
                "User-Agent": "BBB-MagnoliaDB/2.0 (thesis research)",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=SPARQL_TIMEOUT) as resp:
                data = json.loads(resp.read().decode())
                return data.get("results", {}).get("bindings", [])
        except Exception as e:
            log.warning("SPARQL query failed: %s", e)
            return []


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    collector = LOTUSCollector()
    path = collector.run()
    print(f"Output: {path}")
