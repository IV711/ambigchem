"""
orchestrator.py

The real differentiator this whole library was built around: given a
compound name, decide WHICH engine (covalent or ionic) should parse it -
not the individual engines themselves, but the routing and
disambiguation logic connecting them.

REAL, CONCRETE PROBLEM FOUND BY TESTING BOTH ENGINES AGAINST THE SAME
INPUT, BEFORE WRITING ANY ROUTING LOGIC: "aluminum oxide" parses
successfully through BOTH engines, but they disagree. covalent.py has no
concept of metal vs. nonmetal - it treats "aluminum" as just another
element and produces the chemically nonsensical "AlO". ionic.py, using
aluminum's real +3 charge, correctly produces "Al2O3". Picking either
engine's result naively would be wrong roughly half the time.

REAL, CHEMISTRY-GROUNDED ROUTING RULES:
    1. An explicit Greek numeric prefix (di, tri, tetra...) anywhere in
       the name is real covalent/molecular naming convention - ionic
       compound names essentially never use these, since their ratios
       come from charge-balancing, not explicit counting words.
    2. A recognized metal cation as the first word, with NO prefix
       present, is conventionally ionic naming.
    3. When rule 2 applies, the ionic engine's verdict is trusted
       ENTIRELY - a confident formula, or a genuine ambiguity - over any
       coincidental covalent success. Found necessary by hand-tracing
       "iron oxide": covalent.py "succeeds" with a spurious "FeO" (iron
       isn't really named via simple covalent counting), which would
       have silently hidden ionic.py's correctly-detected real ambiguity
       (FeO vs Fe2O3) if covalent's answer were allowed to win by
       default. A real, deliberate fix, not an edge case left to chance.
    4. If neither strong signal applies, both engines are tried and
       compared directly.
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from ambigchem.covalent import parse_covalent_name, PREFIXES as COVALENT_PREFIXES
from ambigchem.ionic import parse_ionic_name, FIXED_CATIONS, VARIABLE_CATIONS


@dataclass
class OrchestratorResult:
    formula: str | None
    method: str  # "covalent" | "ionic" | "covalent+ionic agree" | "unresolved" | "ambiguous_engines"
    ambiguous: bool = False
    all_candidates: list[str] | None = None


def _contains_numeric_prefix(name: str) -> bool:
    words = name.lower().split()
    return any(word.startswith(prefix) for word in words for prefix in COVALENT_PREFIXES)


def _first_word_is_recognized_metal(name: str) -> bool:
    first_word = name.lower().split()[0] if name.split() else ""
    first_word = re.sub(r"\(.*\)", "", first_word).strip()  # strip a possible "(iii)"
    return first_word in FIXED_CATIONS or first_word in VARIABLE_CATIONS


def _combine_results(
    cov_formula: str | None, ion_formula: str | None,
    cov_ambiguous: bool, cov_candidates: list[str] | None,
    ion_ambiguous: bool, ion_candidates: list[str] | None,
) -> OrchestratorResult:
    """The direct comparison logic, deliberately separated into its own
    function so the genuine-disagreement detection (rule 4) can be
    tested in isolation, the same discipline as covalent.py's
    _all_prefix_candidates ambiguity proof."""
    if cov_formula and ion_formula:
        if cov_formula == ion_formula:
            return OrchestratorResult(cov_formula, "covalent+ionic agree")
        return OrchestratorResult(None, "ambiguous_engines", ambiguous=True,
                                   all_candidates=[cov_formula, ion_formula])
    if cov_formula:
        return OrchestratorResult(cov_formula, "covalent")
    if ion_formula:
        return OrchestratorResult(ion_formula, "ionic")
    if cov_ambiguous:
        return OrchestratorResult(None, "covalent", ambiguous=True, all_candidates=cov_candidates)
    if ion_ambiguous:
        return OrchestratorResult(None, "ionic", ambiguous=True, all_candidates=ion_candidates)
    return OrchestratorResult(None, "unresolved")


def parse_compound_name(name: str) -> OrchestratorResult:
    has_prefix = _contains_numeric_prefix(name)
    is_metal_first = _first_word_is_recognized_metal(name)

    cov = parse_covalent_name(name)
    ion = parse_ionic_name(name)

    # Rule 1: explicit prefix -> trust covalent.
    if has_prefix and not is_metal_first and cov.formula:
        return OrchestratorResult(cov.formula, "covalent")

    # Rules 2+3: recognized metal, no prefix -> trust ionic ENTIRELY,
    # confident answer or genuine ambiguity, over any coincidental
    # covalent success (the real "iron oxide" fix found by hand-tracing).
    if is_metal_first and not has_prefix:
        if ion.formula:
            return OrchestratorResult(ion.formula, "ionic")
        if ion.ambiguous:
            return OrchestratorResult(None, "ionic", ambiguous=True, all_candidates=ion.all_candidates)

    # Rule 4: no strong, reliable signal - compare both directly.
    return _combine_results(
        cov.formula, ion.formula,
        cov.ambiguous, cov.all_candidates,
        ion.ambiguous, ion.all_candidates,
    )


if __name__ == "__main__":
    test_cases = [
        ("dinitrogen pentoxide", "N2O5", "covalent"),
        ("carbon monoxide", "CO", "covalent"),
        ("aluminum carbonate", "Al2(CO3)3", "ionic"),
        ("sodium chloride", "NaCl", "ionic"),
        ("silicon carbide", "SiC", "covalent"),  # no strong signal, only covalent succeeds
    ]
    all_passed = True
    for name, expected_formula, expected_method in test_cases:
        result = parse_compound_name(name)
        status = "PASS" if (result.formula == expected_formula and result.method == expected_method) else "FAIL"
        if status == "FAIL":
            all_passed = False
        print(f"[{status}] '{name}' -> {result.formula} via {result.method} "
              f"(expected {expected_formula} via {expected_method})")

    print("\n=== THE motivating case: covalent 'succeeds' wrongly, ionic must win ===")
    result = parse_compound_name("aluminum oxide")
    print(f"'aluminum oxide' -> {result.formula} via {result.method}")
    assert result.formula == "Al2O3" and result.method == "ionic"
    print("PASS - the real fix this orchestrator exists for\n")

    print("=== Genuine ionic ambiguity must survive even though covalent also succeeds ===")
    result = parse_compound_name("iron oxide")
    print(f"'iron oxide' -> ambiguous={result.ambiguous}, candidates={result.all_candidates}, method={result.method}")
    assert result.ambiguous is True and set(result.all_candidates) == {"FeO", "Fe2O3"}
    print("PASS - real ambiguity not silently hidden by a spurious covalent success\n")

    print("=== Direct proof: genuine engine-level disagreement is detected, not guessed ===")
    forced = _combine_results("AlO", "Al2O3", False, None, False, None)
    print(f"Forced disagreement (AlO vs Al2O3) -> {forced}")
    assert forced.ambiguous is True and set(forced.all_candidates) == {"AlO", "Al2O3"}
    print("PASS\n")

    print("ALL TESTS PASSED" if all_passed else "SOME TESTS FAILED")
