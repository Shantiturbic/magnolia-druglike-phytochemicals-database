"""
Bioactivity enrichment from ChEMBL for the Magnolia BBB database.

Strategy:
  1. Batch-lookup InChIKeys against ChEMBL molecule endpoint (50 per batch)
  2. For each found molecule, pull all bioactivity records (paginated, limit=1000)
  3. Optionally fetch DOIs from document endpoint (rate-limited)
  4. Write two output files:
     - magnolia_bbb_bioactivity.csv: all individual activity records
     - magnolia_bbb_bioactivity_summary.csv: per-compound summary for merge

Incremental progress: checkpoint file tracks which InChIKeys have been processed.
Resume by re-running; already-processed compounds are skipped.

Usage:
    python -m phases.bioactivity_enrichment            # full run
    python -m phases.bioactivity_enrichment --test      # test with 10 known compounds
    python -m phases.bioactivity_enrichment --resume    # resume interrupted run
    python -m phases.bioactivity_enrichment --fetch-dois  # also resolve DOIs (slower)
"""

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATABASE_CSV = DATA_DIR / "magnolia_bbb_database.csv"

OUTPUT_ACTIVITIES = DATA_DIR / "magnolia_bbb_bioactivity.csv"
OUTPUT_SUMMARY = DATA_DIR / "magnolia_bbb_bioactivity_summary.csv"
CHECKPOINT_FILE = DATA_DIR / ".bioactivity_checkpoint.json"
DOI_CACHE_FILE = DATA_DIR / ".doi_cache.json"

CHEMBL_BASE = "https://www.ebi.ac.uk/chembl/api/data"
MOLECULE_BATCH_SIZE = 50  # max InChIKeys per batch lookup
ACTIVITY_PAGE_SIZE = 1000  # max activities per request
REQUEST_DELAY = 0.4  # seconds between API calls (rate limiting)
BATCH_DELAY = 1.0  # seconds between molecule batches
SAVE_EVERY = 50  # save checkpoint every N compounds

# Antiviral target keywords for flagging relevant activities
# These are matched against the combined target_name + organism + assay_description
ANTIVIRAL_KEYWORDS = [
    "virus", "viral", "antiviral",
    "dengue", "denv", "flavivir", "zika", "chikungunya",
    "hiv", "sars", "cov", "hepatitis", "hcv", "hbv", "influenza", "ebola",
    "herpes", "rsv", "enterovirus",
    # Cell-based antiviral assay indicators
    "vero", "huh-7", "bhk-21", "c6/36",
]

# Dengue/flavivirus keywords -- must be specific to avoid false positives
# (e.g., "ns1" alone matches Influenza NS1, "e protein" matches any protein)
DENGUE_KEYWORDS = [
    "dengue", "denv",
]

# Broader flavivirus relevance (still highly relevant to dengue thesis)
FLAVIVIRUS_KEYWORDS = [
    "flavivir", "zika", "zikv", "west nile", "wnv", "yellow fever", "yfv",
    "japanese encephalitis", "jev", "tick-borne encephalitis",
]

# Relevant bioactivity categories beyond antiviral
RELEVANT_CATEGORIES = {
    "antimicrobial": ["antibacter", "antimicrob", "antifung", "mic ", "mbc ",
                      "staphyloc", "e. coli", "escherichia", "candida",
                      "pseudomonas", "bacillus", "streptococ"],
    "anti_inflammatory": ["inflammat", "cox-1", "cox-2", "cyclooxygenase",
                          "tnf", "il-1", "il-6", "nf-kb", "lox",
                          "lipoxygenase", "pla2", "phospholipase"],
    "cytotoxicity": ["cytotox", "cancer", "tumor", "hepg2", "hela",
                     "mcf-7", "a549", "viability", "apoptosis",
                     "antiproliferative", "growth inhibit"],
    "antioxidant": ["antioxid", "dpph", "orac", "abts", "radical",
                    "superoxide", "ros"],
    "anti_tb": ["tuberculosis", "mycobacter", "m. tuberculosis", "mtb"],
}

# Activity record fields to save
ACTIVITY_FIELDS = [
    "inchikey",
    "molecule_chembl_id",
    "molecule_pref_name",
    "target_pref_name",
    "target_organism",
    "target_chembl_id",
    "assay_chembl_id",
    "assay_description",
    "assay_type",
    "standard_type",
    "standard_relation",
    "standard_value",
    "standard_units",
    "pchembl_value",
    "document_chembl_id",
    "document_journal",
    "document_year",
    "doi",
    "is_antiviral",
    "is_dengue_relevant",
    "is_flavivirus_relevant",
    "activity_category",
]


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

class ChEMBLClient:
    """Thin wrapper around ChEMBL REST API with rate limiting."""

    def __init__(self, delay: float = REQUEST_DELAY):
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self.delay = delay
        self._last_request = 0.0

    def _rate_limit(self):
        elapsed = time.time() - self._last_request
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self._last_request = time.time()

    def get(self, url: str, params: Optional[dict] = None,
            retries: int = 3) -> Optional[dict]:
        """GET with rate limiting and retries."""
        for attempt in range(retries):
            self._rate_limit()
            try:
                r = self.session.get(url, params=params, timeout=30)
                if r.status_code == 200:
                    return r.json()
                elif r.status_code == 404:
                    return None
                elif r.status_code == 429:
                    # Rate limited — back off
                    wait = 2 ** (attempt + 1)
                    print(f"  Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                else:
                    print(f"  HTTP {r.status_code} for {url}")
                    if attempt < retries - 1:
                        time.sleep(1)
            except requests.exceptions.RequestException as e:
                print(f"  Request error: {e}")
                if attempt < retries - 1:
                    time.sleep(2)
        return None

    def batch_molecule_lookup(self, inchikeys: list[str]) -> dict[str, dict]:
        """Look up multiple molecules by InChIKey. Returns {inchikey: mol_data}."""
        if not inchikeys:
            return {}

        joined = ";".join(inchikeys)
        url = f"{CHEMBL_BASE}/molecule/set/{joined}.json"
        data = self.get(url)

        results = {}
        if data and "molecules" in data:
            for mol in data["molecules"]:
                structs = mol.get("molecule_structures") or {}
                ik = structs.get("standard_inchi_key")
                if ik:
                    results[ik] = mol
        return results

    def get_activities(self, chembl_id: str) -> list[dict]:
        """Get all bioactivity records for a molecule (handles pagination)."""
        activities = []
        offset = 0

        while True:
            url = f"{CHEMBL_BASE}/activity.json"
            data = self.get(url, params={
                "molecule_chembl_id": chembl_id,
                "limit": ACTIVITY_PAGE_SIZE,
                "offset": offset,
            })

            if not data or "activities" not in data:
                break

            page = data["activities"]
            activities.extend(page)

            meta = data.get("page_meta", {})
            total = meta.get("total_count", 0)

            if offset + len(page) >= total:
                break
            offset += ACTIVITY_PAGE_SIZE

        return activities

    def get_document_doi(self, doc_chembl_id: str) -> Optional[str]:
        """Fetch DOI for a document ChEMBL ID."""
        url = f"{CHEMBL_BASE}/document/{doc_chembl_id}.json"
        data = self.get(url)
        if data:
            return data.get("doi")
        return None


# ---------------------------------------------------------------------------
# Activity classification
# ---------------------------------------------------------------------------

def classify_activity(activity: dict) -> tuple[bool, bool, bool, str]:
    """Classify an activity record.

    Returns (is_antiviral, is_dengue_relevant, is_flavivirus_relevant, category_string).
    """
    target = str(activity.get("target_pref_name", "")).lower()
    organism = str(activity.get("target_organism", "")).lower()
    assay_desc = str(activity.get("assay_description", "")).lower()
    searchable = f"{target} {organism} {assay_desc}"

    is_antiviral = any(kw in searchable for kw in ANTIVIRAL_KEYWORDS)
    is_dengue = any(kw in searchable for kw in DENGUE_KEYWORDS)
    is_flavivirus = is_dengue or any(kw in searchable for kw in FLAVIVIRUS_KEYWORDS)

    categories = []
    if is_antiviral:
        categories.append("antiviral")
    if is_dengue:
        categories.append("dengue")
    if is_flavivirus and not is_dengue:
        categories.append("flavivirus")

    for cat_name, keywords in RELEVANT_CATEGORIES.items():
        if any(kw in searchable for kw in keywords):
            categories.append(cat_name)

    return is_antiviral, is_dengue, is_flavivirus, "|".join(categories) if categories else ""


# ---------------------------------------------------------------------------
# Checkpoint management
# ---------------------------------------------------------------------------

def load_checkpoint() -> dict:
    """Load checkpoint tracking processed InChIKeys."""
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE) as f:
            return json.load(f)
    return {"processed": [], "chembl_map": {}, "stats": {}}


def save_checkpoint(checkpoint: dict):
    """Save checkpoint."""
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(checkpoint, f)


def load_doi_cache() -> dict:
    """Load cached DOI lookups."""
    if DOI_CACHE_FILE.exists():
        with open(DOI_CACHE_FILE) as f:
            return json.load(f)
    return {}


def save_doi_cache(cache: dict):
    """Save DOI cache."""
    with open(DOI_CACHE_FILE, "w") as f:
        json.dump(cache, f)


# ---------------------------------------------------------------------------
# Core enrichment logic
# ---------------------------------------------------------------------------

def run_enrichment(
    test_mode: bool = False,
    resume: bool = False,
    fetch_dois: bool = False,
):
    """Main enrichment pipeline."""

    # Load database
    print(f"Loading database from {DATABASE_CSV}")
    df = pd.read_csv(DATABASE_CSV)
    all_inchikeys = df["inchikey"].tolist()
    print(f"  Total compounds: {len(all_inchikeys)}")

    # In test mode, use a curated set of known bioactive Magnolia compounds
    if test_mode:
        # Pick compounds we know are in ChEMBL from our earlier scan
        test_names = [
            "honokiol", "magnolol", "liriodenine", "parthenolide",
            "ellagic acid", "diazepam", "reticuline",
            "fargesin", "isoeugenol", "elemicin",
        ]
        test_inchikeys = []
        for name in test_names:
            matches = df[df["common_names"].str.contains(name, case=False, na=False)]
            if len(matches) > 0:
                ik = matches.iloc[0]["inchikey"]
                test_inchikeys.append(ik)
                print(f"  Test compound: {name} -> {ik}")

        if not test_inchikeys:
            # Fallback: just use first 10
            test_inchikeys = all_inchikeys[:10]
        all_inchikeys = test_inchikeys
        print(f"  Test mode: {len(all_inchikeys)} compounds")

    # Load checkpoint for resume
    checkpoint = load_checkpoint() if resume else {"processed": [], "chembl_map": {}, "stats": {}}
    processed_set = set(checkpoint.get("processed", []))
    chembl_map = checkpoint.get("chembl_map", {})
    doi_cache = load_doi_cache() if fetch_dois else {}

    # Filter out already-processed
    remaining = [ik for ik in all_inchikeys if ik not in processed_set]
    print(f"  Already processed: {len(processed_set)}")
    print(f"  Remaining: {len(remaining)}")

    if not remaining and not processed_set:
        print("Nothing to process.")
        return

    # Initialize client
    client = ChEMBLClient()

    # --- Phase 1: Molecule lookup (batch) ---
    print("\n=== Phase 1: Molecule lookup ===")
    to_lookup = [ik for ik in remaining if ik not in chembl_map]

    if to_lookup:
        found_count = 0
        for i in range(0, len(to_lookup), MOLECULE_BATCH_SIZE):
            batch = to_lookup[i:i + MOLECULE_BATCH_SIZE]
            batch_num = i // MOLECULE_BATCH_SIZE + 1
            total_batches = (len(to_lookup) + MOLECULE_BATCH_SIZE - 1) // MOLECULE_BATCH_SIZE

            results = client.batch_molecule_lookup(batch)

            for ik in batch:
                if ik in results:
                    mol = results[ik]
                    chembl_map[ik] = mol["molecule_chembl_id"]
                    found_count += 1
                else:
                    chembl_map[ik] = None  # not in ChEMBL

            found_in_batch = sum(1 for ik in batch if chembl_map.get(ik) is not None)
            print(f"  Batch {batch_num}/{total_batches}: {found_in_batch}/{len(batch)} found"
                  f" (cumulative: {found_count})")

            # Save checkpoint periodically
            if batch_num % 10 == 0:
                checkpoint["chembl_map"] = chembl_map
                save_checkpoint(checkpoint)

            time.sleep(BATCH_DELAY)

        checkpoint["chembl_map"] = chembl_map
        save_checkpoint(checkpoint)

    # Summary of lookup results
    in_chembl = {ik: cid for ik, cid in chembl_map.items()
                 if cid is not None and ik in set(remaining) | processed_set}
    not_in_chembl = {ik for ik, cid in chembl_map.items()
                     if cid is None and ik in set(remaining) | processed_set}

    total_queried = len(set(all_inchikeys) & set(chembl_map.keys()))
    total_found = sum(1 for ik in all_inchikeys if chembl_map.get(ik) is not None)
    print(f"\n  Compounds queried: {total_queried}")
    print(f"  Found in ChEMBL: {total_found} ({100*total_found/max(total_queried,1):.1f}%)")

    # --- Phase 2: Activity retrieval ---
    print("\n=== Phase 2: Activity retrieval ===")

    # Load existing activities if resuming
    all_activities = []
    if resume and OUTPUT_ACTIVITIES.exists():
        existing = pd.read_csv(OUTPUT_ACTIVITIES)
        all_activities = existing.to_dict("records")
        print(f"  Loaded {len(all_activities)} existing activity records")

    # Compounds that need activity lookup
    need_activities = [
        ik for ik in remaining
        if chembl_map.get(ik) is not None
    ]
    print(f"  Compounds needing activity lookup: {len(need_activities)}")

    compounds_with_activities = 0
    total_new_activities = 0
    compounds_with_antiviral = 0

    for idx, ik in enumerate(need_activities):
        chembl_id = chembl_map[ik]
        progress = f"[{idx+1}/{len(need_activities)}]"

        activities = client.get_activities(chembl_id)

        if activities:
            compounds_with_activities += 1
            has_antiviral = False

            for act in activities:
                is_antiviral, is_dengue, is_flavivirus, category = classify_activity(act)
                if is_antiviral:
                    has_antiviral = True

                doi = ""
                if fetch_dois:
                    doc_id = act.get("document_chembl_id", "")
                    if doc_id:
                        if doc_id in doi_cache:
                            doi = doi_cache[doc_id] or ""
                        else:
                            doi = client.get_document_doi(doc_id) or ""
                            doi_cache[doc_id] = doi

                record = {
                    "inchikey": ik,
                    "molecule_chembl_id": chembl_id,
                    "molecule_pref_name": act.get("molecule_pref_name", ""),
                    "target_pref_name": act.get("target_pref_name", ""),
                    "target_organism": act.get("target_organism", ""),
                    "target_chembl_id": act.get("target_chembl_id", ""),
                    "assay_chembl_id": act.get("assay_chembl_id", ""),
                    "assay_description": act.get("assay_description", ""),
                    "assay_type": act.get("assay_type", ""),
                    "standard_type": act.get("standard_type", ""),
                    "standard_relation": act.get("standard_relation", ""),
                    "standard_value": act.get("standard_value", ""),
                    "standard_units": act.get("standard_units", ""),
                    "pchembl_value": act.get("pchembl_value", ""),
                    "document_chembl_id": act.get("document_chembl_id", ""),
                    "document_journal": act.get("document_journal", ""),
                    "document_year": act.get("document_year", ""),
                    "doi": doi,
                    "is_antiviral": is_antiviral,
                    "is_dengue_relevant": is_dengue,
                    "is_flavivirus_relevant": is_flavivirus,
                    "activity_category": category,
                }
                all_activities.append(record)

            total_new_activities += len(activities)
            if has_antiviral:
                compounds_with_antiviral += 1

            print(f"  {progress} {chembl_id}: {len(activities)} activities"
                  f" {'[ANTIVIRAL]' if has_antiviral else ''}")
        else:
            print(f"  {progress} {chembl_id}: 0 activities")

        # Mark as processed
        processed_set.add(ik)

        # Save incrementally
        if (idx + 1) % SAVE_EVERY == 0:
            checkpoint["processed"] = list(processed_set)
            save_checkpoint(checkpoint)
            _write_activities(all_activities)
            if fetch_dois:
                save_doi_cache(doi_cache)
            print(f"  ** Checkpoint saved at {idx+1}/{len(need_activities)} **")

    # Mark compounds not in ChEMBL as processed too
    for ik in remaining:
        if chembl_map.get(ik) is None:
            processed_set.add(ik)

    # --- Phase 3: Write outputs ---
    print("\n=== Phase 3: Writing outputs ===")

    _write_activities(all_activities)
    print(f"  Wrote {len(all_activities)} activity records to {OUTPUT_ACTIVITIES}")

    # Build per-compound summary
    _write_summary(all_activities, all_inchikeys, chembl_map)

    # Final checkpoint
    checkpoint["processed"] = list(processed_set)
    checkpoint["chembl_map"] = chembl_map
    checkpoint["stats"] = {
        "total_compounds": len(all_inchikeys),
        "in_chembl": total_found,
        "with_activities": compounds_with_activities,
        "with_antiviral": compounds_with_antiviral,
        "total_activity_records": len(all_activities),
    }
    save_checkpoint(checkpoint)
    if fetch_dois:
        save_doi_cache(doi_cache)

    # --- Report ---
    print("\n" + "=" * 60)
    print("BIOACTIVITY ENRICHMENT REPORT")
    print("=" * 60)
    print(f"Total compounds queried:        {total_queried}")
    print(f"Found in ChEMBL:                {total_found} ({100*total_found/max(total_queried,1):.1f}%)")
    print(f"With bioactivity data:          {compounds_with_activities}")
    print(f"With antiviral activities:       {compounds_with_antiviral}")
    print(f"Total activity records:         {len(all_activities)}")

    # Antiviral breakdown
    if all_activities:
        av_records = [a for a in all_activities if a.get("is_antiviral")]
        dengue_records = [a for a in all_activities if a.get("is_dengue_relevant")]
        flavi_records = [a for a in all_activities if a.get("is_flavivirus_relevant")]
        print(f"\nAntiviral activity records:     {len(av_records)}")
        print(f"Dengue-specific records:        {len(dengue_records)}")
        print(f"Flavivirus-relevant records:    {len(flavi_records)}")

        # Category breakdown
        cats = {}
        for a in all_activities:
            for cat in (a.get("activity_category") or "").split("|"):
                if cat:
                    cats[cat] = cats.get(cat, 0) + 1
        if cats:
            print("\nActivity categories:")
            for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
                print(f"  {cat}: {count} records")

    print(f"\nOutputs:")
    print(f"  Activities: {OUTPUT_ACTIVITIES}")
    print(f"  Summary:    {OUTPUT_SUMMARY}")


def _write_activities(activities: list[dict]):
    """Write activity records to CSV."""
    if not activities:
        return
    act_df = pd.DataFrame(activities)
    # Ensure column order
    cols = [c for c in ACTIVITY_FIELDS if c in act_df.columns]
    extra = [c for c in act_df.columns if c not in ACTIVITY_FIELDS]
    act_df = act_df[cols + extra]
    act_df.to_csv(OUTPUT_ACTIVITIES, index=False)


def _write_summary(activities: list[dict], all_inchikeys: list[str],
                   chembl_map: dict):
    """Write per-compound summary CSV."""
    empty_row = {
        "has_bioactivity": False,
        "bioactivity_count": 0,
        "has_antiviral": False,
        "antiviral_count": 0,
        "has_dengue_relevant": False,
        "dengue_relevant_count": 0,
        "has_flavivirus_relevant": False,
        "flavivirus_relevant_count": 0,
        "best_antiviral_ic50_nM": "",
        "best_antiviral_target": "",
        "best_pchembl": "",
        "activity_categories": "",
        "unique_targets": 0,
        "unique_assays": 0,
    }

    if not activities:
        # Still write an empty summary for all compounds
        summary_rows = []
        for ik in all_inchikeys:
            row = {
                "inchikey": ik,
                "chembl_id": chembl_map.get(ik, ""),
                "in_chembl": chembl_map.get(ik) is not None,
            }
            row.update(empty_row)
            summary_rows.append(row)
        pd.DataFrame(summary_rows).to_csv(OUTPUT_SUMMARY, index=False)
        return

    act_df = pd.DataFrame(activities)

    summary_rows = []
    for ik in all_inchikeys:
        chembl_id = chembl_map.get(ik)
        compound_acts = act_df[act_df["inchikey"] == ik] if ik in act_df["inchikey"].values else pd.DataFrame()

        row = {
            "inchikey": ik,
            "chembl_id": chembl_id or "",
            "in_chembl": chembl_id is not None,
        }

        if len(compound_acts) == 0:
            row.update(empty_row)
        else:
            antiviral_acts = compound_acts[compound_acts["is_antiviral"] == True]
            dengue_acts = compound_acts[compound_acts["is_dengue_relevant"] == True]
            flavi_acts = compound_acts[compound_acts["is_flavivirus_relevant"] == True]

            # Find best antiviral IC50 (lowest value in nM)
            best_ic50 = ""
            best_target = ""
            if len(antiviral_acts) > 0:
                ic50_acts = antiviral_acts[
                    antiviral_acts["standard_type"].isin(["IC50", "EC50", "Ki"])
                    & antiviral_acts["standard_units"].isin(["nM"])
                    & antiviral_acts["standard_value"].notna()
                ]
                if len(ic50_acts) > 0:
                    ic50_vals = pd.to_numeric(ic50_acts["standard_value"], errors="coerce")
                    valid = ic50_vals.dropna()
                    if len(valid) > 0:
                        best_idx = valid.idxmin()
                        best_ic50 = valid[best_idx]
                        best_target = ic50_acts.loc[best_idx, "target_pref_name"]

            # Best pchembl across all activities
            best_pchembl = ""
            pchembl_vals = pd.to_numeric(compound_acts["pchembl_value"], errors="coerce").dropna()
            if len(pchembl_vals) > 0:
                best_pchembl = pchembl_vals.max()

            # Collect categories
            all_cats = set()
            for cats_str in compound_acts["activity_category"].dropna():
                for cat in str(cats_str).split("|"):
                    if cat:
                        all_cats.add(cat)

            row.update({
                "has_bioactivity": True,
                "bioactivity_count": len(compound_acts),
                "has_antiviral": len(antiviral_acts) > 0,
                "antiviral_count": len(antiviral_acts),
                "has_dengue_relevant": len(dengue_acts) > 0,
                "dengue_relevant_count": len(dengue_acts),
                "has_flavivirus_relevant": len(flavi_acts) > 0,
                "flavivirus_relevant_count": len(flavi_acts),
                "best_antiviral_ic50_nM": best_ic50,
                "best_antiviral_target": best_target,
                "best_pchembl": best_pchembl,
                "activity_categories": "|".join(sorted(all_cats)),
                "unique_targets": compound_acts["target_chembl_id"].nunique(),
                "unique_assays": compound_acts["assay_chembl_id"].nunique(),
            })

        summary_rows.append(row)

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(OUTPUT_SUMMARY, index=False)
    print(f"  Wrote {len(summary_df)} compound summaries to {OUTPUT_SUMMARY}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Enrich Magnolia BBB database with ChEMBL bioactivity data"
    )
    parser.add_argument("--test", action="store_true",
                        help="Test mode: run with ~10 known compounds only")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from last checkpoint")
    parser.add_argument("--fetch-dois", action="store_true",
                        help="Also fetch DOIs from document records (slower)")
    args = parser.parse_args()

    run_enrichment(
        test_mode=args.test,
        resume=args.resume,
        fetch_dois=args.fetch_dois,
    )


if __name__ == "__main__":
    main()
