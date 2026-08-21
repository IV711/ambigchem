"""
test_orchestrator.py

Real pytest coverage for parse_compound_name() - the routing layer
deciding between covalent.py and ionic.py. Includes explicit regression
tests for two subtle bugs found by hand-tracing during design, before
any code was run: covalent.py silently producing a wrong-but-plausible
answer for a metal oxide, and a genuine ionic ambiguity being hidden by
a spurious covalent success.
"""

from ambigchem.orchestrator import parse_compound_name, _combine_results


def test_covalent_prefix_routes_correctly():
    result = parse_compound_name("dinitrogen pentoxide")
    assert result.formula == "N2O5"
    assert result.method == "covalent"


def test_metal_first_no_prefix_routes_to_ionic():
    result = parse_compound_name("sodium chloride")
    assert result.formula == "NaCl"
    assert result.method == "ionic"


def test_polyatomic_anion_only_covalent_cannot_parse():
    """'carbonate' isn't a real IDE_FORMS entry, so covalent.py can't
    parse this at all - only ionic.py can."""
    result = parse_compound_name("aluminum carbonate")
    assert result.formula == "Al2(CO3)3"
    assert result.method == "ionic"


def test_the_motivating_bug_covalent_succeeds_wrongly():
    """THE real problem this whole module exists to solve, found by
    testing both engines against the same input before writing any
    routing logic: covalent.py has no concept of metal vs. nonmetal and
    produces the nonsensical 'AlO'; ionic.py correctly produces the real
    'Al2O3'. The routing layer must prefer ionic here, not whichever
    engine happens to run first."""
    result = parse_compound_name("aluminum oxide")
    assert result.formula == "Al2O3"
    assert result.method == "ionic"


def test_genuine_ambiguity_survives_a_spurious_covalent_success():
    """A subtler bug found by hand-tracing: iron oxide's genuine
    ambiguity (FeO or Fe2O3, from iron's real variable charge) must not
    be silently hidden just because covalent.py also happens to produce
    SOME answer (a coincidentally-plausible but chemically spurious
    'FeO', since iron isn't really named via simple covalent counting)."""
    result = parse_compound_name("iron oxide")
    assert result.formula is None
    assert result.ambiguous is True
    assert set(result.all_candidates) == {"FeO", "Fe2O3"}
    assert result.method == "ionic"


def test_no_strong_signal_falls_back_to_whichever_engine_succeeds():
    """Silicon isn't a recognized ionic cation (silicon carbide is a
    real covalent network solid, not an ionic compound) and no prefix is
    present - neither strong routing signal applies, so this exercises
    the direct fallback comparison path."""
    result = parse_compound_name("silicon carbide")
    assert result.formula == "SiC"
    assert result.method == "covalent"


def test_genuine_engine_disagreement_detected_directly():
    """Direct, isolated proof of the comparison logic itself - the same
    discipline as covalent.py's deliberately-constructed ambiguity test.
    Forces a disagreement rather than relying on real data happening to
    produce one, since the routing rules are specifically designed to
    avoid ever needing this fallback for well-known real cases."""
    result = _combine_results("AlO", "Al2O3", False, None, False, None)
    assert result.ambiguous is True
    assert result.method == "ambiguous_engines"
    assert set(result.all_candidates) == {"AlO", "Al2O3"}


def test_both_engines_agreeing_is_a_real_possible_outcome():
    result = _combine_results("NaCl", "NaCl", False, None, False, None)
    assert result.formula == "NaCl"
    assert result.ambiguous is False


def test_invalid_input_returns_unresolved():
    result = parse_compound_name("not a real compound at all")
    assert result.formula is None
    assert result.method == "unresolved"
