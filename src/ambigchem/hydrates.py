"""
hydrates.py

Parses real crystalline hydrate names - e.g. "copper(II) sulfate
pentahydrate" -> CuSO4·5H2O. A well-defined, real, well-known 3-word
naming pattern (base compound name + Greek-prefixed "hydrate"), NOT an
attempt at open-ended, general 3+-word compound support - that remains a
genuine, honest, unaddressed limitation for names that don't follow this
specific pattern.

Reuses orchestrator.parse_compound_name() for the base compound and
covalent.py's own, already-tested PREFIXES dict for the water count -
no new element or prefix data invented here.

Real, standard hydrate formula notation uses a middle dot (·) between
the base formula and the water count (e.g. "CuSO4·5H2O") - the same
convention used throughout real chemistry literature and databases.
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from ambigchem.covalent import PREFIXES

_HYDRATE_PATTERN = re.compile(
    r"^(" + "|".join(PREFIXES.keys()) + r")?hydrate$", re.IGNORECASE
)


@dataclass
class HydrateParseResult:
    formula: str | None
    base_formula: str | None = None
    water_count: int | None = None
    ambiguous: bool = False
    all_candidates: list[str] | None = None


def parse_hydrate_name(name: str) -> HydrateParseResult:
    """Parses "[base compound name] [prefix]hydrate" into a real hydrate
    formula. Propagates genuine base-compound ambiguity (e.g. if the
    base name itself were ambiguous) by applying the hydrate suffix to
    every real candidate, rather than picking one."""
    words = name.strip().split()
    if len(words) < 3:
        return HydrateParseResult(None)

    last_word = words[-1].lower()
    match = _HYDRATE_PATTERN.match(last_word)
    if not match:
        return HydrateParseResult(None)

    prefix = match.group(1)
    water_count = PREFIXES[prefix] if prefix else 1  # bare "hydrate" implies 1 - rare, but real

    base_name = " ".join(words[:-1])
    from ambigchem.orchestrator import parse_compound_name
    base_result = parse_compound_name(base_name)

    if base_result.ambiguous:
        candidates = [f"{c}\u00b7{water_count}H2O" for c in base_result.all_candidates]
        return HydrateParseResult(None, water_count=water_count, ambiguous=True, all_candidates=candidates)

    if base_result.formula:
        formula = f"{base_result.formula}\u00b7{water_count}H2O"
        return HydrateParseResult(formula, base_formula=base_result.formula, water_count=water_count)

    return HydrateParseResult(None)


if __name__ == "__main__":
    test_cases = [
        ("copper(II) sulfate pentahydrate", "CuSO4\u00b75H2O"),
        ("magnesium sulfate heptahydrate", "MgSO4\u00b77H2O"),  # real: Epsom salt
        ("calcium chloride dihydrate", "CaCl2\u00b72H2O"),
    ]
    all_passed = True
    for name, expected in test_cases:
        result = parse_hydrate_name(name)
        status = "PASS" if result.formula == expected else "FAIL"
        if status == "FAIL":
            all_passed = False
        print(f"[{status}] '{name}' -> {result.formula} (expected {expected})")
    print("ALL TESTS PASSED" if all_passed else "SOME TESTS FAILED")
