"""
test_elements.py

pytest, not a __main__ block. Two real, important differences worth
understanding:
  1. pytest AUTO-DISCOVERS this file just because it's named `test_*.py`
     inside a `tests/` folder - nobody has to remember to run it manually.
  2. Each `test_*` function is a fully independent test. A failure in one
     doesn't stop the others from running, and pytest reports every
     failure with a clear, real diff - not a manually-printed PASS/FAIL
     string we had to build ourselves.
"""

from ambigchem.elements import symbol_to_name, name_to_symbol, ELEMENT_DATA


def test_all_118_elements_present():
    assert len(ELEMENT_DATA) == 118


def test_symbol_to_name_basic():
    assert symbol_to_name("H") == "Hydrogen"
    assert symbol_to_name("Ti") == "Titanium"
    assert symbol_to_name("Og") == "Oganesson"


def test_name_to_symbol_basic():
    assert name_to_symbol("Hydrogen") == "H"
    assert name_to_symbol("titanium") == "Ti"  # case-insensitive


def test_name_to_symbol_handles_spelling_variants():
    assert name_to_symbol("aluminum") == "Al"
    assert name_to_symbol("aluminium") == "Al"
    assert name_to_symbol("sulfur") == "S"
    assert name_to_symbol("sulphur") == "S"
    assert name_to_symbol("caesium") == "Cs"
    assert name_to_symbol("cesium") == "Cs"


def test_unknown_symbol_returns_none():
    assert symbol_to_name("Xx") is None


def test_unknown_name_returns_none():
    assert name_to_symbol("unobtainium") is None
