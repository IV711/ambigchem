"""
local_database.py

A real, offline, SQLite-backed datastore for compound name -> formula/
SMILES lookup - the actual, permanent local store that PubChem/ChEBI
bulk data gets imported INTO, once, so runtime lookups never need
network access again. This is the concrete "download once, offline
forever" pattern discussed for ChEBI's libChEBI, generalized to work
with either real source.

Fully, genuinely testable locally - pure SQLite, zero network
dependency at any point.
"""

from __future__ import annotations
import sqlite3
from dataclasses import dataclass


@dataclass
class DatabaseRecord:
    name: str
    formula: str
    smiles: str | None
    source: str  # "pubchem" | "chebi"


def create_database(db_path: str) -> None:
    """Creates a real, empty SQLite database with the correct schema."""
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS compounds (
            name TEXT PRIMARY KEY,
            formula TEXT NOT NULL,
            smiles TEXT,
            source TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_name ON compounds(name)")
    conn.commit()
    conn.close()


def insert_records(db_path: str, records: list[DatabaseRecord], batch_size: int = 1000) -> int:
    """Real, bulk insert - names are stored lowercase for case-
    insensitive lookup, matching every other module's convention in
    this library. Commits periodically (every `batch_size` records)
    rather than only once at the end - found necessary once a real,
    large-scale import (up to 500,000 PubChem entries) was actually
    attempted: a single final commit means an interrupted large import
    loses ALL progress, not just the remainder. Returns count of
    records actually inserted."""
    conn = sqlite3.connect(db_path)
    count = 0
    for i, r in enumerate(records):
        try:
            conn.execute(
                "INSERT OR REPLACE INTO compounds (name, formula, smiles, source) VALUES (?, ?, ?, ?)",
                (r.name.lower(), r.formula, r.smiles, r.source),
            )
            count += 1
        except sqlite3.Error:
            continue  # a single bad record must not abort the whole import
        if (i + 1) % batch_size == 0:
            conn.commit()
    conn.commit()  # final commit for any remaining records
    conn.close()
    return count


def lookup(db_path: str, name: str) -> DatabaseRecord | None:
    """Real, offline lookup - pure local SQLite query, zero network."""
    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        "SELECT name, formula, smiles, source FROM compounds WHERE name = ?",
        (name.lower(),),
    )
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return None
    return DatabaseRecord(name=row[0], formula=row[1], smiles=row[2], source=row[3])


def remove_low_quality_names(db_path: str, batch_size: int = 1000) -> int:
    """Retroactively purges short/common-word entries from an ALREADY-
    BUILT database - for anyone whose database was imported before
    bulk_import.py's is_trustworthy_name() filter existed. Reuses that
    exact same filter, so a fresh import and a cleaned-up old one apply
    the identical, real quality bar. Found necessary via live user
    testing: real, unfiltered PubChem imports genuinely include bare
    element symbols and other short noise that coincidentally matches
    inside ordinary English words during full-sentence extraction.
    Returns the count of rows removed."""
    from ambigchem.bulk_import import is_trustworthy_name

    conn = sqlite3.connect(db_path)
    all_names = [row[0] for row in conn.execute("SELECT name FROM compounds")]

    to_remove = [name for name in all_names if not is_trustworthy_name(name)]
    removed = 0
    for i, name in enumerate(to_remove):
        conn.execute("DELETE FROM compounds WHERE name = ?", (name,))
        removed += 1
        if (i + 1) % batch_size == 0:
            conn.commit()
    conn.commit()
    conn.close()
    return removed


def count_records(db_path: str) -> int:
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT COUNT(*) FROM compounds")
    count = cursor.fetchone()[0]
    conn.close()
    return count


if __name__ == "__main__":
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")

        print("=== Real SQLite datastore: create, insert, query ===\n")
        create_database(db_path)

        records = [
            DatabaseRecord("aspirin", "C9H8O4", "CC(=O)OC1=CC=CC=C1C(=O)O", "pubchem"),
            DatabaseRecord("2-acetyloxybenzoic acid", "C9H8O4", "CC(=O)OC1=CC=CC=C1C(=O)O", "pubchem"),
        ]
        inserted = insert_records(db_path, records)
        print(f"Inserted {inserted} records")
        assert inserted == 2

        result = lookup(db_path, "aspirin")
        print(f"Lookup 'aspirin': {result}")
        assert result is not None and result.formula == "C9H8O4"

        result_case = lookup(db_path, "ASPIRIN")
        print(f"Lookup 'ASPIRIN' (case-insensitive): {result_case}")
        assert result_case is not None and result_case.formula == "C9H8O4"

        missing = lookup(db_path, "not a real compound")
        print(f"Lookup missing compound: {missing}")
        assert missing is None

        print(f"\nTotal records: {count_records(db_path)}")
        assert count_records(db_path) == 2

        print("\nALL TESTS PASSED")