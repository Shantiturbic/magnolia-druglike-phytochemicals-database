"""Magnolia species taxonomy: name resolution and synonyms."""

from __future__ import annotations

import re

from bbb_database_stc.config import SYNONYM_MAP, OLD_GENUS_NAMES


def normalize_species(name: str) -> str:
    name = name.strip()
    return SYNONYM_MAP.get(name, name)


def is_magnolia_genus(name: str) -> bool:
    name = normalize_species(name)
    lower = name.lower()
    if lower.startswith("magnolia "):
        return True
    for syn_target in SYNONYM_MAP.values():
        if syn_target.lower() == lower:
            return True
    return False


_OLD_GENUS_PATTERN = "|".join(re.escape(g) for g in OLD_GENUS_NAMES)


def extract_species_from_text(text: str) -> list[str]:
    pattern = rf"(?:Magnolia|M\.|{_OLD_GENUS_PATTERN})\s+[a-z][a-z\-]+"
    matches = re.findall(pattern, text)
    results = []
    for m in matches:
        if m.startswith("M. "):
            m = "Magnolia " + m[3:]
        normalized = normalize_species(m)
        if is_magnolia_genus(normalized):
            results.append(normalized)
    return list(set(results))
