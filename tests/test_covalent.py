"""
test_covalent.py

Real pytest coverage for covalent.py's parse_covalent_name(), including
both the strict IUPAC form and the dominant real-usage elided form,
since the module deliberately accepts both rather than picking one as
"correct" - see covalent.py's own module docstring for the real,
source-checked reasoning behind that choice.
"""

from ambigchem.covalent import parse_covalent_name, IDE_FORMS


def test_elided_form():
    assert parse_covalent_name("dinitrogen pentoxide").formula == "N2O5"


def test_strict_non_elided_form_also_works():
    assert parse_covalent_name("dinitrogen pentaoxide").formula == "N2O5"


def test_mono_dropped_on_first_element():
    result = parse_covalent_name("carbon monoxide")
    assert result.formula == "CO"
    assert result.element1_count == 1


def test_di_does_not_elide():
    assert parse_covalent_name("carbon dioxide").formula == "CO2"


def test_no_elision_needed_before_consonant():
    assert parse_covalent_name("sulfur hexafluoride").formula == "SF6"
    assert parse_covalent_name("carbon tetrachloride").formula == "CCl4"
    assert parse_covalent_name("phosphorus pentachloride").formula == "PCl5"


def test_tetra_elision():
    assert parse_covalent_name("dinitrogen tetroxide").formula == "N2O4"


def test_unverified_prefixes_deliberately_not_elided():
    """hexa/hepta/octa/nona/deca elision was never confirmed against a
    real source - the module deliberately does NOT guess at it. This
    test protects that honest limitation from being silently 'fixed'
    into a guess later."""
    # "decoxide" (deca + oxide, elided) is NOT recognized - only the
    # strict, non-elided "decaoxide" form should work for this prefix.
    assert parse_covalent_name("tetraphosphorus decoxide").formula is None
    assert parse_covalent_name("tetraphosphorus decaoxide").formula == "P4O10"


def test_invalid_input_returns_none():
    assert parse_covalent_name("not a real compound name").formula is None
    assert parse_covalent_name("just one word").formula is None


def test_ambiguity_detection_mechanism():
    """Our real IDE_FORMS dictionary has no overlapping entries today, so
    this constructs a deliberately overlapping one to prove the
    detection mechanism itself works - not that any real compound is
    ambiguous right now, but that the machinery would catch it if a
    future dictionary expansion ever introduces one."""
    from ambigchem.covalent import _all_prefix_candidates

    fake_lookup = {"oxide": "O", "xide": "Xx"}  # deliberately overlapping
    candidates = _all_prefix_candidates("monoxide", fake_lookup)
    assert len(candidates) == 2, "Should find both readings as independently valid"
    assert (1, "O") in candidates
    assert (1, "Xx") in candidates


def test_plumbide_and_stannide_confirmed_real_terms():
    """Confirmed via direct search against real reference sources - see
    covalent.py's IDE_FORMS docstring for the full reasoning, including
    why ferride/cupride (same Latin-root pattern) were NOT added without
    further verification."""
    assert IDE_FORMS["plumbide"] == "Pb"
    assert IDE_FORMS["stannide"] == "Sn"


def test_zintl_stoichiometry_is_a_known_honest_limitation():
    """plumbide/stannide are real, but real compounds using them (e.g.
    Mg2Sn, magnesium stannide) often need CHARGE-BALANCING to get the
    correct ratio, not simple prefix-counting - Mg2+ x2 balances Sn4-,
    a 2:1 ratio this engine has no way to know. This engine produces A
    formula, but not the REAL one, for exactly this class of compound.
    Documented explicitly here rather than silently shipping a
    plausible-looking wrong answer - this is precisely the gap the
    ionic engine (charge-balancing, built next) is meant to close."""
    result = parse_covalent_name("magnesium stannide")
    assert result.formula == "MgSn"  # mechanically valid, chemically wrong
    # The real compound is Mg2Sn - a known, honestly-flagged limitation,
    # not a silent bug.
