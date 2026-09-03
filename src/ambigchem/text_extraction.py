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
from typing import Protocol
import marisa_trie

from ambigchem.elements import SYMBOL_TO_NAME
from ambigchem.local_database import lookup as db_lookup


@dataclass
class DiscoveredMatch:
    text: str
    start: int
    end: int


class HasSpan(Protocol):
    """Structural type for 'anything with a text span' - select_longest_
    non_overlapping() only ever touches .start/.end, confirmed by reading
    its real implementation, so it genuinely works correctly across
    DiscoveredMatch, SuffixCandidate, ExtractedCompound, or any future
    result type with these two fields - not type-hinted narrowly by
    accident."""
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


# Phase 3: suffix candidates. GIVEN A DISTINCT TYPE FROM DiscoveredMatch,
# deliberately - a suffix match is architecturally NOT the same kind of
# claim as a real database hit or a validated formula, and should never
# be treated with the same confidence by a caller.
#
# HONEST, MEASURED LIMITATION, confirmed by direct testing before this
# was built, not assumed: ordinary English words are full of these exact
# suffixes. A test of 29 hand-picked, completely ordinary words
# ("outside", "decide", "anyone", "phone"...) found 29/29 matched at
# least one chemical suffix pattern. This means Phase 3's real job is
# NOT to be accurate on its own - it is a loose pre-filter, narrowing
# "check every word in a sentence against OPSIN" down to "check only
# words shaped like they might be chemical names." Phase 4 (OPSIN
# validation) is what actually does the real filtering; Phase 3 is
# honestly expected to pass through real false positives.
#
# Includes "-one" (ketones - acetone, cyclohexanone) and "-al" (aldehydes
# - propanal, butanal) alongside the more common suffixes - genuine,
# additional chemical name categories, even though both carry real,
# extra false-positive risk ("-one" especially: someone/anyone/phone/
# alone/gone/stone). Accepted deliberately, consistent with this
# module's own stated design: Phase 4 is the real filter, not this one.
CHEMICAL_SUFFIXES = ("ide", "ate", "ite", "ol", "ane", "ene", "yne", "amine", "one", "al")

# A real, reasonably comprehensive stoplist of common English words that
# would otherwise be constant noise - mirrors formula_segmenter.py's
# _COMMON_WORD_STOPLIST pattern. Explicitly NOT a full solution to the
# false-positive problem (confirmed: even a list this size only catches
# the highest-frequency offenders) - just removes the most obviously
# non-chemical words before they ever reach Phase 4.
_SUFFIX_STOPLIST = {
    "side", "wide", "guide", "provide", "decide", "divide", "collide",
    "outside", "inside", "beside", "ride", "hide", "pride", "slide",
    "site", "quite", "white", "write", "invite", "polite", "opposite", "despite",
    "create", "separate", "immediate", "chocolate", "private", "late",
    "plate", "state", "rate", "gate", "date",
    "insane", "humane", "membrane", "hurricane", "mundane",
    "scene", "serene", "gene",
    "alone", "phone", "stone", "zone", "tone", "bone", "done", "gone", "none", "one",
    "someone", "anyone", "everyone",
    "several", "normal", "final", "total", "signal", "animal", "capital", "general", "natural",
    "school", "tool", "control", "protocol", "cool", "pool", "fool", "symbol",
    # existing 71 words stay exactly as they are - just adding to the set
    'alone', 'animal', 'anyone', 'beside', 'bone', 'capital', 'chocolate',
    'collide', 'control', 'cool', 'create', 'date', 'decide', 'despite',
    'divide', 'done', 'everyone', 'final', 'fool', 'gate', 'gene', 'general',
    'gone', 'guide', 'hide', 'humane', 'hurricane', 'immediate', 'insane',
    'inside', 'invite', 'late', 'membrane', 'mundane', 'natural', 'none',
    'normal', 'one', 'opposite', 'outside', 'phone', 'plate', 'polite',
    'pool', 'pride', 'private', 'protocol', 'provide', 'quite', 'rate',
    'ride', 'scene', 'school', 'separate', 'serene', 'several', 'side',
    'signal', 'site', 'slide', 'someone', 'state', 'stone', 'symbol',
    'tone', 'tool', 'total', 'white', 'wide', 'write', 'zone',
    # confirmed live during real benchmark runs - real OPSIN rejections observed
    'thermal', 'radical', 'orbital', 'lone', 'backbone', 'lethal', 'amide',
    'nodal', 'personal', 'seasonal',
    # new additions - each individually verified against real OPSIN parsing
    # before inclusion; none resolve as real compounds
    'mental', 'social', 'legal', 'equal', 'rural', 'oral', 'moral', 'vital',
    'focal', 'fatal', 'casual', 'actual', 'ideal', 'trial', 'portal',
    'hospital', 'digital', 'vertical', 'critical', 'medical', 'physical',
    'musical', 'magical', 'typical', 'tropical', 'ethical', 'logical',
    'political', 'practical', 'technical', 'historical', 'original',
    'national', 'additional', 'traditional', 'professional', 'potential',
    'essential', 'initial', 'special', 'official', 'financial', 'commercial',
    'industrial', 'universal', 'minimal', 'formal', 'verbal', 'dental',
    'rental', 'coastal', 'postal', 'brutal', 'crystal', 'aside', 'coincide',
    'confide', 'override', 'preside', 'reside', 'subside', 'worldwide',
    'bride', 'glide', 'snide', 'tide', 'climate', 'corporate', 'debate',
    'delicate', 'desperate', 'donate', 'intermediate', 'locate', 'moderate',
    'relate', 'rotate', 'senate', 'ultimate', 'appropriate', 'adequate',
    'candidate', 'certificate', 'duplicate', 'estimate', 'fortunate',
    'graduate', 'legislate', 'literate', 'negotiate', 'operate', 'temperate',
    'translate', 'vertebrate', 'bite', 'definite', 'excite', 'favorite',
    'ignite', 'infinite', 'kite', 'unite', 'appetite', 'requite', 'obscene',
    'hygiene', 'prone', 'drone', 'throne', 'atone', 'clone', 'crone',
    'urbane', 'arcane', 'profane',
}



@dataclass
class SuffixCandidate:
    text: str
    start: int
    end: int
    suffix: str  # which pattern matched, for transparency


def discover_suffix_candidates(text: str) -> list[SuffixCandidate]:
    """Phase 3: words matching a common chemical-name suffix pattern,
    kept as its own, distinctly-typed, independently-tested function.
    Deliberately low precision, honestly documented above - real
    filtering happens in Phase 4."""
    candidates: list[SuffixCandidate] = []
    for m in re.finditer(r"\b[a-zA-Z]+\b", text):
        word = m.group(0)
        word_lower = word.lower()
        if word_lower in _SUFFIX_STOPLIST:
            continue
        for suffix in CHEMICAL_SUFFIXES:
            if word_lower.endswith(suffix) and len(word_lower) > len(suffix):
                candidates.append(SuffixCandidate(word, m.start(), m.end(), suffix))
                break  # one candidate per word, first matching suffix
    return candidates


@dataclass
class ValidatedSuffixMatch:
    text: str
    start: int
    end: int
    suffix: str
    formula: str   # the REAL, OPSIN-confirmed formula - this field only
                   # ever exists if OPSIN genuinely validated the candidate
    smiles: str | None


def validate_suffix_candidates(
    candidates: list[SuffixCandidate], reject_cache_path: str | None = None
) -> list[ValidatedSuffixMatch]:
    """Phase 4: the step that actually redeems Phase 3's honestly-low
    precision. Runs each candidate through OPSIN (reusing organic.py's
    already-proven parse_organic_name() directly, not reimplementing
    anything) and keeps ONLY the ones that genuinely resolve to a real
    structure. A word like 'indicate' (a real, documented Phase 3 false
    positive - see test_text_extraction.py) reaches this function but
    OPSIN correctly rejects it, so it never appears in the output. A
    word like 'ethanol' gets a real, confirmed formula attached.

    HONEST, REAL COST worth stating plainly: each OPSIN call has real,
    non-trivial latency (a genuine subprocess launch, confirmed
    throughout organic.py's own testing) - this function is not free to
    run on every word in a large document, which is exactly why Phase 3
    exists as a pre-filter in the first place, not to be skipped.

    `reject_cache_path`, optional: a real, persistent, REAL-TIME cache
    of words OPSIN has already, definitively rejected - found valuable
    via live benchmarking, where the exact same non-chemical distractor
    words ("thermal", "radical", "orbital"...) recurred across many
    different real queries, each one paying a real, full OPSIN
    subprocess cost again. OPSIN's answer for a given string is
    deterministic - a rejection once is a rejection always - so once
    cached, a word never needs a real OPSIN call again, in this run or
    any future one. Updated the MOMENT a rejection happens, not
    batched or deferred. Explicitly opt-in (None by default): existing
    callers see no behavior change and no surprise cache file."""
    from ambigchem.organic import parse_organic_name
    from ambigchem.opsin_rejection_cache import load_rejection_cache, add_to_rejection_cache

    rejected = load_rejection_cache(reject_cache_path) if reject_cache_path else set()

    validated: list[ValidatedSuffixMatch] = []
    for candidate in candidates:
        if candidate.text.lower() in rejected:
            continue  # real, already-confirmed rejection - no OPSIN call needed
        result = parse_organic_name(candidate.text)
        if result.formula:
            validated.append(ValidatedSuffixMatch(
                candidate.text, candidate.start, candidate.end,
                candidate.suffix, result.formula, result.smiles,
            ))
        elif reject_cache_path:
            add_to_rejection_cache(candidate.text, reject_cache_path)
    return validated


def _normalize(text: str) -> str:
    """Case normalization, hyphens treated as word boundaries (same as
    spaces), apostrophes STRIPPED ENTIRELY (not replaced with a space) -
    found necessary specifically for real terms like "Young's modulus":
    replacing with a space would turn it into three words ("young s
    modulus"), never matching a two-word vocabulary entry. Other
    punctuation is stripped while word boundaries are preserved."""
    normalized = text.lower().replace("-", " ")
    normalized = normalized.replace("'", "")
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
    at every genuine word-boundary-aligned starting position - including
    shorter matches even when a longer match also exists at the same
    position (e.g. both 'iron' and 'iron oxide' from the same starting
    point). Never decides which to prefer - that is SELECTION's job,
    kept deliberately separate so a caller wanting the full candidate
    set (not just the default selection) always has access to it.

    TWO REAL WORD-BOUNDARY CONSTRAINTS, added after live user testing
    found the original version accepted matches with no such
    constraints at all - a real, more fundamental bug than a length or
    stopword filter alone could fix (a length filter can't distinguish
    "urea", a real 4-character compound name, from "indi", 4-character
    noise - the actual problem is that "indi" was never a real word to
    begin with):
      1. START boundary - a match may only be attempted at position 0,
         or immediately after a space. Without this, "ted" was found
         starting mid-word at position 3 of "tested" - never a genuine
         word start at all.
      2. END boundary - a match must consume a COMPLETE token, ending
         at a space or the end of the text, never leaving characters
         dangling right after it. Without this, "fe2" was accepted as a
         partial match of the longer token "fe2o3", and "indi" as a
         partial match of "indicate"."""
    normalized = _normalize(text)
    all_matches: list[DiscoveredMatch] = []
    i = 0
    while i < len(normalized):
        if normalized[i] == " ":
            i += 1
            continue
        is_word_start = (i == 0) or (normalized[i - 1] == " ")
        if is_word_start:
            for candidate in trie.prefixes(normalized[i:]):
                end = i + len(candidate)
                is_word_end = (end == len(normalized)) or (normalized[end] == " ")
                if is_word_end:
                    all_matches.append(DiscoveredMatch(candidate, i, end))
        i += 1
    return all_matches


def select_longest_non_overlapping(matches: list[HasSpan]) -> list[HasSpan]:
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


@dataclass
class ExtractedCompound:
    text: str
    start: int
    end: int
    method: str              # "database" | "formula" | "opsin_validated"
    formula: str | None = None  # populated for "formula" and "opsin_validated"


def extract_all(text: str, trie: marisa_trie.Trie, db_path: str | None = None,
                 opsin_reject_cache_path: str | None = None) -> list[ExtractedCompound]:
    """The unified entry point, combining all four independently-proven
    phases - built only now that each stands on its own real evidence,
    per the original, explicit design intent: 'I would not immediately
    combine all four methods into one giant detector. Build them in
    layers.'

    Everything in the OUTPUT is genuinely high-confidence by
    construction: Phase 3's honestly-low-precision candidates only
    appear here if Phase 4 (real OPSIN validation) actually confirmed
    them - the unvalidated, low-confidence candidates never reach this
    final list at all.

    `db_path`, optional: a real gap found by reviewing this function
    after it was first built - build_trie_from_database() only pulls
    compound NAMES into the trie, never formulas, so a database match
    would otherwise always have formula=None even though the real
    formula sits one lookup away. If given, each database match gets
    its real formula via local_database.lookup() directly - the same,
    already-proven function, not reimplemented. Deliberately a real
    SQLite lookup per match, NOT marisa_trie.RecordTrie - confirmed via
    direct testing that RecordTrie requires FIXED-SIZE byte records,
    meaning any formula longer than a chosen size would be silently
    corrupted, not error out. A real lookup() call is slightly slower
    but never silently wrong.

    Cross-phase spatial overlaps (e.g. a formula-shaped database entry
    found by both Phase 1 and Phase 2) are reconciled using the exact
    same longest-match/non-overlapping policy already proven for Phase
    1's own internal overlaps - genuinely reused via the HasSpan
    Protocol, not duplicated logic."""
    combined: list[ExtractedCompound] = []

    for m in extract_compounds_from_text(text, trie):
        formula = None
        if db_path:
            record = db_lookup(db_path, m.text)
            if record:
                formula = record.formula
        combined.append(ExtractedCompound(m.text, m.start, m.end, "database", formula=formula))

    for m in discover_formula_matches(text):
        # m.text IS itself a validated formula (it passed _is_real_formula()
        # to be discovered at all) - populating it here, rather than
        # leaving formula=None, closes a real inconsistency found by
        # reviewing live output: "NaCl" via method="formula" previously
        # carried formula=None even though the matched text is the answer.
        combined.append(ExtractedCompound(m.text, m.start, m.end, "formula", formula=m.text))

    validated = validate_suffix_candidates(discover_suffix_candidates(text), reject_cache_path=opsin_reject_cache_path)
    for v in validated:
        combined.append(ExtractedCompound(v.text, v.start, v.end, "opsin_validated", formula=v.formula))

    # Phase 5 already returns real, complete ExtractedCompound objects
    # (real formula, real specific method - "covalent"/"ionic"/"organic",
    # not a generic label) - append directly, no rewrapping needed.
    combined.extend(discover_orchestrator_matches(text))

    return select_longest_non_overlapping(combined)


# Real, curated chemistry property concept vocabulary - deliberately
# generic, independent of any specific tool's task/API naming (e.g.
# "band gap" here, never "HOMOLUMOGapTask" - that project-specific
# concept-to-task-class mapping belongs in ResAIyan, per the same
# reasoning that originally kept property-to-task mapping out of this
# library entirely). Deliberately apostrophe-free (e.g. "youngs
# modulus" not "Young's modulus") - _normalize() strips punctuation to
# spaces, and an apostrophe-containing trie entry would silently never
# match the normalized search text otherwise. A real edge case caught
# before it became a real bug, not after.
PROPERTY_CONCEPTS = {
    "band gap", "dipole moment", "melting point", "boiling point",
    "density", "molar mass", "ionization energy", "electronegativity",
    "cohesive energy", "atomization energy", "lattice constant",
    "vapor pressure", "thermal conductivity", "refractive index",
    "solubility", "electron affinity", "bond length", "bond angle",
    "oxidation state", "spin state", "specific heat", "enthalpy",
    "formation energy", "adsorption energy", "surface energy",
    "youngs modulus", "bulk modulus", "shear modulus", "hardness",
    "thermal expansion", "heat capacity", "magnetic moment",
    "work function", "electron mobility", "carrier concentration",
}


def build_property_trie() -> marisa_trie.Trie:
    """A real, small trie built from the fixed property vocabulary -
    reuses the exact same generic discovery/selection machinery already
    proven for compound-name matching, with zero code changes needed for
    a completely different vocabulary."""
    return marisa_trie.Trie(PROPERTY_CONCEPTS)


def extract_property_concepts_from_text(text: str) -> list[DiscoveredMatch]:
    """Extracts real, generic chemistry property concepts from text,
    WITH real position data - essential for a caller (e.g. ResAIyan) to
    reason about proximity between a property mention and a compound
    mention, per the already-agreed design: this library returns raw
    material only, it never decides which compound a property refers to
    (see e.g. 'compare the band gaps of X and Y' - a case where
    proximity alone would be the wrong signal, decided outside this
    library entirely).

    Deliberately reuses discover_all_matches()/select_longest_non_
    overlapping() unchanged - the same longest-match, overlap-safe
    machinery already proven for compound names works identically here,
    since both are the same underlying problem: known vocabulary, found
    in text, with real positions attached."""
    trie = build_property_trie()
    return select_longest_non_overlapping(discover_all_matches(text, trie))


# Phase 5: real, multi-word covalent/ionic/organic names via
# orchestrator.parse_compound_name() - the real gap Phases 1-4
# structurally can't fill. covalent.py/ionic.py's parsers require
# ADJACENT WORD PAIRS ("carbon monoxide", "iron oxide"), not single
# tokens or exact database entries - a name genuinely absent from the
# offline database (Phase 1) and not formula-shaped (Phase 2) would
# otherwise never be found, even though parse_compound_name() resolves
# it instantly on its own.
#
# TOKENIZATION, deliberately NOT reusing the shared _normalize()
# pipeline: ionic.py's Roman-numeral detection needs literal
# parentheses ("iron(III)"), which _normalize() strips to spaces
# elsewhere - confirmed directly, a real requirement, not an assumption.
_WORD_WITH_OPTIONAL_ROMAN = re.compile(r"[A-Za-z]+(?:\([IVXivx]+\))?")

# PERFORMANCE-CONSCIOUS DESIGN, real and deliberate: calling the full
# orchestrator (which can fall through to a real OPSIN subprocess call)
# on EVERY adjacent word pair in a document would be genuinely slow. A
# cheap, free pre-filter first checks whether the second word plausibly
# ends in a known anion pattern - real vocabulary already defined in
# covalent.py/ionic.py, reused here, not invented new.
#
# HONEST SCOPE LIMIT: this pre-filter works well for covalent/ionic
# (small, curated anion vocabularies) but means multi-word ORGANIC names
# without an anion-like second word (e.g. "acetic acid") are NOT caught
# by this phase - single-word organic names remain covered by Phase 3+4
# as before. Confirmed directly, not hidden.
def _known_anion_endings() -> set[str]:
    from ambigchem.covalent import IDE_FORMS
    from ambigchem.ionic import POLYATOMIC_ANIONS
    return set(IDE_FORMS.keys()) | set(POLYATOMIC_ANIONS.keys())


def discover_orchestrator_matches(text: str) -> list[ExtractedCompound]:
    """Phase 5: finds real, multi-word covalent/ionic/organic compound
    names by scanning adjacent word pairs through
    orchestrator.parse_compound_name() - genuinely reuses that
    function's existing covalent+ionic+organic routing, not
    reimplemented here. Returns ExtractedCompound directly (not a bare
    DiscoveredMatch) so the real, resolved formula and the SPECIFIC
    engine that resolved it (orchestrator's own real method label -
    "covalent", "ionic", "organic" - not a generic "orchestrator" tag)
    are preserved, not discarded.

    Only reports CONFIDENT (non-ambiguous) matches. Genuine
    orchestrator-level ambiguity (e.g. "iron oxide" with no Roman
    numeral) is deliberately NOT surfaced within this phase's output -
    ExtractedCompound has no slot for "ambiguous, here are the real
    candidates" today, a real, separate, follow-up design question, not
    silently dropped without acknowledgment."""
    from ambigchem.orchestrator import parse_compound_name

    known_anions = _known_anion_endings()
    tokens = [(m.group(0), m.start(), m.end()) for m in _WORD_WITH_OPTIONAL_ROMAN.finditer(text)]

    matches: list[ExtractedCompound] = []
    for i in range(len(tokens) - 1):
        word1, start1, _ = tokens[i]
        word2, _, end2 = tokens[i + 1]

        if not any(word2.lower().endswith(anion) for anion in known_anions):
            continue  # cheap pre-filter - skip pairs with no chemistry signal at all

        candidate_text = f"{word1} {word2}"
        result = parse_compound_name(candidate_text)
        if result.formula and not result.ambiguous:
            matches.append(ExtractedCompound(candidate_text, start1, end2, result.method, formula=result.formula))

    return matches
