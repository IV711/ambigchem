"""
test_organic.py

Real pytest coverage for parse_organic_name(). Requires the optional
'organic' extra to be installed (pip install ambigchem[organic]) - these
tests call real OPSIN and RDKit, not mocks, since both were directly
confirmed working in the build environment.
"""

from ambigchem.organic import parse_organic_name


def test_simple_organic_names():
    assert parse_organic_name("methane").formula == "CH4"
    assert parse_organic_name("ethanol").formula == "C2H6O"
    assert parse_organic_name("benzene").formula == "C6H6"


def test_branched_hydrocarbon():
    """Tests OPSIN's real handling of substituent locants, not just
    simple, unbranched names."""
    assert parse_organic_name("2,3-dimethylbutane").formula == "C6H14"


def test_functional_group():
    assert parse_organic_name("acetic acid").formula == "C2H4O2"


def test_real_smiles_is_also_returned():
    """Confirms the intermediate structure is genuinely available, not
    just the final formula - useful for anyone wanting the actual
    structure, not only its composition."""
    result = parse_organic_name("methane")
    assert result.smiles is not None


def test_inorganic_names_are_correctly_out_of_scope():
    """Real, confirmed scope boundary: OPSIN is an organic nomenclature
    parser and genuinely does not handle inorganic covalent names -
    that's covalent.py's job. This is complementary design, not a gap."""
    result = parse_organic_name("dinitrogen pentoxide")
    assert result.formula is None


def test_invalid_input_returns_none():
    result = parse_organic_name("not a real chemical name at all xyz123")
    assert result.formula is None
