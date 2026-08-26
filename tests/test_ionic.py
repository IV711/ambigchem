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


def test_scandium_fixed_charge_confirmed_by_real_search():
    """Confirmed via direct search: scandium appears consistently with
    NO Roman numeral across real compound listings, consistent with its
    well-established, always-+3 behavior, much like aluminum."""
    assert parse_ionic_name("scandium chloride").formula == "ScCl3"


def test_new_variable_cations_confirmed_by_real_search():
    """titanium, chromium, cobalt, manganese, nickel - added after real
    search evidence (explicit Roman-numeral usage in real compound
    listings), not assumed from the regular naming pattern alone."""
    assert parse_ionic_name("titanium(IV) chloride").formula == "TiCl4"  # real: titanium tetrachloride
    assert parse_ionic_name("chromium(II) chloride").formula == "CrCl2"
    assert parse_ionic_name("chromium(III) chloride").formula == "CrCl3"
    assert parse_ionic_name("cobalt(III) oxide").formula == "Co2O3"


def test_titanium_oxide_is_a_new_real_ambiguity_case():
    """A genuinely new ambiguity this expansion enables: titanium could
    be +3 or +4 (TiO2, titanium dioxide, is the far more commonly known
    compound in casual usage - but algorithmically, without an explicit
    oxidation state, both Ti2O3 and TiO2 are real, valid readings, and
    flagging this honestly is more correct than silently assuming the
    more 'famous' answer)."""
    result = parse_ionic_name("titanium oxide")
    assert result.ambiguous is True
    assert set(result.all_candidates) == {"Ti2O3", "TiO2"}


def test_dichromate_and_permanganate():
    """Real gap found via live user testing: 'potassium dichromate' and
    'potassium permanganate' both correctly formula-computed via the
    organic/OPSIN path (a valid answer, but via an unexpected mechanism
    and misleading method label for real ionic compounds) - now
    resolved correctly and directly via ionic.py instead."""
    assert parse_ionic_name("potassium dichromate").formula == "K2Cr2O7"
    assert parse_ionic_name("potassium permanganate").formula == "KMnO4"


def test_invalid_input_returns_none():
    assert parse_ionic_name("not a real compound").formula is None
    assert parse_ionic_name("justoneword").formula is None


def test_manganese_oxide_shows_all_three_real_candidates():
    """Real bug found via live user testing: manganese's +4 state
    (MnO2, confirmed 'the most important manganese(IV) compound') was
    too conservatively excluded - manganese oxide's ambiguity must
    surface all three real candidates, not just two."""
    result = parse_ionic_name("manganese oxide")
    assert result.ambiguous is True
    assert set(result.all_candidates) == {"MnO", "Mn2O3", "MnO2"}


def test_manganese_iv_oxide_resolves():
    assert parse_ionic_name("manganese(IV) oxide").formula == "MnO2"


def test_mercury_chloride_genuine_ambiguity():
    """Real bug found via live user testing: mercury wasn't in the
    cation data at all. Mercury(I)'s real compound is the DIMERIC Hg2^2+
    ion (Hg2Cl2, 'calomel'), genuinely different from mercury(II)'s
    simple HgCl2 ('corrosive sublimate') - both real, distinctly named
    compounds, correctly surfaced as genuine ambiguity."""
    result = parse_ionic_name("mercury chloride")
    assert result.ambiguous is True
    assert set(result.all_candidates) == {"Hg2Cl2", "HgCl2"}


def test_mercury_roman_numerals_resolve_correctly():
    assert parse_ionic_name("mercury(I) chloride").formula == "Hg2Cl2"
    assert parse_ionic_name("mercury(II) chloride").formula == "HgCl2"


def test_monatomic_smiles_generated_and_valid():
    """Real, standard SMILES bracket-ion notation for purely monatomic
    ion pairs - independently validated via RDKit (not just internally
    self-consistent) before this test was written."""
    from rdkit import Chem
    from rdkit.Chem import rdMolDescriptors

    result = parse_ionic_name("sodium chloride")
    assert result.smiles == "[Na+].[Cl-]"
    mol = Chem.MolFromSmiles(result.smiles)
    assert mol is not None
    assert rdMolDescriptors.CalcMolFormula(mol) in ("NaCl", "ClNa")


def test_smiles_correctly_reflects_real_stoichiometry():
    """Confirms ion COUNT, not just presence, is reflected in the
    SMILES - calcium chloride needs two separate chloride ions."""
    result = parse_ionic_name("calcium chloride")
    assert result.smiles == "[Ca+2].[Cl-].[Cl-]"


def test_polyatomic_case_smiles_honestly_none():
    """Real, honest scope boundary: polyatomic ions (sulfate, carbonate)
    need their own, individually-verified SMILES strings, not yet done -
    smiles stays None rather than guessing."""
    result = parse_ionic_name("aluminum carbonate")
    assert result.formula == "Al2(CO3)3"
    assert result.smiles is None


def test_classical_ous_ic_naming():
    """Real, classical -ous/-ic naming convention, confirmed via
    multiple independent real sources: -ous = lower charge, -ic =
    higher charge. Only added where both the name AND the charge are
    directly confirmed for a cation already verified in this file."""
    assert parse_ionic_name("ferrous chloride").formula == "FeCl2"
    assert parse_ionic_name("ferric chloride").formula == "FeCl3"
    assert parse_ionic_name("cuprous oxide").formula == "Cu2O"
    assert parse_ionic_name("cupric oxide").formula == "CuO"
    assert parse_ionic_name("stannous fluoride").formula == "SnF2"
    assert parse_ionic_name("stannic fluoride").formula == "SnF4"
    assert parse_ionic_name("plumbous oxide").formula == "PbO"
    assert parse_ionic_name("plumbic oxide").formula == "PbO2"


def test_mercury_classical_names_reuse_the_real_dimeric_case():
    """Mercurous/mercuric correctly reuse mercury's existing, real,
    dimeric-ion special case - mercurous chloride is the real compound
    calomel (Hg2Cl2), not two independent Hg+ ions."""
    assert parse_ionic_name("mercurous chloride").formula == "Hg2Cl2"
    assert parse_ionic_name("mercuric chloride").formula == "HgCl2"


def test_cuprous_oxide_now_resolves_directly_via_ionic_not_opsin():
    """A genuine full-circle fix: 'cuprous oxide' previously produced a
    malformed formula via a real OPSIN misinterpretation (correctly
    rejected earlier), then fell back to 'unresolved' entirely. Now
    resolves confidently and correctly through ionic.py directly,
    closing the real gap for good."""
    result = parse_ionic_name("cuprous oxide")
    assert result.formula == "Cu2O"
    assert result.ambiguous is False


def test_new_polyatomic_anions():
    """chromate/sulfite/nitrite/oxalate/thiosulfate/peroxide, confirmed
    via direct search across multiple, independent, consistent real
    sources before being added."""
    assert parse_ionic_name("potassium chromate").formula == "K2CrO4"
    assert parse_ionic_name("sodium sulfite").formula == "Na2SO3"
    assert parse_ionic_name("sodium nitrite").formula == "NaNO2"
    assert parse_ionic_name("sodium oxalate").formula == "Na2C2O4"
    assert parse_ionic_name("sodium thiosulfate").formula == "Na2S2O3"
    assert parse_ionic_name("sodium peroxide").formula == "Na2O2"
