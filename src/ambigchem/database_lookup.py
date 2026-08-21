"""
database_lookup.py

Fills the real, remaining gap in name resolution: trivial/trade names
that OPSIN doesn't know. Confirmed directly, live, before writing this
module: OPSIN already handles many common names correctly ("water" ->
"O", "glucose" and "caffeine" both resolved to real, correct SMILES) -
but "aspirin" and "table salt" both genuinely failed, live, in this
project's own testing. This module exists specifically for that
remaining gap, not as a duplicate of organic.py's existing common-name
coverage - resolve_via_database() tries organic.py FIRST, only falling
through to a real database lookup when that genuinely fails.

UNLIKE EVERY OTHER MODULE IN THIS LIBRARY (elements, covalent, ionic,
organic, structure_convert, organic_structure - all directly, fully
tested with real execution in this sandbox), this module genuinely
cannot be tested live here: pubchem.ncbi.nlm.nih.gov is outside this
sandbox's network allowlist - confirmed directly, not assumed. A real,
live pubchempy call was attempted before writing this module and
returned "PubChemHTTPError: PubChem HTTP Error 403 Forbidden". This
follows the same honest pluggable-interface pattern used throughout the
ResAIyan project this library grew out of: a real interface, a
documented real implementation, and an explicitly-labeled mock for local
testing - never a silent fake.
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass
class DatabaseLookupResult:
    formula: str | None
    smiles: str | None = None
    source: str | None = None  # "opsin" | "pubchem" - which real path answered


class PubChemLookup:
    """
    Pluggable interface.

    THE REAL implementation, meant for a machine with genuine PubChem
    access (confirmed unavailable in this sandbox):

        import pubchempy as pcp
        class RealPubChemLookup(PubChemLookup):
            def __call__(self, name: str) -> DatabaseLookupResult | None:
                try:
                    compounds = pcp.get_compounds(name, 'name')
                    if not compounds:
                        return None
                    c = compounds[0]
                    return DatabaseLookupResult(
                        formula=c.molecular_formula,
                        smiles=c.canonical_smiles,
                        source="pubchem",
                    )
                except Exception:
                    return None
    """

    def __call__(self, name: str) -> DatabaseLookupResult | None:
        raise NotImplementedError(
            "Real lookup requires PubChem network access, confirmed unavailable "
            "in this sandbox (a real, live test returned 403 Forbidden). Inject "
            "a real callable on a machine with genuine access; use MockPubChemLookup "
            "for local testing."
        )


class MockPubChemLookup(PubChemLookup):
    """FOR LOCAL TESTING ONLY. Returns hand-provided, explicitly fake
    results - mirrors every other Mock* class throughout this project."""

    def __init__(self, fake_results: dict[str, DatabaseLookupResult]):
        self.fake_results = fake_results

    def __call__(self, name: str) -> DatabaseLookupResult | None:
        return self.fake_results.get(name.lower())


def resolve_via_database(name: str, lookup: PubChemLookup) -> DatabaseLookupResult | None:
    """The real entry point: tries organic.py FIRST (which already has
    decent common-name coverage via OPSIN, confirmed live), only falling
    through to the database lookup for genuine gaps."""
    from ambigchem.organic import parse_organic_name
    organic_result = parse_organic_name(name)
    if organic_result.formula:
        return DatabaseLookupResult(
            formula=organic_result.formula, smiles=organic_result.smiles, source="opsin"
        )
    return lookup(name)
