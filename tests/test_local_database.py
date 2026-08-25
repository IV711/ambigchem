"""
test_local_database.py

Real pytest coverage for the SQLite-backed offline datastore - fully
testable locally, zero network dependency at any point.
"""

import os
import tempfile
import pytest
from ambigchem.local_database import create_database, insert_records, lookup, count_records, remove_low_quality_names, DatabaseRecord


@pytest.fixture
def db_path():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "test.db")
        create_database(path)
        yield path


def test_insert_and_lookup(db_path):
    records = [DatabaseRecord("aspirin", "C9H8O4", "CC(=O)OC1=CC=CC=C1C(=O)O", "pubchem")]
    assert insert_records(db_path, records) == 1

    result = lookup(db_path, "aspirin")
    assert result is not None
    assert result.formula == "C9H8O4"
    assert result.source == "pubchem"


def test_lookup_is_case_insensitive(db_path):
    insert_records(db_path, [DatabaseRecord("Aspirin", "C9H8O4", None, "pubchem")])
    assert lookup(db_path, "ASPIRIN") is not None
    assert lookup(db_path, "aspirin") is not None
    assert lookup(db_path, "AsPiRiN") is not None


def test_missing_compound_returns_none(db_path):
    assert lookup(db_path, "not a real compound") is None


def test_multiple_names_same_formula(db_path):
    """A real, common case - the same compound has multiple valid names
    (trivial name + IUPAC name), both should be independently lookupable."""
    records = [
        DatabaseRecord("aspirin", "C9H8O4", "CC(=O)OC1=CC=CC=C1C(=O)O", "pubchem"),
        DatabaseRecord("2-acetyloxybenzoic acid", "C9H8O4", "CC(=O)OC1=CC=CC=C1C(=O)O", "pubchem"),
    ]
    assert insert_records(db_path, records) == 2
    assert lookup(db_path, "aspirin").formula == "C9H8O4"
    assert lookup(db_path, "2-acetyloxybenzoic acid").formula == "C9H8O4"


def test_count_records(db_path):
    assert count_records(db_path) == 0
    insert_records(db_path, [
        DatabaseRecord("water", "H2O", "O", "pubchem"),
        DatabaseRecord("methane", "CH4", "C", "pubchem"),
    ])
    assert count_records(db_path) == 2


def test_insert_or_replace_does_not_duplicate(db_path):
    """Re-inserting the same name (e.g. re-running an import) should
    update, not create a duplicate row."""
    insert_records(db_path, [DatabaseRecord("water", "H2O", "O", "pubchem")])
    insert_records(db_path, [DatabaseRecord("water", "H2O", "[OH2]", "pubchem")])  # different SMILES, same name
    assert count_records(db_path) == 1
    assert lookup(db_path, "water").smiles == "[OH2]"


class TestRemoveLowQualityNames:
    """Real bug found via live user testing: a real, unfiltered PubChem
    import genuinely includes bare element symbols and other short noise
    (e.g. 'W' for tungsten) that coincidentally matches inside ordinary
    English words during full-sentence extraction ('w' found inside
    'We', 'es' found inside 'tested'). This retroactively cleans an
    already-built database - for anyone whose data predates
    bulk_import.py's is_trustworthy_name() filter."""

    def test_short_and_common_names_removed_real_compounds_kept(self, db_path):
        insert_records(db_path, [
            DatabaseRecord("W", "W", None, "pubchem"),
            DatabaseRecord("Es", "Es", None, "pubchem"),
            DatabaseRecord("the", "C1", None, "pubchem"),
            DatabaseRecord("aspirin", "C9H8O4", None, "pubchem"),
            DatabaseRecord("titanium dioxide", "TiO2", None, "pubchem"),
        ])
        removed = remove_low_quality_names(db_path)
        assert removed == 3
        assert lookup(db_path, "W") is None
        assert lookup(db_path, "Es") is None
        assert lookup(db_path, "the") is None
        assert lookup(db_path, "aspirin") is not None
        assert lookup(db_path, "aspirin").formula == "C9H8O4"
        assert lookup(db_path, "titanium dioxide") is not None

    def test_clean_database_removes_nothing(self, db_path):
        insert_records(db_path, [DatabaseRecord("aspirin", "C9H8O4", None, "pubchem")])
        assert remove_low_quality_names(db_path) == 0
        assert count_records(db_path) == 1
