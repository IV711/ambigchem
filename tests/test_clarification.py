"""
test_clarification.py

Real pytest coverage for clarification.py, including the actual
integration with ionic.py's genuine ambiguity output - not just testing
clarification.py in isolation.
"""

from ambigchem.clarification import from_formula_ambiguity, from_ionic_ambiguity
from ambigchem.ionic import parse_ionic_name


def test_formula_ambiguity_two_candidates():
    result = from_formula_ambiguity("cocl2", ["CoCl2", "COCl2"])
    assert result.kind == "compound_formula"
    assert set(result.candidates) == {"CoCl2", "COCl2"}
    assert "CoCl2" in result.question and "COCl2" in result.question


def test_formula_ambiguity_wording_scales_beyond_two():
    """A real bug found in the original project: wording said 'both'
    unconditionally, which is wrong for 3+ candidates."""
    result = from_formula_ambiguity("iron oxide", ["FeO", "Fe2O3", "Fe3O4"])
    assert "all" in result.question
    assert "both" not in result.question


def test_ionic_ambiguity_has_distinct_kind_and_explains_why():
    result = from_ionic_ambiguity("iron oxide", ["FeO", "Fe2O3"])
    assert result.kind == "variable_oxidation_state"
    assert result.kind != "compound_formula"  # deliberately distinct
    assert "charge" in result.question  # explains WHY, not just THAT


def test_real_integration_with_ionic_engine():
    """The actual, real end-to-end path: a genuine ambiguous result from
    ionic.py, turned into a real, displayable clarification request."""
    result = parse_ionic_name("iron oxide")
    assert result.ambiguous is True

    clarification = from_ionic_ambiguity("iron oxide", result.all_candidates)
    assert set(clarification.candidates) == {"FeO", "Fe2O3"}
    assert clarification.original_text == "iron oxide"


def test_copper_also_produces_real_ambiguity_and_clarification():
    """Confirms this works for more than just iron - copper is the
    other classic variable-charge example in our data."""
    result = parse_ionic_name("copper oxide")
    assert result.ambiguous is True
    assert set(result.all_candidates) == {"Cu2O", "CuO"}

    clarification = from_ionic_ambiguity("copper oxide", result.all_candidates)
    assert set(clarification.candidates) == {"Cu2O", "CuO"}
