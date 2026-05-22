"""RDKit chemistry helpers: standardization, descriptors, inclusion filters."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from rdkit import Chem, RDLogger
from rdkit.Chem import Descriptors, AllChem, SaltRemover, inchi as InchiMod

from bbb_database_stc.config import (
    MW_MIN, MW_MAX, HEAVY_ATOM_MIN,
    EXCLUDE_INORGANIC, PRIMARY_METABOLITE_INCHIKEYS,
)

RDLogger.DisableLog("rdApp.*")
log = logging.getLogger(__name__)

_salt_remover = SaltRemover.SaltRemover()


@dataclass
class StandardizedMol:
    canonical_smiles: str
    inchi: str
    inchikey: str
    molecular_formula: str
    molecular_weight: float
    exact_mass: float


def standardize_smiles(smiles: str) -> Optional[StandardizedMol]:
    if not smiles or not isinstance(smiles, str):
        return None
    smiles = smiles.strip()
    if not smiles:
        return None

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None

    try:
        mol = _salt_remover.StripMol(mol)
    except Exception:
        pass

    mol = _neutralize(mol)

    try:
        Chem.SanitizeMol(mol)
    except Exception:
        return None

    canon = Chem.MolToSmiles(mol, canonical=True)
    if not canon:
        return None

    inchi_str = InchiMod.MolToInchi(mol)
    if not inchi_str:
        return None
    inchikey = InchiMod.InchiToInchiKey(inchi_str)
    if not inchikey:
        return None

    return StandardizedMol(
        canonical_smiles=canon,
        inchi=inchi_str,
        inchikey=inchikey,
        molecular_formula=Chem.rdMolDescriptors.CalcMolFormula(mol),
        molecular_weight=round(Descriptors.MolWt(mol), 4),
        exact_mass=round(Descriptors.ExactMolWt(mol), 4),
    )


def check_inclusion(smiles: str, inchikey: str = "") -> tuple[bool, str]:
    """Return (passes, rejection_reason). Empty reason = passes."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return False, "unparseable_smiles"

    mw = Descriptors.MolWt(mol)
    if mw < MW_MIN:
        return False, f"mw_below_{MW_MIN}"
    if mw > MW_MAX:
        return False, f"mw_above_{MW_MAX}"

    heavy = mol.GetNumHeavyAtoms()
    if heavy < HEAVY_ATOM_MIN:
        return False, f"heavy_atoms_below_{HEAVY_ATOM_MIN}"

    if EXCLUDE_INORGANIC:
        atoms = {a.GetSymbol() for a in mol.GetAtoms()}
        if "C" not in atoms:
            return False, "inorganic_no_carbon"

    if inchikey and len(inchikey) >= 14:
        prefix = inchikey[:14]
        if prefix in PRIMARY_METABOLITE_INCHIKEYS:
            return False, "primary_metabolite"

    return True, ""


def compute_descriptors(smiles: str) -> dict | None:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None

    logp = Descriptors.MolLogP(mol)
    hba = Descriptors.NumHAcceptors(mol)
    hbd = Descriptors.NumHDonors(mol)
    tpsa = Descriptors.TPSA(mol)
    rot = Descriptors.NumRotatableBonds(mol)
    mw = Descriptors.MolWt(mol)
    rings = Descriptors.RingCount(mol)
    fsp3 = Descriptors.FractionCSP3(mol)
    heavy = mol.GetNumHeavyAtoms()

    lipinski_violations = sum([mw > 500, logp > 5, hba > 10, hbd > 5])

    return {
        "logp": round(logp, 2),
        "hba": hba,
        "hbd": hbd,
        "tpsa": round(tpsa, 2),
        "rotatable_bonds": rot,
        "molecular_weight": round(mw, 4),
        "ring_count": rings,
        "fsp3": round(fsp3, 3),
        "heavy_atom_count": heavy,
        "lipinski_violations": lipinski_violations,
    }


def inchikey_connectivity(inchikey: str) -> str:
    return inchikey[:14] if inchikey and len(inchikey) >= 14 else ""


def _neutralize(mol: Chem.Mol) -> Chem.Mol:
    pattern = Chem.MolFromSmarts(
        "[+1!h0!$([*]~[-1,-2,-3,-4])],"
        "[-1!$([*]~[+1,+2,+3,+4])]"
    )
    if pattern is None:
        return mol
    at_matches = mol.GetSubstructMatches(pattern)
    if not at_matches:
        return mol
    rw = Chem.RWMol(mol)
    for match in at_matches:
        idx = match[0]
        atom = rw.GetAtomWithIdx(idx)
        chg = atom.GetFormalCharge()
        h_count = atom.GetTotalNumHs()
        if chg > 0 and h_count > 0:
            atom.SetFormalCharge(0)
            atom.SetNumExplicitHs(h_count - 1)
        elif chg < 0:
            atom.SetFormalCharge(0)
            atom.SetNumExplicitHs(h_count + 1)
    return rw.GetMol()
