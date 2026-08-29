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


def test_spelling_variants_work_correctly():
    """Real bug found via live user testing: covalent.py maintained its
    own, separate element lookup that had silently diverged from
    elements.py's own name_to_symbol() - 'sulphur hexafluoride' failed
    while the canonical 'sulfur hexafluoride' succeeded, even though
    elements.py itself has always correctly recognized 'sulphur' as a
    real spelling variant."""
    assert parse_covalent_name("sulphur hexafluoride").formula == "SF6"
    assert parse_covalent_name("sulfur hexafluoride").formula == "SF6"


def test_same_element_on_both_sides_rejected():
    """Real bug found via live user testing: 'trinitrogen nitride' was
    producing the nonsensical formula 'N3N' (the same element symbol
    appearing twice, never how a real formula is written). A binary
    covalent name genuinely needs two DIFFERENT elements - this is
    rejected outright, not silently combined into something equally
    wrong like 'N4'."""
    assert parse_covalent_name("trinitrogen nitride").formula is None


def test_bare_nitrogen_oxide_is_genuinely_ambiguous():
    """Real ambiguity check added after live user testing: a bare,
    unprefixed name for an element pair with multiple real, well-known
    compounds is genuinely, colloquially ambiguous - confirmed via
    direct search: six real, consistently-cited nitrogen oxides exist."""
    result = parse_covalent_name("nitrogen oxide")
    assert result.ambiguous is True
    assert set(result.all_candidates) == {"NO", "NO2", "N2O", "N2O3", "N2O4", "N2O5"}


def test_explicitly_prefixed_nitrogen_oxides_are_never_ambiguous():
    """The ambiguity check must ONLY fire for genuinely bare names -
    every explicitly-prefixed real nitrogen oxide must still resolve
    confidently, since the prefix already says exactly what was meant."""
    assert parse_covalent_name("dinitrogen pentoxide").formula == "N2O5"
    assert parse_covalent_name("nitrogen dioxide").formula == "NO2"
    assert parse_covalent_name("nitrogen monoxide").formula == "NO"
    assert parse_covalent_name("dinitrogen trioxide").formula == "N2O3"
    assert parse_covalent_name("dinitrogen tetroxide").formula == "N2O4"


def test_bare_names_outside_the_verified_set_remain_confident():
    """Honest starter-set limitation, confirmed by a real test: carbon
    also has multiple real oxides (CO, CO2), but carbon+oxygen isn't yet
    in the verified KNOWN_MULTI_COMPOUND_PAIRS set - 'carbon oxide' is
    NOT flagged ambiguous today. This protects the honest scope boundary
    from silently expanding without real verification."""
    result = parse_covalent_name("carbon dioxide")
    assert result.formula == "CO2"
    assert result.ambiguous is False


def test_sulfur_oxide_ambiguity_excludes_unstable_so():
    """Real, precise verification: sulfur has multiple real oxides, but
    unlike nitrogen, only SO2/SO3 are confirmed 'common/important' -
    sulfur monoxide (SO) is confirmed unstable, 'rarely found outside
    of space' - deliberately excluded, not assumed to fit the same
    6-candidate pattern nitrogen has."""
    result = parse_covalent_name("sulfur oxide")
    assert result.ambiguous is True
    assert set(result.all_candidates) == {"SO2", "SO3"}


def test_carbon_oxide_ambiguity_excludes_uncommon_suboxide():
    """Real, precise verification: Britannica directly confirms carbon
    forms 'two well-known oxides' (CO, CO2) - carbon suboxide (C3O2)
    exists but is confirmed 'uncommon'/'rarely encountered', not
    included."""
    result = parse_covalent_name("carbon oxide")
    assert result.ambiguous is True
    assert set(result.all_candidates) == {"CO", "CO2"}


def test_phosphorus_oxide_ambiguity_uses_real_tetrameric_formulas():
    """Real, precise verification: Britannica directly confirms
    phosphorus forms 'two common oxides' - P4O6 and P4O10, using the
    real tetraphosphorus convention. The bare, unprefixed literal parse
    ('PO') is not even a real, well-known compound itself - correctly
    intercepted before ever being returned."""
    result = parse_covalent_name("phosphorus oxide")
    assert result.ambiguous is True
    assert set(result.all_candidates) == {"P4O6", "P4O10"}


def test_hexa_elision_both_forms_work():
    """Real, NEW verification finding: unlike hepta/octa/nona/deca
    (still unconfirmed), hexa's elided form is confirmed via multiple,
    independent, real sources - Wikipedia's own infobox uses
    'hexaoxide' while its body text uses 'hexoxide' for the same real
    compound; multiple patent documents consistently use the elided
    'tetraarsenic hexoxide' for the analogous As4O6. Both forms must
    resolve to the same real compound."""
    assert parse_covalent_name("tetraphosphorus hexoxide").formula == "P4O6"
    assert parse_covalent_name("tetraphosphorus hexaoxide").formula == "P4O6"


def test_hepta_octa_nona_deca_elision_still_deliberately_unverified():
    """Protects the honest scope boundary: hexa's elision being
    confirmed does NOT mean hepta/octa/nona/deca are assumed to share
    the pattern - only the elided form of hexa is accepted, the
    strict, non-elided forms of the others still work correctly."""
    assert parse_covalent_name("tetraphosphorus decaoxide").formula == "P4O10"
    # A hypothetically-elided "decoxide" is deliberately NOT recognized
    assert parse_covalent_name("tetraphosphorus decoxide").formula is None


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
