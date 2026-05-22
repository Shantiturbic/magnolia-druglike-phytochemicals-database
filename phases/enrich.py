"""Phase 4: Enrichment — molecular descriptors, NP classification, drug-likeness.

Reads the standardized database, adds:
  1. RDKit descriptors (LogP, TPSA, HBA, HBD, rotatable bonds, Fsp3, rings)
  2. NP Classifier annotations (from COCONUT provenance → heuristic fallback)
  3. Lipinski/Veber compliance
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path

from bbb_database_stc.config import OUTPUT_DIR, RAW_DIR
from bbb_database_stc.utils.chem import compute_descriptors

log = logging.getLogger(__name__)

ENRICHED_FIELDS = [
    "inchikey", "inchikey_connectivity", "canonical_smiles", "inchi",
    "iupac_name", "common_names", "molecular_formula", "molecular_weight",
    "evidence_tier", "source_count", "source_list",
    "species_list", "species_count",
    "compound_class", "compound_superclass", "np_pathway",
    "logp", "tpsa", "hba", "hbd", "rotatable_bonds",
    "ring_count", "fsp3", "heavy_atom_count",
    "lipinski_violations",
    "doi_refs", "reference_count",
]

NAME_CLASSIFICATION: dict[str, tuple[str, str, str]] = {
    "magnolol": ("Shikimates and Phenylpropanoids", "Lignans", "Neolignans"),
    "honokiol": ("Shikimates and Phenylpropanoids", "Lignans", "Neolignans"),
    "obovatol": ("Shikimates and Phenylpropanoids", "Lignans", "Neolignans"),
    "4-o-methylhonokiol": ("Shikimates and Phenylpropanoids", "Lignans", "Neolignans"),
    "magnolin": ("Shikimates and Phenylpropanoids", "Lignans", "Furanoid lignans"),
    "fargesin": ("Shikimates and Phenylpropanoids", "Lignans", "Furanoid lignans"),
    "eudesmin": ("Shikimates and Phenylpropanoids", "Lignans", "Furanoid lignans"),
    "kobusin": ("Shikimates and Phenylpropanoids", "Lignans", "Furanoid lignans"),
    "sesamin": ("Shikimates and Phenylpropanoids", "Lignans", "Furanoid lignans"),
    "syringaresinol": ("Shikimates and Phenylpropanoids", "Lignans", "Furofuran lignans"),
    "pinoresinol": ("Shikimates and Phenylpropanoids", "Lignans", "Furofuran lignans"),
    "magnoflorine": ("Alkaloids", "Isoquinoline alkaloids", "Protoberberine alkaloids"),
    "magnocurarine": ("Alkaloids", "Isoquinoline alkaloids", "Bisbenzylisoquinoline alkaloids"),
    "liriodenine": ("Alkaloids", "Isoquinoline alkaloids", "Aporphine alkaloids"),
    "anonaine": ("Alkaloids", "Isoquinoline alkaloids", "Aporphine alkaloids"),
    "roemerine": ("Alkaloids", "Isoquinoline alkaloids", "Aporphine alkaloids"),
    "boldine": ("Alkaloids", "Isoquinoline alkaloids", "Aporphine alkaloids"),
    "glaucine": ("Alkaloids", "Isoquinoline alkaloids", "Aporphine alkaloids"),
    "isocorydine": ("Alkaloids", "Isoquinoline alkaloids", "Aporphine alkaloids"),
    "nornuciferine": ("Alkaloids", "Isoquinoline alkaloids", "Aporphine alkaloids"),
    "dicentrine": ("Alkaloids", "Isoquinoline alkaloids", "Aporphine alkaloids"),
    "costunolide": ("Terpenoids", "Sesquiterpenoids", "Germacrane sesquiterpenoids"),
    "parthenolide": ("Terpenoids", "Sesquiterpenoids", "Germacrane sesquiterpenoids"),
    "micheliolide": ("Terpenoids", "Sesquiterpenoids", "Guaianolides"),
    "quercetin": ("Polyketides", "Flavonoids", "Flavonols"),
    "kaempferol": ("Polyketides", "Flavonoids", "Flavonols"),
    "rutin": ("Polyketides", "Flavonoids", "Flavonol glycosides"),
    "eugenol": ("Shikimates and Phenylpropanoids", "Phenylpropanoids", "Allylphenols"),
}


def _load_coconut_npc_map() -> dict[str, tuple[str, str, str]]:
    """Build InChIKey→(pathway, superclass, class) from COCONUT raw CSV extra fields."""
    npc: dict[str, tuple[str, str, str]] = {}
    coconut_csv = RAW_DIR / "coconut.csv"
    if not coconut_csv.exists():
        return npc

    try:
        with open(coconut_csv, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ik = row.get("inchikey", "").strip()
                if not ik or len(ik) < 14:
                    continue
                # NP Classifier annotations stored in extra JSON if collector saved them
                # But raw CSV doesn't have extra column — check for direct columns
                # COCONUT collector writes standard fields only to CSV
                pass
    except Exception:
        pass

    # Check if any meta has NPC annotations stored separately
    coconut_meta = RAW_DIR / "coconut.meta.json"
    if coconut_meta.exists():
        try:
            with open(coconut_meta) as f:
                meta = json.load(f)
                log.info("COCONUT meta: %s", meta.get("status", "unknown"))
        except Exception:
            pass

    return npc


def _classify_by_name(names: str) -> tuple[str, str, str]:
    """Classify compound by matching known compound names."""
    for name in names.lower().split("|"):
        name = name.strip()
        for key, classification in NAME_CLASSIFICATION.items():
            if key in name:
                return classification
    return ("", "", "")


def run(output_dir: Path | None = None) -> dict:
    output_dir = output_dir or OUTPUT_DIR
    db_path = output_dir / "magnolia_bbb_database.csv"
    if not db_path.exists():
        log.error("Database not found: %s. Run standardize first.", db_path)
        return {"enriched": 0}

    with open(db_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    log.info("=== Phase 4: Enrichment (%d compounds) ===", len(rows))

    coconut_npc = _load_coconut_npc_map()
    log.info("COCONUT NPC annotations available: %d", len(coconut_npc))

    classified = 0
    for i, row in enumerate(rows):
        smiles = row.get("canonical_smiles", "")
        ik = row.get("inchikey", "")

        desc = compute_descriptors(smiles) if smiles else None
        if desc:
            row["logp"] = desc["logp"]
            row["hba"] = desc["hba"]
            row["hbd"] = desc["hbd"]
            row["tpsa"] = desc["tpsa"]
            row["rotatable_bonds"] = desc["rotatable_bonds"]
            row["ring_count"] = desc["ring_count"]
            row["fsp3"] = desc["fsp3"]
            row["heavy_atom_count"] = desc["heavy_atom_count"]
            row["lipinski_violations"] = desc["lipinski_violations"]
        else:
            for k in ["logp", "hba", "hbd", "tpsa", "rotatable_bonds",
                       "ring_count", "fsp3", "heavy_atom_count", "lipinski_violations"]:
                row[k] = ""

        pathway, superclass, compound_class = "", "", ""

        if ik and ik in coconut_npc:
            pathway, superclass, compound_class = coconut_npc[ik]

        if not compound_class:
            names = row.get("common_names", "")
            pathway, superclass, compound_class = _classify_by_name(names)

        row["np_pathway"] = pathway
        row["compound_superclass"] = superclass
        row["compound_class"] = compound_class
        if compound_class:
            classified += 1

        if (i + 1) % 200 == 0:
            log.info("  Enriched %d/%d", i + 1, len(rows))

    with open(db_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ENRICHED_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    lipinski_ok = sum(1 for r in rows if str(r.get("lipinski_violations", "")) in ("0", "1"))
    drug_like = sum(1 for r in rows
                    if r.get("molecular_weight")
                    and 200 <= float(r.get("molecular_weight", 0)) <= 500)

    result = {
        "enriched": len(rows),
        "classified": classified,
        "unclassified": len(rows) - classified,
        "lipinski_compliant": lipinski_ok,
        "drug_like_200_500": drug_like,
    }
    log.info("Enriched %d compounds: %d classified, %d Lipinski-compliant, %d drug-like",
             len(rows), classified, lipinski_ok, drug_like)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = run()
    print(json.dumps(result, indent=2))
