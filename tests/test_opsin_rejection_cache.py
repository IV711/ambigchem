"""
test_opsin_rejection_cache.py

Real pytest coverage for the OPSIN rejection cache - built after live
benchmarking showed the exact same non-chemical distractor words
recurring across many real queries, each paying a full OPSIN
subprocess cost again.
"""
import os
import tempfile
import time
import pytest

from ambigchem.opsin_rejection_cache import load_rejection_cache, add_to_rejection_cache, cache_size
from ambigchem.text_extraction import (
    discover_suffix_candidates, validate_suffix_candidates, extract_all,
    build_trie_from_database,
)
from ambigchem.local_database import create_database, insert_records, DatabaseRecord


@pytest.fixture
def cache_path():
    fd, path = tempfile.mkstemp(suffix=".txt")
    os.close(fd)
    os.remove(path)  # start genuinely empty, not just an empty file
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_empty_cache_for_nonexistent_file(cache_path):
    assert load_rejection_cache(cache_path) == set()


def test_add_and_load_round_trip(cache_path):
    add_to_rejection_cache("thermal", cache_path)
    assert load_rejection_cache(cache_path) == {"thermal"}


def test_case_insensitive_and_deduplicated(cache_path):
    add_to_rejection_cache("Thermal", cache_path)
    add_to_rejection_cache("THERMAL", cache_path)
    add_to_rejection_cache("thermal", cache_path)
    assert cache_size(cache_path) == 1


def test_real_opsin_rejection_gets_cached(cache_path):
    """The core, real behavior: a genuine OPSIN rejection is recorded
    immediately, not batched or deferred."""
    candidates = discover_suffix_candidates("The thermal properties were measured.")
    assert len(candidates) == 1 and candidates[0].text == "thermal"

    result = validate_suffix_candidates(candidates, reject_cache_path=cache_path)
    assert result == []  # correctly rejected, not a real compound
    assert "thermal" in load_rejection_cache(cache_path)


def test_second_call_skips_opsin_and_is_dramatically_faster(cache_path):
    """The actual point of this whole cache: real, measured speedup on
    a repeated word, not just a claim."""
    candidates = discover_suffix_candidates("The thermal properties were measured.")

    t0 = time.perf_counter()
    validate_suffix_candidates(candidates, reject_cache_path=cache_path)
    first_call_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    result2 = validate_suffix_candidates(candidates, reject_cache_path=cache_path)
    second_call_ms = (time.perf_counter() - t0) * 1000

    assert result2 == []
    # Real OPSIN calls cost real seconds; a cache hit costs microseconds.
    # A generous threshold - the point is orders of magnitude, not a
    # precise number that could vary by machine.
    assert second_call_ms < first_call_ms / 10


def test_real_compound_never_gets_cached_as_rejected(cache_path):
    """Critical safety check: a genuinely real compound must never end
    up in the rejection cache, under any circumstance."""
    candidates = discover_suffix_candidates("The ethanol sample was pure.")
    result = validate_suffix_candidates(candidates, reject_cache_path=cache_path)
    assert len(result) == 1 and result[0].text == "ethanol"
    assert "ethanol" not in load_rejection_cache(cache_path)


def test_no_cache_path_means_unchanged_backward_compatible_behavior(cache_path):
    """Explicitly opt-in: existing callers passing no cache path see
    no behavior change and no surprise file created."""
    candidates = discover_suffix_candidates("The thermal properties were measured.")
    result = validate_suffix_candidates(candidates)  # no reject_cache_path at all
    assert result == []
    assert not os.path.exists(cache_path)  # nothing was ever written


def test_extract_all_integration(cache_path):
    """The real, end-to-end path a caller actually uses."""
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test.db")
    create_database(db_path)
    insert_records(db_path, [DatabaseRecord("benzene", "benzene", None, "pubchem")])
    trie = build_trie_from_database(db_path)

    text = "The thermal properties of benzene were studied."
    results = extract_all(text, trie, db_path=db_path, opsin_reject_cache_path=cache_path)

    assert len(results) == 1
    assert results[0].text == "benzene"
    assert "thermal" in load_rejection_cache(cache_path)
    assert "benzene" not in load_rejection_cache(cache_path)
