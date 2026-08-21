"""
test_ionic.py

Real pytest coverage for parse_ionic_name(), including the genuine,
algorithmic ambiguity-detection trigger for variable-charge metals - the
core motivation behind building this engine in the first place.
"""

from ambigchem.ionic import parse_ionic_name


def test_original_worked_example():
    """The exact example this engine's design was built around."""
    result = parse_ionic_name("aluminum carbonate")
    assert result.formula == "Al2(CO3)3"
    assert result.ambiguous is False


def test_polyatomic_cation_gets_parentheses():
    """Found by hand-tracing before writing any code: naively only
    handling parentheses on the anion side would produce the nonsensical
    'NH42SO4' instead of the real '(NH4)2SO4'."""
    assert parse_ionic_name("ammonium sulfate").formula == "(NH4)2SO4"


def test_roman_numeral_resolves_variable_charge():
    assert parse_ionic_name("iron(III) oxide").formula == "Fe2O3"
    assert parse_ionic_name("iron(II) oxide").formula == "FeO"
    assert parse_ionic_name("copper(I) oxide").formula == "Cu2O"
    assert parse_ionic_name("copper(II) oxide").formula == "CuO"


def test_invalid_roman_numeral_charge_fails_cleanly():
    """Iron has no real +5 state in our data - specifying it should
    fail, not silently ignore the Roman numeral."""
    assert parse_ionic_name("iron(V) oxide").formula is None


def test_simple_fixed_charge_compounds():
    assert parse_ionic_name("sodium chloride").formula == "NaCl"
    assert parse_ionic_name("magnesium nitride").formula == "Mg3N2"


def test_polyatomic_anion_gets_parentheses():
    assert parse_ionic_name("calcium hydroxide").formula == "Ca(OH)2"


def test_genuine_algorithmic_ambiguity_no_database_needed():
    """The actual point of this engine: a variable-charge metal named
    with no Roman numeral is a real, deterministic trigger for ambiguity
    - known purely from the periodic table, not from checking any
    external source. Iron could be +2 or +3; both give real, different,
    valid formulas."""
    result = parse_ionic_name("iron oxide")
    assert result.formula is None
    assert result.ambiguous is True
    assert set(result.all_candidates) == {"FeO", "Fe2O3"}


def test_invalid_input_returns_none():
    assert parse_ionic_name("not a real compound").formula is None
    assert parse_ionic_name("justoneword").formula is None
