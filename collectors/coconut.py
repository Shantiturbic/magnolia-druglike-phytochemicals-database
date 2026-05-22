"""COCONUT 2.0 collector: cross-reference Magnolia compounds against bulk CSV.

The COCONUT API is down and the full CSV requires auth. The public lite CSV
has ~738K compounds but no organism column. Strategy: cross-reference InChIKeys
from prior collectors (LOTUS, PubChem, KNApSAcK) against the lite CSV, plus
name fragment matching for known Magnolia phytochemicals.

Also extracts NP Classifier annotations (np_classifier_pathway, _superclass,
_class) when present in the CSV — used in Phase 4 enrichment.
"""

from __future__ import annotations

import csv
import logging
import pathlib
import urllib.request
import zipfile

from bbb_database_stc.collectors.base import BaseCollector, RawCompound
from bbb_database_stc.config import (
    RAW_DIR, CACHE_DIR, COCONUT_CSV_URL, KNOWN_MAGNOLIA_COMPOUNDS,
    EvidenceTier,
)

log = logging.getLogger(__name__)


class COCONUTCollector(BaseCollector):
    name = "coconut"
    description = "COCONUT 2.0: cross-reference Magnolia compounds against 738K NPs"

    def collect(self) -> list[RawCompound]:
        csv_path = self._get_csv()
        if csv_path is None:
            return []

        known_iks = self._load_known_inchikeys()
        log.info("Loaded %d known Magnolia InChIKeys from prior collectors", len(known_iks))

        return self._cross_reference(csv_path, known_iks)

    def _load_known_inchikeys(self) -> set[str]:
        iks: set[str] = set()
        for csv_file in RAW_DIR.glob("*.csv"):
            if csv_file.name == "coconut.csv":
                continue
            try:
                with open(csv_file, "r") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        ik = row.get("inchikey", "").strip()
                        if ik and len(ik) >= 14:
                            iks.add(ik[:14])
            except Exception:
                pass
        return iks

    def _get_csv(self) -> pathlib.Path | None:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        zip_path = CACHE_DIR / "coconut_csv_lite.zip"
        csv_path = CACHE_DIR / "coconut_lite.csv"

        if csv_path.exists() and csv_path.stat().st_size > 1_000_000:
            log.info("Using cached COCONUT CSV: %.1f MB", csv_path.stat().st_size / 1e6)
            return csv_path

        if not (zip_path.exists() and zip_path.stat().st_size > 1_000_000):
            log.info("Downloading COCONUT CSV lite (~190 MB)...")
            try:
                req = urllib.request.Request(
                    COCONUT_CSV_URL,
                    headers={"User-Agent": "BBB-MagnoliaDB/2.0 (thesis research)"},
                )
                with urllib.request.urlopen(req, timeout=600) as resp:
                    with open(zip_path, "wb") as f:
                        while True:
                            chunk = resp.read(1024 * 1024)
                            if not chunk:
                                break
                            f.write(chunk)
                log.info("Download complete: %.1f MB", zip_path.stat().st_size / 1e6)
            except Exception as e:
                log.error("Download failed: %s", e)
                if zip_path.exists():
                    zip_path.unlink()
                return None

        log.info("Extracting ZIP...")
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                csv_names = [n for n in zf.namelist() if n.endswith(".csv")]
                if not csv_names:
                    log.error("No CSV in ZIP")
                    return None
                with zf.open(csv_names[0]) as src, open(csv_path, "wb") as dst:
                    while True:
                        chunk = src.read(4 * 1024 * 1024)
                        if not chunk:
                            break
                        dst.write(chunk)
            log.info("Extracted: %.1f MB", csv_path.stat().st_size / 1e6)
            return csv_path
        except Exception as e:
            log.error("Extraction failed: %s", e)
            return None

    def _cross_reference(self, csv_path: pathlib.Path, known_iks: set[str]) -> list[RawCompound]:
        records: list[RawCompound] = []
        ik_matches = 0
        name_matches = 0
        seen_ids: set[str] = set()
        total_rows = 0

        log.info("Scanning COCONUT CSV (InChIKey cross-ref + name search)...")

        with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            header = list(reader.fieldnames or [])

            def _find_col(candidates: list[str]) -> str | None:
                for c in candidates:
                    if c in header:
                        return c
                return None

            ik_col = _find_col(["standard_inchi_key", "inchikey", "InChIKey"])
            smi_col = _find_col(["canonical_smiles", "smiles", "SMILES"])
            name_col = _find_col(["name", "iupac_name", "compound_name"])
            id_col = _find_col(["identifier", "id", "coconut_id"])
            inchi_col = _find_col(["standard_inchi", "inchi", "InChI"])
            mf_col = _find_col(["molecular_formula", "molecularFormula"])
            mw_col = _find_col(["molecular_weight", "molecularWeight"])
            npc_pathway_col = _find_col(["np_classifier_pathway", "npc_pathway"])
            npc_superclass_col = _find_col(["np_classifier_superclass", "npc_superclass"])
            npc_class_col = _find_col(["np_classifier_class", "npc_class"])

            for row in reader:
                total_rows += 1

                smiles = row.get(smi_col, "") if smi_col else ""
                if not smiles:
                    continue

                ik = row.get(ik_col, "") if ik_col else ""
                cid = row.get(id_col, "") if id_col else ""
                name = row.get(name_col, "") if name_col else ""

                matched = False
                match_type = ""

                if ik and len(ik) >= 14 and ik[:14] in known_iks:
                    matched = True
                    match_type = "inchikey"
                    ik_matches += 1
                elif name:
                    name_lower = name.lower()
                    for frag in KNOWN_MAGNOLIA_COMPOUNDS:
                        if frag in name_lower:
                            matched = True
                            match_type = "name"
                            name_matches += 1
                            break

                if not matched:
                    continue

                if cid in seen_ids and cid:
                    continue
                if cid:
                    seen_ids.add(cid)

                extra = {}
                if npc_pathway_col and row.get(npc_pathway_col, ""):
                    extra["np_classifier_pathway"] = row[npc_pathway_col]
                if npc_superclass_col and row.get(npc_superclass_col, ""):
                    extra["np_classifier_superclass"] = row[npc_superclass_col]
                if npc_class_col and row.get(npc_class_col, ""):
                    extra["np_classifier_class"] = row[npc_class_col]

                records.append(RawCompound(
                    compound_name=name,
                    canonical_smiles=smiles,
                    inchi=row.get(inchi_col, "") if inchi_col else "",
                    inchikey=ik,
                    molecular_formula=row.get(mf_col, "") if mf_col else "",
                    molecular_weight=float(row.get(mw_col, 0) or 0) if mw_col else 0.0,
                    source_db="COCONUT",
                    source_id=cid,
                    species="Magnolia sp.",
                    evidence_tier=(EvidenceTier.SILVER.value if match_type == "inchikey"
                                   else EvidenceTier.BRONZE.value),
                    query_term=match_type,
                    query_date=self._query_date,
                    extra=extra,
                ))

                if len(records) % 50 == 0:
                    log.info("  %d matches so far (scanned %d rows)",
                             len(records), total_rows)

        log.info("COCONUT cross-reference: %d matches from %d rows "
                 "(%d InChIKey, %d name)",
                 len(records), total_rows, ik_matches, name_matches)
        return records


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    collector = COCONUTCollector()
    path = collector.run()
    print(f"Output: {path}")
