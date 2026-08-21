"""
test_text_extraction.py

Real pytest coverage for the discovery/selection split, including a
genuine local_database.py-backed test (not just a hand-built trie) to
prove build_trie_from_database() works end to end, plus real trie
persistence and every correctness requirement from the design
discussion: longest match, shared prefixes across different compounds,
overlapping candidates at one position, case normalization, punctuation,
hyphens, and multi-word names.
"""

import os
import tempfile
import marisa_trie
import pytest
from ambigchem.local_database import create_database, insert_records, DatabaseRecord
from ambigchem.text_extraction import (
    discover_all_matches,
    select_longest_non_overlapping,
    extract_compounds_from_text,
    build_trie_from_database,
    load_or_build_trie,
    discover_formula_matches,
    discover_suffix_candidates,
    validate_suffix_candidates,
    DiscoveredMatch,
    SuffixCandidate,
    ValidatedSuffixMatch,
)


@pytest.fixture
def sample_trie():
    """A small, controlled, real vocabulary - hand-built for precise
    testing, mirroring the shape of real database entries."""
    names = ["iron", "iron oxide", "sodium", "sodium chloride", "sodium bicarbonate", "water", "titanium dioxide"]
    return marisa_trie.Trie(names)


def test_longest_match_wins_by_default(sample_trie):
    matches = extract_compounds_from_text("Titanium dioxide is a real compound.", sample_trie)
    assert [m.text for m in matches] == ["titanium dioxide"]


def test_shared_prefix_across_different_compounds_both_found(sample_trie):
    """Requirement (a): 'sodium chloride' and 'sodium bicarbonate' share
    only their first word but must both be found as independent matches,
    not confused with each other."""
    text = "The sample contains sodium chloride and sodium bicarbonate."
    matches = extract_compounds_from_text(text, sample_trie)
    assert [m.text for m in matches] == ["sodium chloride", "sodium bicarbonate"]


def test_discovery_keeps_shorter_candidates_selection_picks_longest(sample_trie):
    """Requirement (b): at the SAME starting position, both 'iron' and
    'iron oxide' are valid database entries. Discovery must keep BOTH
    (architecturally reusable for a caller who wants the shorter match
    too), while the default selection policy picks the longer one."""
    text = "iron oxide was synthesized."
    discovered = discover_all_matches(text, sample_trie)

    discovered_texts = [m.text for m in discovered]
    assert "iron" in discovered_texts, "Discovery must not silently drop the shorter candidate"
    assert "iron oxide" in discovered_texts

    selected = select_longest_non_overlapping(discovered)
    assert [m.text for m in selected] == ["iron oxide"], "Selection must pick the longer match by default"


def test_combined_real_world_sentence(sample_trie):
    """The full example from the design discussion - proves both
    requirements work together correctly in one real sentence, and that
    sodium chloride is never confused with sodium bicarbonate."""
    text = "The sample contained sodium chloride and iron oxide."
    matches = extract_compounds_from_text(text, sample_trie)
    assert [m.text for m in matches] == ["sodium chloride", "iron oxide"]


def test_case_normalization(sample_trie):
    matches = extract_compounds_from_text("WATER, Titanium Dioxide, and SODIUM are all here.", sample_trie)
    assert [m.text for m in matches] == ["water", "titanium dioxide", "sodium"]


def test_hyphen_treated_as_word_boundary(sample_trie):
    matches = extract_compounds_from_text("sodium-chloride is table salt", sample_trie)
    assert [m.text for m in matches] == ["sodium chloride"]


def test_punctuation_does_not_break_matching(sample_trie):
    matches = extract_compounds_from_text("Is this water? Yes, it's water.", sample_trie)
    assert [m.text for m in matches] == ["water", "water"]


def test_positions_are_real_and_correct(sample_trie):
    """Position data must genuinely correspond to the real text - this
    is the exact information ResAIyan's own intent logic would depend on."""
    text = "The compound is water."
    matches = extract_compounds_from_text(text, sample_trie)
    assert len(matches) == 1
    m = matches[0]
    normalized_text = "the compound is water"
    assert normalized_text[m.start:m.end] == "water"


def test_no_match_returns_empty_list(sample_trie):
    matches = extract_compounds_from_text("This sentence has no chemicals in it.", sample_trie)
    assert matches == []


class TestPhase2FormulaExtraction:
    """Phase 2, kept deliberately separate per the layered build plan -
    formula-shaped tokens (Fe2O3, NaCl, CuSO4), not database names."""

    def test_finds_real_formula_in_sentence(self):
        matches = discover_formula_matches("The formula for iron oxide is Fe2O3.")
        assert [m.text for m in matches] == ["Fe2O3"]

    def test_finds_multiple_formulas_in_one_sentence(self):
        matches = discover_formula_matches("We used CuSO4 and NaCl in the experiment.")
        assert [m.text for m in matches] == ["CuSO4", "NaCl"]

    def test_positions_are_real_and_correct(self):
        text = "The compound NaCl is common salt."
        matches = discover_formula_matches(text)
        assert len(matches) == 1
        m = matches[0]
        assert text[m.start:m.end] == "NaCl"

    def test_adversarial_property_acronyms_still_correctly_rejected(self):
        """The exact real bug this validation logic was originally built
        to fix, now proven in full-sentence context, not just an
        isolated token: HOMO/LUMO/DOS are syntactically formula-shaped
        (every capital letter satisfies the pattern) but must be
        rejected, since 'M' and 'D' aren't real element symbols."""
        matches = discover_formula_matches(
            "The HOMO-LUMO gap was calculated using DOS methods."
        )
        assert matches == [], "Property acronyms must never be mistaken for real formulas"

    def test_real_formulas_with_single_letter_elements_still_work(self):
        """Confirms the fix doesn't overcorrect - real formulas using
        only single-letter elements (no lowercase at all) must still be
        accepted, the exact case a naive 'require lowercase' fix would
        have broken."""
        matches = discover_formula_matches("The molecule H2O is essential for life.")
        assert [m.text for m in matches] == ["H2O"]

    def test_no_formula_in_plain_text_returns_empty(self):
        matches = discover_formula_matches("This sentence has no chemical formulas.")
        assert matches == []


class TestPhase3SuffixCandidates:
    """Phase 3, kept deliberately separate and distinctly typed from
    DiscoveredMatch - a suffix match is honestly a much weaker claim
    than a real database hit or validated formula (see module docstring
    for the measured 29/29 false-positive rate that shaped this design)."""

    def test_real_chemical_names_are_detected_as_candidates(self):
        text = "We dissolved sodium chloride in ethanol and measured the sulfate content."
        candidates = discover_suffix_candidates(text)
        texts = [c.text.lower() for c in candidates]
        assert "chloride" in texts
        assert "ethanol" in texts
        assert "sulfate" in texts

    def test_stoplist_filters_the_most_common_false_positives(self):
        """The small, explicit mitigation - not a real solution, just
        removes the highest-frequency non-chemical words."""
        candidates = discover_suffix_candidates("Anyone outside can decide to phone someone.")
        assert candidates == [], "Every word here is in the stoplist and must be filtered"

    def test_honest_proof_real_false_positives_still_get_through(self):
        """THE actual, documented limitation, proven with a real test,
        not just asserted in a comment: a common English word NOT in the
        small stoplist will still incorrectly appear as a candidate.
        This is expected, honestly-accepted behavior - Phase 4 (OPSIN)
        is what does the real filtering, not this function."""
        candidates = discover_suffix_candidates("Please indicate your favorite candidate.")
        texts = [c.text.lower() for c in candidates]
        assert "indicate" in texts or "candidate" in texts, (
            "This test documents a REAL, accepted limitation - if it ever "
            "starts failing, it means false positives got filtered, which "
            "would be a genuine improvement, but the module docstring's "
            "claims should be updated to match, not left stale"
        )

    def test_positions_and_matched_suffix_are_real_and_correct(self):
        text = "The compound ethanol was tested."
        candidates = discover_suffix_candidates(text)
        assert len(candidates) == 1
        c = candidates[0]
        assert text[c.start:c.end] == "ethanol"
        assert c.suffix == "ol"

    def test_no_chemical_suffixed_words_returns_empty(self):
        candidates = discover_suffix_candidates("The cat sat on the mat.")
        assert candidates == []


class TestPhase4OpsinValidation:
    """Phase 4: the step that actually redeems Phase 3's honestly-low
    precision. Uses REAL OPSIN calls, not mocks - confirmed working
    throughout organic.py's own test suite already."""

    def test_real_chemical_is_validated_with_a_real_formula(self):
        candidates = discover_suffix_candidates("The reaction used ethanol as solvent.")
        validated = validate_suffix_candidates(candidates)
        assert len(validated) == 1
        assert validated[0].text == "ethanol"
        assert validated[0].formula == "C2H6O"

    def test_false_positive_is_correctly_rejected_not_validated(self):
        """The direct proof Phase 4 does real work, not just pass-
        through: 'indicate' is a real, documented Phase 3 false positive
        (see TestPhase3SuffixCandidates) - it reaches this function but
        OPSIN correctly refuses to validate it."""
        candidates = discover_suffix_candidates("Please indicate your answer.")
        assert len(candidates) == 1  # Phase 3 honestly lets it through
        validated = validate_suffix_candidates(candidates)
        assert validated == [], "OPSIN must correctly reject a non-chemical word"

    def test_the_decisive_combined_case(self):
        """THE real, decisive proof of the whole 4-phase design: one
        sentence containing both a genuine chemical (ethanol) and a
        documented false positive (indicate) - Phase 3 finds both,
        Phase 4 correctly keeps only the real one."""
        text = "Please indicate that ethanol was used in this reaction."
        candidates = discover_suffix_candidates(text)
        candidate_texts = {c.text.lower() for c in candidates}
        assert "indicate" in candidate_texts
        assert "ethanol" in candidate_texts

        validated = validate_suffix_candidates(candidates)
        validated_texts = [v.text for v in validated]
        assert validated_texts == ["ethanol"], (
            "Phase 4 must keep the real chemical and discard the false "
            "positive - this is the entire point of the 4-phase design"
        )
        assert validated[0].formula == "C2H6O"

    def test_no_candidates_returns_empty_validated_list(self):
        assert validate_suffix_candidates([]) == []


class TestRealDatabaseBackedTrie:
    """Proves build_trie_from_database() genuinely works against a real
    local_database.py instance, not just a hand-built trie - the actual
    real-world path this module is meant to run."""

    @pytest.fixture
    def real_db(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "compounds.db")
            create_database(db_path)
            insert_records(db_path, [
                DatabaseRecord("aspirin", "C9H8O4", "CC(=O)OC1=CC=CC=C1C(=O)O", "pubchem"),
                DatabaseRecord("water", "H2O", "O", "pubchem"),
                DatabaseRecord("titanium dioxide", "TiO2", None, "pubchem"),
            ])
            yield db_path

    def test_trie_builds_correctly_from_real_database(self, real_db):
        trie = build_trie_from_database(real_db)
        matches = extract_compounds_from_text("We tested aspirin and titanium dioxide today.", trie)
        assert [m.text for m in matches] == ["aspirin", "titanium dioxide"]

    def test_trie_persistence_build_once_load_forever(self, real_db):
        """The real 'build once, offline forever' path - a save/load
        round trip must produce a trie that matches identically."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = os.path.join(tmpdir, "trie_cache.marisa")

            assert not os.path.exists(cache_path)
            trie1 = load_or_build_trie(real_db, trie_cache_path=cache_path)
            assert os.path.exists(cache_path), "Building should have saved a cache file"

            # Second call should LOAD the cache, not rebuild - same result either way
            trie2 = load_or_build_trie(real_db, trie_cache_path=cache_path)

            matches1 = extract_compounds_from_text("aspirin and water", trie1)
            matches2 = extract_compounds_from_text("aspirin and water", trie2)
            assert [m.text for m in matches1] == [m.text for m in matches2] == ["aspirin", "water"]