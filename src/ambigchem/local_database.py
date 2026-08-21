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


def insert_records(db_path: str, records: list[DatabaseRecord]) -> int:
    """Real, bulk insert - names are stored lowercase for case-
    insensitive lookup, matching every other module's convention in
    this library. Returns count of records actually inserted."""
    conn = sqlite3.connect(db_path)
    count = 0
    for r in records:
        try:
            conn.execute(
                "INSERT OR REPLACE INTO compounds (name, formula, smiles, source) VALUES (?, ?, ?, ?)",
                (r.name.lower(), r.formula, r.smiles, r.source),
            )
            count += 1
        except sqlite3.Error:
            continue  # a single bad record must not abort the whole import
    conn.commit()
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
