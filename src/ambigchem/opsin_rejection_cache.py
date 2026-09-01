"""
opsin_rejection_cache.py

A real, persistent, real-time cache of words OPSIN has already,
definitively rejected as not being real chemical names.

Found valuable via live benchmarking: the exact same non-chemical
distractor words ("thermal", "radical", "orbital", "lone", "lethal",
"backbone", "nodal"...) recurred across many different real queries in
a single 60-query run, each one paying a full, real OPSIN subprocess
launch again - genuinely expensive on some machines (tens of seconds
per call, confirmed directly on a real HPC cluster).

OPSIN's answer for a given input string is deterministic - it has no
internal randomness, no notion of "context" beyond the string itself.
A rejection once is a rejection always. This cache exploits that fact
safely: once a word is confirmed rejected, it never needs a real OPSIN
call again, in this process or any future one.

Deliberately a plain, human-readable text file - one rejected word per
line - not a database. Easy to inspect, easy to diff, easy to delete
and start fresh if ever needed, no extra dependencies.
"""

from __future__ import annotations
import os
import threading

_write_lock = threading.Lock()


def load_rejection_cache(cache_path: str) -> set[str]:
    """Loads the real, currently-persisted set of rejected words. A
    cache file that doesn't exist yet is simply an empty cache - not
    an error."""
    if not os.path.exists(cache_path):
        return set()
    with open(cache_path, "r", encoding="utf-8") as f:
        return {line.strip().lower() for line in f if line.strip()}


def add_to_rejection_cache(word: str, cache_path: str) -> None:
    """Real-time update: called the MOMENT OPSIN rejects a word - not
    batched, not deferred - so this exact word never triggers a real
    OPSIN call again. A lock guards against two near-simultaneous
    writes corrupting each other within one process; re-checking
    membership right before writing avoids an unnecessary duplicate
    line if the same word was already added a moment before."""
    normalized = word.strip().lower()
    with _write_lock:
        if normalized in load_rejection_cache(cache_path):
            return
        with open(cache_path, "a", encoding="utf-8") as f:
            f.write(normalized + "\n")


def cache_size(cache_path: str) -> int:
    """Real, current count of distinct rejected words - useful for
    seeing the cache actually growing over real use."""
    return len(load_rejection_cache(cache_path))
