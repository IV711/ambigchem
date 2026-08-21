"""
text_extraction.py

Phase 1 of full-sentence compound extraction: trie-based discovery of
known compound names from the real, offline local_database.py, plus a
default longest-match selection policy - kept architecturally separate
by direct design decision:

    DISCOVERY answers "what chemical spans exist in this text?"
    SELECTION answers "which of the overlapping candidates do I pick?"

This mirrors formula_segmenter.py's own segment_formula()/disambiguate()
split (from the ResAIyan project this library grew out of) - the same
principle, independently re-derived for a different problem, which is
itself a real signal it's the right shape.

Deliberately does NOT decide "which compound is the user's real intent"
- e.g. "compare the band gaps of sodium chloride and titanium dioxide"
proves distance-based heuristics alone would be wrong here (both
compounds are genuine targets despite different distances from the
property word), so that judgment correctly stays out of this library
entirely. Every DiscoveredMatch carries real position data so a caller
with real task/grammar/intent knowledge (like ResAIyan) can make that
call itself - keeping this module honestly reusable for completely
different applications (e.g. "extract every chemical mentioned in this
paper", which cares about none of that).

USES marisa-trie, NOT pygtrie - confirmed via direct, real benchmarking
before choosing, not assumed: at real database scale (1.4M entries),
marisa-trie builds in ~2s versus pygtrie's ~66s, and uses ~11MB versus
~1.4GB. Genuine save/load support means the trie only needs to be built
once, ever, then loaded near-instantly on every subsequent run - the
same "build once, offline forever" philosophy already proven for
local_database.py itself.
"""

from __future__ import annotations
import os
import re
import sqlite3
from dataclasses import dataclass
import marisa_trie

from ambigchem.elements import SYMBOL_TO_NAME


@dataclass
class DiscoveredMatch:
    text: str
    start: int
    end: int


# Phase 2: formula-shaped tokens (Fe2O3, NaCl, CuSO4). Pattern and
# validation logic ported from the original ResAIyan extraction
# pipeline's compound_resolver.py - the exact mechanism that correctly
# rejects property acronyms like "HOMO"/"LUMO"/"DOS" (syntactically
# formula-shaped, but "M" isn't a real element) while accepting real
# formulas like H2O/NaCl that use single-letter elements with no
# lowercase at all. Reuses elements.py's own SYMBOL_TO_NAME as the
# canonical element-symbol set, rather than a separately duplicated
# list - unlike the original version, which needed its own independent
# set since no shared elements module existed in that project.
FORMULA_PATTERN = re.compile(r"\b(?:[A-Z][a-z]?\d{0,3}){2,}\b")
_FORMULA_CHUNK_PATTERN = re.compile(r"[A-Z][a-z]?")


def _is_real_formula(candidate: str) -> bool:
    """Every parsed (capital + optional lowercase) chunk must be a real
    periodic table symbol."""
    chunks = _FORMULA_CHUNK_PATTERN.findall(re.sub(r"\d+", "", candidate))
    return len(chunks) >= 1 and all(c in SYMBOL_TO_NAME for c in chunks)


def discover_formula_matches(text: str) -> list[DiscoveredMatch]:
    """Phase 2: finds real, chemically-valid formula-shaped tokens
    directly in text, kept as its own independently-tested function per
    the layered build plan - not yet merged with Phase 1's trie
    discovery."""
    matches: list[DiscoveredMatch] = []
    for m in FORMULA_PATTERN.finditer(text):
        if _is_real_formula(m.group(0)):
            matches.append(DiscoveredMatch(m.group(0), m.start(), m.end()))
    return matches


def _normalize(text: str) -> str:
    """Case normalization, hyphens treated as word boundaries (same as
    spaces), punctuation stripped while word boundaries are preserved."""
    normalized = text.lower().replace("-", " ")
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def build_trie_from_database(db_path: str) -> marisa_trie.Trie:
    """Real, direct SQLite query - every distinct compound name
    currently in the local offline database becomes a trie entry."""
    conn = sqlite3.connect(db_path)
    names = [row[0] for row in conn.execute("SELECT DISTINCT name FROM compounds")]
    conn.close()
    return marisa_trie.Trie(names)


def load_or_build_trie(db_path: str, trie_cache_path: str | None = None) -> marisa_trie.Trie:
    """Build-once, persist-forever. Loads a cached trie if one already
    exists (near-instant, confirmed directly); otherwise builds fresh
    from the database (~2s at real 1.4M-entry scale, confirmed directly)
    and saves it for next time."""
    if trie_cache_path and os.path.exists(trie_cache_path):
        trie = marisa_trie.Trie()
        trie.load(trie_cache_path)
        return trie
    trie = build_trie_from_database(db_path)
    if trie_cache_path:
        trie.save(trie_cache_path)
    return trie


def discover_all_matches(text: str, trie: marisa_trie.Trie) -> list[DiscoveredMatch]:
    """DISCOVERY: every database entry that occurs anywhere in the text,
    at every starting position - including shorter matches even when a
    longer match also exists at the same position (e.g. both 'iron' and
    'iron oxide' from the same starting point). Never decides which to
    prefer - that is SELECTION's job, kept deliberately separate so a
    caller wanting the full candidate set (not just the default
    selection) always has access to it."""
    normalized = _normalize(text)
    all_matches: list[DiscoveredMatch] = []
    i = 0
    while i < len(normalized):
        if normalized[i] == " ":
            i += 1
            continue
        for candidate in trie.prefixes(normalized[i:]):
            all_matches.append(DiscoveredMatch(candidate, i, i + len(candidate)))
        i += 1
    return all_matches


def select_longest_non_overlapping(matches: list[DiscoveredMatch]) -> list[DiscoveredMatch]:
    """SELECTION: a separate, swappable default policy - longest match
    wins at each position, non-overlapping spans across the whole
    sentence (so 'sodium chloride' and 'sodium bicarbonate', sharing
    only their first word, are both correctly kept as independent
    matches, not confused with each other)."""
    matches_sorted = sorted(matches, key=lambda m: (m.start, -(m.end - m.start)))
    selected: list[DiscoveredMatch] = []
    last_end = -1
    for m in matches_sorted:
        if m.start >= last_end:
            selected.append(m)
            last_end = m.end
    return selected


def extract_compounds_from_text(text: str, trie: marisa_trie.Trie) -> list[DiscoveredMatch]:
    """Convenience wrapper: discovery + default selection in one call,
    for the common case. Callers wanting the full raw candidate set
    (e.g. ResAIyan, to reason about property-word proximity across ALL
    candidates, not just the ones this default policy picked) should
    call discover_all_matches() directly instead."""
    return select_longest_non_overlapping(discover_all_matches(text, trie))
