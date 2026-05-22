"""Base collector class and RawCompound dataclass."""

from __future__ import annotations

import csv
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from pathlib import Path

from bbb_database_stc.config import RAW_DIR, SOURCE_REGISTRY, EvidenceTier

log = logging.getLogger(__name__)


@dataclass
class RawCompound:
    compound_name: str = ""
    canonical_smiles: str = ""
    inchi: str = ""
    inchikey: str = ""
    molecular_formula: str = ""
    molecular_weight: float = 0.0
    source_db: str = ""
    source_id: str = ""
    species: str = ""
    plant_part: str = ""
    doi: str = ""
    evidence_tier: str = EvidenceTier.BRONZE.value
    query_term: str = ""
    query_date: str = ""
    extra: dict = field(default_factory=dict)


FIELDNAMES = [
    "compound_name", "canonical_smiles", "inchi", "inchikey",
    "molecular_formula", "molecular_weight", "source_db", "source_id",
    "species", "plant_part", "doi", "evidence_tier", "query_term", "query_date",
]


class BaseCollector(ABC):
    name: str = "base"
    description: str = ""

    def __init__(self, output_dir: Path | None = None):
        self.output_dir = output_dir or RAW_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._start_time: float = 0
        self._query_date = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    @property
    def source_config(self):
        return SOURCE_REGISTRY.get(self.name)

    @abstractmethod
    def collect(self) -> list[RawCompound]:
        ...

    def run(self) -> Path:
        log.info("[%s] Starting collection...", self.name)
        self._start_time = time.time()

        try:
            records = self.collect()
        except Exception as e:
            log.error("[%s] Collection failed: %s", self.name, e)
            self._write_meta([], self.output_dir / f"{self.name}.csv",
                             status="failed", error=str(e))
            raise

        elapsed = time.time() - self._start_time
        outpath = self.output_dir / f"{self.name}.csv"
        self._write_csv(records, outpath)
        self._write_meta(records, outpath)

        log.info(
            "[%s] Done: %d records in %.1fs -> %s",
            self.name, len(records), elapsed, outpath.name,
        )
        return outpath

    def _write_csv(self, records: list[RawCompound], path: Path) -> None:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
            writer.writeheader()
            for r in records:
                row = asdict(r)
                row.pop("extra", None)
                writer.writerow(row)

    def _write_meta(self, records: list[RawCompound], path: Path,
                    status: str = "success", error: str = "") -> None:
        sc = self.source_config
        meta = {
            "source": self.name,
            "description": self.description,
            "record_count": len(records),
            "elapsed_seconds": round(time.time() - self._start_time, 1),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "status": status,
            "error": error,
            "tier": sc.tier if sc else None,
            "license": sc.license if sc else None,
        }
        metapath = path.with_suffix(".meta.json")
        with open(metapath, "w") as f:
            json.dump(meta, f, indent=2)
