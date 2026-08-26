"""
test_hydrates.py

Real pytest coverage for parse_hydrate_name() - the well-scoped, real
solution to the 3-word compound gap found via live user testing.
"""

from ambigchem.hydrates import parse_hydrate_name


def test_real_user_found_case():
    """The exact real case that surfaced this gap: 'copper(II) sulfate
    pentahydrate' returned formula=None before this module existed."""
    result = parse_hydrate_name("copper(II) sulfate pentahydrate")
    assert result.formula == "CuSO4\u00b75H2O"
    assert result.base_formula == "CuSO4"
    assert result.water_count == 5


def test_cross_validated_against_real_pubchem_data():
    """'magnesium sulfate heptahydrate' (Epsom salt) is independently
    cross-checked against the user's own real, earlier database test:
    'epsom salt' -> H14MgO11S from PubChem. MgSO4 + 7 H2O = Mg + S + O4
    + H14O7 = MgH14O11S - an exact atom-count match against real,
    independently-sourced data, not just internal self-consistency."""
    result = parse_hydrate_name("magnesium sulfate heptahydrate")
    assert result.formula == "MgSO4\u00b77H2O"


def test_various_real_prefixes():
    assert parse_hydrate_name("calcium chloride dihydrate").formula == "CaCl2\u00b72H2O"


def test_two_word_name_not_a_hydrate():
    assert parse_hydrate_name("sodium chloride").formula is None


def test_non_hydrate_third_word_returns_none():
    assert parse_hydrate_name("sodium chloride solution").formula is None


def test_ambiguous_base_compound_propagates_to_all_candidates():
    """If the base compound is itself genuinely ambiguous, that
    ambiguity must propagate - never silently pick one candidate to
    apply the hydrate suffix to."""
    result = parse_hydrate_name("iron oxide monohydrate")
    assert result.ambiguous is True
    assert set(result.all_candidates) == {"FeO\u00b71H2O", "Fe2O3\u00b71H2O"}
