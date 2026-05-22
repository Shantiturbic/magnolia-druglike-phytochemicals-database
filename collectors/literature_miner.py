"""Literature miner: 3-layer compound extraction from published papers.

Layer 1: PubMed abstract mining with chemical NER (dictionary + regex)
Layer 2: PMC full-text table extraction
Layer 3: Claude API structured extraction for complex papers

The NER dictionary is built dynamically from Phase 1 results (all compound
names found across database collectors) plus the KNOWN_MAGNOLIA_COMPOUNDS
baseline from config. This means literature mining confirms known compounds
AND discovers new ones.

Evidence tier: PROVISIONAL (name-only extractions without SMILES need
resolution in Phase 3).
"""

from __future__ import annotations

import csv
import json
import logging
import os
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from bbb_database_stc.collectors.base import BaseCollector, RawCompound
from bbb_database_stc.config import (
    KNOWN_MAGNOLIA_COMPOUNDS, OLD_GENUS_NAMES, EvidenceTier, RAW_DIR,
)
from bbb_database_stc.utils.http import get_json, get_text
from bbb_database_stc.utils.taxonomy import extract_species_from_text, normalize_species

log = logging.getLogger(__name__)

ENTREZ_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
S2_API = "https://api.semanticscholar.org/graph/v1"

_GENUS_OR = " OR ".join(
    f'"{g}"[Title/Abstract]'
    for g in ["Magnolia"] + OLD_GENUS_NAMES[:5]
)

PUBMED_QUERY = (
    f'({_GENUS_OR}) AND '
    '("phytochem*"[Title/Abstract] OR "compound*"[Title/Abstract] OR '
    '"isolat*"[Title/Abstract] OR "constituent*"[Title/Abstract] OR '
    '"secondary metabolit*"[Title/Abstract] OR "essential oil"[Title/Abstract] OR '
    '"bioactive"[Title/Abstract] OR "alkaloid*"[Title/Abstract] OR '
    '"lignan*"[Title/Abstract] OR "neolignan*"[Title/Abstract] OR '
    '"terpenoid*"[Title/Abstract] OR "flavonoid*"[Title/Abstract])'
)


def _build_compound_dictionary() -> set[str]:
    """Build NER dictionary from config baseline + Phase 1 raw CSVs."""
    names = {n.lower() for n in KNOWN_MAGNOLIA_COMPOUNDS}

    for csv_path in sorted(RAW_DIR.glob("*.csv")):
        if csv_path.stem == "literature_miner":
            continue
        try:
            with open(csv_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get("compound_name", "").strip()
                    if name and len(name) >= 3:
                        names.add(name.lower())
        except Exception:
            pass

    log.info("NER dictionary: %d compound names (%d from config, rest from Phase 1)",
             len(names), len(KNOWN_MAGNOLIA_COMPOUNDS))
    return names


class LiteratureMinerCollector(BaseCollector):
    name = "literature_miner"
    description = "PubMed + PMC + S2: 3-layer compound extraction from literature"

    def __init__(self, *args, use_llm: bool = True, max_papers_llm: int = 200, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_llm = use_llm
        self.max_papers_llm = max_papers_llm
        self._compound_dict: set[str] = set()

    def collect(self) -> list[RawCompound]:
        self._compound_dict = _build_compound_dictionary()
        records: list[RawCompound] = []

        log.info("=== Layer 1: PubMed abstract mining ===")
        pmids = self._search_pubmed()
        log.info("Found %d PubMed articles", len(pmids))

        abstracts = self._fetch_abstracts(pmids)
        layer1 = self._extract_from_abstracts(abstracts)
        records.extend(layer1)
        log.info("Layer 1 (abstracts): %d compound mentions", len(layer1))

        log.info("=== Layer 2: PMC full-text table extraction ===")
        pmc_ids = self._find_pmc_articles(pmids)
        layer2 = self._extract_from_fulltext(pmc_ids)
        records.extend(layer2)
        log.info("Layer 2 (full-text): %d compound mentions", len(layer2))

        if self.use_llm:
            log.info("=== Layer 3: LLM structured extraction ===")
            layer3 = self._llm_extraction(abstracts)
            records.extend(layer3)
            log.info("Layer 3 (LLM): %d compound extractions", len(layer3))

        log.info("=== Supplementary: Semantic Scholar ===")
        s2 = self._search_semantic_scholar()
        records.extend(s2)

        log.info("Literature miner total: %d records", len(records))
        return records

    def _search_pubmed(self, max_results: int = 2000) -> list[str]:
        try:
            data = get_json(
                f"{ENTREZ_BASE}/esearch.fcgi",
                params={
                    "db": "pubmed",
                    "term": PUBMED_QUERY,
                    "retmax": str(max_results),
                    "retmode": "json",
                    "sort": "relevance",
                },
                delay=0.4,
            )
            return data.get("esearchresult", {}).get("idlist", [])
        except Exception as e:
            log.error("PubMed search failed: %s", e)
            return []

    def _fetch_abstracts(self, pmids: list[str]) -> dict[str, dict]:
        abstracts: dict[str, dict] = {}
        batch_size = 200

        for i in range(0, len(pmids), batch_size):
            batch = pmids[i:i + batch_size]
            log.info("Fetching abstracts %d-%d of %d",
                     i + 1, min(i + batch_size, len(pmids)), len(pmids))
            try:
                xml_text = get_text(
                    f"{ENTREZ_BASE}/efetch.fcgi",
                    params={
                        "db": "pubmed",
                        "id": ",".join(batch),
                        "rettype": "xml",
                        "retmode": "xml",
                    },
                    delay=0.5,
                    timeout=60,
                )

                root = ET.fromstring(xml_text)
                for article in root.findall(".//PubmedArticle"):
                    pmid_el = article.find(".//PMID")
                    if pmid_el is None:
                        continue
                    pmid = pmid_el.text

                    title_el = article.find(".//ArticleTitle")
                    title = title_el.text if title_el is not None and title_el.text else ""

                    abstract_parts = article.findall(".//AbstractText")
                    abstract = " ".join(
                        (part.text or "") + (part.tail or "")
                        for part in abstract_parts
                    ).strip()

                    doi = ""
                    for eid in article.findall(".//ArticleId"):
                        if eid.get("IdType") == "doi":
                            doi = eid.text or ""
                            break

                    abstracts[pmid] = {
                        "title": title,
                        "abstract": abstract,
                        "doi": doi,
                    }

            except Exception as e:
                log.warning("Abstract fetch batch %d failed: %s", i, e)

        return abstracts

    def _extract_from_abstracts(self, abstracts: dict[str, dict]) -> list[RawCompound]:
        records: list[RawCompound] = []
        seen: set[str] = set()

        for pmid, paper in abstracts.items():
            text = f"{paper['title']} {paper['abstract']}".lower()
            doi = paper.get("doi", "")

            for compound in self._compound_dict:
                if compound in text:
                    key = f"{compound}:{doi}"
                    if key in seen:
                        continue
                    seen.add(key)

                    species_list = extract_species_from_text(
                        f"{paper['title']} {paper['abstract']}"
                    )

                    records.append(RawCompound(
                        compound_name=compound,
                        source_db="PubMed_NER",
                        source_id=f"PMID:{pmid}",
                        species="|".join(species_list) if species_list else "Magnolia sp.",
                        doi=doi,
                        evidence_tier=EvidenceTier.PROVISIONAL.value,
                        query_term="PubMed_abstract_NER",
                        query_date=self._query_date,
                    ))

        return records

    def _find_pmc_articles(self, pmids: list[str]) -> list[str]:
        pmc_ids: list[str] = []
        batch_size = 200

        for i in range(0, len(pmids), batch_size):
            batch = pmids[i:i + batch_size]
            try:
                data = get_json(
                    f"{ENTREZ_BASE}/elink.fcgi",
                    params={
                        "dbfrom": "pubmed",
                        "db": "pmc",
                        "id": ",".join(batch),
                        "retmode": "json",
                    },
                    delay=0.5,
                )

                for linkset in data.get("linksets", []):
                    for linkdb in linkset.get("linksetdbs", []):
                        if linkdb.get("dbto") == "pmc":
                            for link in linkdb.get("links", []):
                                pmc_ids.append(link)

            except Exception as e:
                log.warning("PMC link lookup batch %d failed: %s", i, e)

        log.info("Found %d PMC full-text articles from %d PMIDs", len(pmc_ids), len(pmids))
        return pmc_ids[:500]

    def _extract_from_fulltext(self, pmc_ids: list[str]) -> list[RawCompound]:
        records: list[RawCompound] = []
        seen: set[str] = set()
        limit = min(100, len(pmc_ids))

        for i, pmc_id in enumerate(pmc_ids[:limit]):
            if i % 20 == 0:
                log.info("Processing PMC article %d/%d", i + 1, limit)

            try:
                xml_text = get_text(
                    f"{ENTREZ_BASE}/efetch.fcgi",
                    params={
                        "db": "pmc",
                        "id": pmc_id,
                        "rettype": "xml",
                        "retmode": "xml",
                    },
                    delay=0.5,
                    timeout=60,
                )

                root = ET.fromstring(xml_text)

                doi = ""
                for aid in root.findall(".//article-id"):
                    if aid.get("pub-id-type") == "doi":
                        doi = aid.text or ""
                        break

                for table in root.findall(".//table-wrap"):
                    caption = table.find(".//caption")
                    caption_text = ""
                    if caption is not None:
                        caption_text = "".join(caption.itertext()).lower()

                    is_compound_table = any(
                        term in caption_text
                        for term in [
                            "compound", "constituent", "phytochem",
                            "metabolit", "isolat", "chemical composition",
                        ]
                    )
                    if not is_compound_table:
                        continue

                    for row in table.findall(".//tr"):
                        cells = row.findall(".//td")
                        if not cells:
                            continue

                        for cell in cells:
                            cell_text = "".join(cell.itertext()).strip()
                            if not cell_text or len(cell_text) < 3:
                                continue

                            cell_lower = cell_text.lower()
                            for known in self._compound_dict:
                                if known in cell_lower:
                                    key = f"{known}:{doi}"
                                    if key not in seen:
                                        seen.add(key)
                                        records.append(RawCompound(
                                            compound_name=known,
                                            source_db="PMC_fulltext",
                                            source_id=f"PMC:{pmc_id}",
                                            species="Magnolia sp.",
                                            doi=doi,
                                            evidence_tier=EvidenceTier.PROVISIONAL.value,
                                            query_term="PMC_table_NER",
                                            query_date=self._query_date,
                                        ))

            except Exception as e:
                log.debug("PMC %s parse failed: %s", pmc_id, e)

        return records

    def _llm_extraction(self, abstracts: dict[str, dict]) -> list[RawCompound]:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            log.warning("ANTHROPIC_API_KEY not set, skipping LLM extraction")
            return []

        records: list[RawCompound] = []
        papers = list(abstracts.items())[:self.max_papers_llm]
        log.info("LLM extraction: processing %d papers", len(papers))

        batch_size = 10
        for i in range(0, len(papers), batch_size):
            batch = papers[i:i + batch_size]
            log.info("LLM batch %d-%d of %d",
                     i + 1, min(i + batch_size, len(papers)), len(papers))

            for pmid, paper in batch:
                title = paper.get("title", "")
                abstract = paper.get("abstract", "")
                doi = paper.get("doi", "")

                if not abstract or len(abstract) < 100:
                    continue

                try:
                    extracted = self._call_claude(pmid, title, abstract, doi)
                    records.extend(extracted)
                except Exception as e:
                    log.debug("LLM extraction failed for PMID %s: %s", pmid, e)

                time.sleep(0.3)

        return records

    def _call_claude(self, pmid: str, title: str, abstract: str, doi: str) -> list[RawCompound]:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return []

        prompt = (
            "Extract all phytochemical compounds mentioned in this paper as being "
            "isolated from, found in, or associated with a Magnolia species "
            "(including old genus names: Michelia, Talauma, Manglietia, Liriopsis, Yulania).\n\n"
            f"Title: {title}\n\n"
            f"Abstract: {abstract}\n\n"
            "Return ONLY a JSON array (no other text). Each element:\n"
            '{"compound_name": "string", "species": "string (Magnolia species name)", '
            '"plant_part": "string (bark/leaf/flower/root/seed/fruit or empty)", '
            '"activity": "string (any reported bioactivity or empty)"}\n\n'
            "If no Magnolia compounds are mentioned, return an empty array []."
        )

        body = json.dumps({
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        }).encode()

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=body,
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())

        text_content = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                text_content += block.get("text", "")

        json_match = re.search(r'\[.*\]', text_content, re.DOTALL)
        if not json_match:
            return []

        compounds = json.loads(json_match.group())
        records: list[RawCompound] = []
        for c in compounds:
            name = c.get("compound_name", "").strip()
            if not name:
                continue

            species = c.get("species", "Magnolia sp.").strip()
            if species:
                species = normalize_species(species)

            records.append(RawCompound(
                compound_name=name,
                source_db="LLM_extraction",
                source_id=f"PMID:{pmid}",
                species=species,
                plant_part=c.get("plant_part", ""),
                doi=doi,
                evidence_tier=EvidenceTier.PROVISIONAL.value,
                query_term="Claude_abstract_extraction",
                query_date=self._query_date,
            ))

        return records

    def _search_semantic_scholar(self) -> list[RawCompound]:
        records: list[RawCompound] = []
        queries = [
            "Magnolia phytochemistry compounds",
            "Magnolia officinalis bioactive constituents",
            "honokiol magnolol biological activity",
        ]

        for query in queries:
            try:
                data = get_json(
                    f"{S2_API}/paper/search",
                    params={
                        "query": query,
                        "limit": "100",
                        "fields": "title,abstract,externalIds",
                    },
                    delay=3.0,
                    timeout=30,
                )

                papers = data.get("data", [])
                seen: set[str] = set()
                for paper in papers:
                    abstract = paper.get("abstract", "")
                    if not abstract:
                        continue
                    title = paper.get("title", "")
                    ext_ids = paper.get("externalIds", {}) or {}
                    doi = ext_ids.get("DOI", "")

                    text = f"{title} {abstract}".lower()
                    for compound in self._compound_dict:
                        if compound in text:
                            key = f"{compound}:{doi}"
                            if key in seen:
                                continue
                            seen.add(key)

                            species_list = extract_species_from_text(f"{title} {abstract}")
                            records.append(RawCompound(
                                compound_name=compound,
                                source_db="SemanticScholar_NER",
                                source_id=f"DOI:{doi}" if doi else "",
                                species="|".join(species_list) if species_list else "Magnolia sp.",
                                doi=doi,
                                evidence_tier=EvidenceTier.PROVISIONAL.value,
                                query_term=f"S2_search:{query}",
                                query_date=self._query_date,
                            ))

            except Exception as e:
                log.warning("S2 search '%s' failed: %s", query, e)

        log.info("Semantic Scholar: %d records", len(records))
        return records


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    collector = LiteratureMinerCollector(use_llm=False)
    path = collector.run()
    print(f"Output: {path}")
