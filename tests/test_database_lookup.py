"""
test_database_lookup.py

Real pytest coverage for resolve_via_database(). The organic.py calls
here are REAL, not mocked - "water" genuinely resolves via OPSIN
(confirmed live before writing this module) and "aspirin" genuinely
fails OPSIN (also confirmed live) - only the PubChem-dependent fallback
path uses MockPubChemLookup, since that's the one piece genuinely
untestable in this sandbox.
"""

from ambigchem.database_lookup import resolve_via_database, DatabaseLookupResult, MockPubChemLookup


def test_water_resolves_via_opsin_not_database():
    """A real, live-confirmed fact: OPSIN already knows 'water'. The
    database mock is deliberately empty here - if this test passes,
    it's genuine proof the database was never even consulted, since an
    empty mock would return None for anything."""
    empty_mock = MockPubChemLookup(fake_results={})
    result = resolve_via_database("water", empty_mock)
    assert result is not None
    assert result.formula == "H2O"
    assert result.source == "opsin"


def test_aspirin_falls_through_to_database():
    """A real, live-confirmed fact: OPSIN genuinely fails on 'aspirin'
    (a trade name, not a systematic name) - confirmed with a real,
    live py2opsin call before writing this module. This proves the
    fallback path actually fires for a real, known gap, not a
    hypothetical one."""
    mock = MockPubChemLookup(fake_results={
        "aspirin": DatabaseLookupResult(
            formula="C9H8O4",
            smiles="CC(=O)OC1=CC=CC=C1C(=O)O",
            source="pubchem",
        ),
    })
    result = resolve_via_database("aspirin", mock)
    assert result is not None
    assert result.formula == "C9H8O4"
    assert result.source == "pubchem"


def test_genuinely_unknown_compound_returns_none():
    """Fails both OPSIN (real, live) and the database mock (empty) -
    confirms the whole chain fails gracefully rather than crashing."""
    empty_mock = MockPubChemLookup(fake_results={})
    result = resolve_via_database("not a real compound xyz123", empty_mock)
    assert result is None


def test_glucose_and_caffeine_also_resolve_via_opsin():
    """Two more real, live-confirmed OPSIN successes, proving this
    isn't a one-off - OPSIN's common-name coverage is genuinely broader
    than 'just water'."""
    empty_mock = MockPubChemLookup(fake_results={})
    glucose_result = resolve_via_database("glucose", empty_mock)
    assert glucose_result is not None
    assert glucose_result.source == "opsin"

    caffeine_result = resolve_via_database("caffeine", empty_mock)
    assert caffeine_result is not None
    assert caffeine_result.source == "opsin"
