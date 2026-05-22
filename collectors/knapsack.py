"""KNApSAcK collector: species-metabolite pairs for Magnolia genus.

KNApSAcK Core DB contains 101,500+ species-metabolite relationships.
Query by organism name for Magnolia species. Returns names + formulas
(no SMILES); structures resolved in Phase 3 (standardize).
"""

from __future__ import annotations

import logging
import time

from bbb_database_stc.collectors.base import BaseCollector, RawCompound
from bbb_database_stc.utils.http import get_text
from bbb_database_stc.utils.taxonomy import normalize_species
from bbb_database_stc.config import (
    MAGNOLIA_SPECIES_QIDS, OLD_GENUS_NAMES, SYNONYM_MAP, EvidenceTier,
)

log = logging.getLogger(__name__)

KNAPSACK_SEARCH = "http://www.knapsackfamily.com/knapsack_core/result.php"


class KNApSAcKCollector(BaseCollector):
    name = "knapsack"
    description = "KNApSAcK: species-metabolite relationship DB (web scraping)"

    def collect(self) -> list[RawCompound]:
        records: list[RawCompound] = []
        all_species = [
            name for name in MAGNOLIA_SPECIES_QIDS.values()
            if name != "Magnolia (genus)" and "var." not in name
        ]
        old_binomials = sorted({
            syn for syn in SYNONYM_MAP
            if not syn.startswith("Magnolia ")
        })
        search_terms = (
            ["Magnolia"] + OLD_GENUS_NAMES
            + all_species + old_binomials
        )
        seen_pairs: set[str] = set()

        for term in search_terms:
            log.info("KNApSAcK search: '%s'", term)
            try:
                new_records = self._search_organism(term, seen_pairs)
                records.extend(new_records)
                time.sleep(2.0)
            except Exception as e:
                log.warning("KNApSAcK search '%s' failed: %s", term, e)

        log.info("KNApSAcK total: %d records", len(records))
        return records

    def _search_organism(self, organism: str, seen: set[str]) -> list[RawCompound]:
        records: list[RawCompound] = []

        try:
            html = get_text(
                KNAPSACK_SEARCH,
                params={"sname": "organism", "word": organism},
                delay=2.0,
                timeout=60,
            )
        except Exception as e:
            log.warning("KNApSAcK HTTP failed for '%s': %s", organism, e)
            return records

        rows = self._parse_html_table(html)

        for row in rows:
            c_id = row.get("c_id", "")
            name = row.get("name", "")
            formula = row.get("formula", "")
            species = row.get("organism", "")
            cas = row.get("cas", "")

            pair_key = f"{c_id}:{species}"
            if pair_key in seen:
                continue
            seen.add(pair_key)

            records.append(RawCompound(
                compound_name=name,
                molecular_formula=formula,
                source_db="KNApSAcK",
                source_id=c_id,
                species=normalize_species(species) if species else "",
                evidence_tier=EvidenceTier.GOLD.value,
                query_term=organism,
                query_date=self._query_date,
                extra={"cas": cas},
            ))

        return records

    def _parse_html_table(self, html: str) -> list[dict]:
        rows: list[dict] = []
        try:
            from html.parser import HTMLParser

            class TableParser(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.in_table = False
                    self.in_td = False
                    self.current_row: list[str] = []
                    self.all_rows: list[list[str]] = []
                    self.current_data = ""

                def handle_starttag(self, tag, attrs):
                    if tag == "table":
                        self.in_table = True
                    elif tag == "td" and self.in_table:
                        self.in_td = True
                        self.current_data = ""
                    elif tag == "tr" and self.in_table:
                        self.current_row = []

                def handle_endtag(self, tag):
                    if tag == "td" and self.in_td:
                        self.in_td = False
                        self.current_row.append(self.current_data.strip())
                    elif tag == "tr" and self.in_table:
                        if self.current_row:
                            self.all_rows.append(self.current_row)
                    elif tag == "table":
                        self.in_table = False

                def handle_data(self, data):
                    if self.in_td:
                        self.current_data += data

            parser = TableParser()
            parser.feed(html)

            for row_data in parser.all_rows:
                if len(row_data) >= 4:
                    rows.append({
                        "c_id": row_data[0] if len(row_data) > 0 else "",
                        "cas": row_data[1] if len(row_data) > 1 else "",
                        "name": row_data[2] if len(row_data) > 2 else "",
                        "formula": row_data[3] if len(row_data) > 3 else "",
                        "organism": row_data[5] if len(row_data) > 5 else "",
                    })

        except Exception as e:
            log.warning("HTML parsing failed: %s", e)

        return rows


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    collector = KNApSAcKCollector()
    path = collector.run()
    print(f"Output: {path}")
