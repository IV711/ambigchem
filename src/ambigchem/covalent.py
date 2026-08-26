"""
covalent.py

Names binary covalent (non-metal) compounds algorithmically - e.g.
"dinitrogen pentoxide" -> N2O5 - without a database lookup.

REAL, VERIFIED CHEMISTRY NOTE, worth being precise about: elision of a
prefix's final vowel before a vowel-starting word is not simply "always
happens." Directly checked against IUPAC's own 2005 Brief Guide to
Inorganic Nomenclature, which states elision is officially restricted to
the single case of "monoxide" - "pentaoxide" is explicitly given there as
the strict, correct form. However, multiple independent sources confirm
elided forms (pentoxide, tetroxide) are the dominant convention in real
ACS-style and US general chemistry usage, and both spellings genuinely
coexist in current practice.

Rather than enforce one convention as "correct," this engine accepts
BOTH forms as valid input - the same "real spelling variants" design
already used for aluminum/aluminium in elements.py. Only mono, tetra,
and penta are treated as elidable here, since those are the specific
prefixes multiple independent sources confirmed; hexa/hepta/octa/nona/deca
eliding before a vowel is NOT verified and is deliberately left
unimplemented rather than guessed at. CONFIRMED DECISIVELY, not merely
unverified: IUPAC's own 2005 guide states plainly "there is no elision
of vowels... except in the special case of monoxide" - extending
elision further would be actively wrong, not just unconfirmed.

REAL AMBIGUITY DETECTION, added after live user testing: a BARE,
unprefixed name (e.g. "nitrogen oxide", no prefix on either word at
all) for an element pair with multiple, real, well-known compounds is
genuinely, colloquially ambiguous - confirmed via direct search: six
real, consistently-cited nitrogen oxides exist (N2O, NO, NO2, N2O3,
N2O4, N2O5), and casual usage of "nitrogen oxide" does not reliably
specify which. This is architecturally DIFFERENT from ionic.py's
ambiguity (which comes from a cation's variable real charge) - here,
the literal parse of "nitrogen oxide" (no prefix -> count 1 on both
sides) is technically well-defined as NO, but that would silently hide
the real fact that this bare phrasing doesn't reliably distinguish
between six genuine compounds. A small, curated, deliberately
NOT-exhaustive starter set (KNOWN_MULTI_COMPOUND_PAIRS below) - adding
more elements (sulfur, carbon, phosphorus, all of which also have
multiple real oxides) would need their own real verification, not
assumed from this one confirmed case.
"""

from __future__ import annotations
from dataclasses import dataclass
from ambigchem.elements import ELEMENT_DATA, SPELLING_VARIANTS

PREFIXES: dict[str, int] = {
    "mono": 1, "di": 2, "tri": 3, "tetra": 4, "penta": 5,
    "hexa": 6, "hepta": 7, "octa": 8, "nona": 9, "deca": 10,
}

# Confirmed via direct source-checking - see module docstring. Deliberately
# does NOT include hexa/hepta/octa/nona/deca, since their elision before a
# vowel was not verified.
_ELIDABLE_PREFIXES = {"mono", "tetra", "penta"}

# The "-ide" form used for the second element in a binary covalent name.
# Genuinely irregular real IUPAC forms - not derivable from element names
# by a simple suffix rule (e.g. "oxide" from "oxygen" isn't a clean swap).
#
# REAL, VERIFIED ADDITION: "plumbide" (Pb) and "stannide" (Sn) confirmed
# via direct search against dedicated real reference sources - both are
# genuine, established terms, from the same Latin-root pattern as their
# chemical symbols (Pb <- plumbum, Sn <- stannum). HONEST SCOPE NOTE:
# real plumbide/stannide compounds are often Zintl-phase/intermetallic
# species with complex polyatomic anion clusters (e.g. Sn9^4-), not
# simple 1:1 stoichiometry - some real compounds using these words will
# be beyond what this simple counting engine can correctly parse, even
# though the dictionary entry itself is genuine.
#
# DELIBERATELY NOT ADDED, despite fitting the same Latin-root pattern:
# "ferride" (Fe) and "cupride" (Cu) were NOT confirmed by direct search -
# iron and copper's Latin roots are certainly real (ferric/ferrous/
# ferrate/ferrite; cupric/cuprous), but whether "ferride"/"cupride"
# specifically are the standard simple binary anion forms is unverified.
# Left out rather than guessed at.
#
# ALSO DELIBERATELY NOT ADDED: the broader set of regularly-formed
# transition/post-transition "-ide" terms (scandide, titanide, vanadide,
# chromide, manganide, cobaltide, nickelide, zincide, gallide, germanide,
# indide, thallide, bismuthide) - individually plausible by the regular
# pattern, but none independently verified. A real "needs verification"
# backlog, not bulk-added on pattern-matching alone.
IDE_FORMS: dict[str, str] = {
    "oxide": "O", "nitride": "N", "carbide": "C", "chloride": "Cl",
    "sulfide": "S", "sulphide": "S", "fluoride": "F", "bromide": "Br",
    "iodide": "I", "phosphide": "P", "hydride": "H", "boride": "B",
    "silicide": "Si", "selenide": "Se", "arsenide": "As",
    "antimonide": "Sb", "telluride": "Te", "astatide": "At",
    "plumbide": "Pb", "stannide": "Sn",
}


@dataclass
class CovalentParseResult:
    formula: str | None
    element1_count: int | None
    element2_count: int | None
    ambiguous: bool = False
    all_candidates: list[str] | None = None


def _all_prefix_candidates(word: str, base_lookup: dict[str, str]) -> list[tuple[int, str]]:
    """Every plausible (count, symbol) reading of `word` against
    `base_lookup` - the no-prefix case, every exact prefix match, and
    every confirmed-elidable prefix's elided match. Deliberately does
    NOT stop at the first success: returns everything valid, so the
    caller can detect genuine ambiguity (more than one real answer)
    instead of silently keeping whichever the algorithm happened to try
    first. Same "generate candidates, let validity decide" pattern
    already proven in formula_segmenter.py's segment_formula()."""
    word = word.lower()
    candidates = []

    if word in base_lookup:
        candidates.append((1, base_lookup[word]))

    for prefix, count in PREFIXES.items():
        if word.startswith(prefix):
            rest = word[len(prefix):]
            if rest in base_lookup:
                candidates.append((count, base_lookup[rest]))
        if prefix in _ELIDABLE_PREFIXES and word.startswith(prefix[:-1]):
            rest = word[len(prefix) - 1:]
            if rest in base_lookup and rest and rest[0] in "aeiou":
                candidates.append((count, base_lookup[rest]))

    seen = set()
    unique = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    return unique


_ELEMENT_LOOKUP: dict[str, str] = {n.lower(): s for s, n in ELEMENT_DATA}
_ELEMENT_LOOKUP.update(SPELLING_VARIANTS)  # real bug fix: "sulphur" etc. were missing here

# Real, curated (element, element) pairs where multiple, distinct, real,
# well-known compounds exist at different prefix combinations - see
# module docstring for the real, search-confirmed reasoning. A
# deliberate starter set: only nitrogen+oxygen is confirmed here.
KNOWN_MULTI_COMPOUND_PAIRS: dict[tuple[str, str], list[str]] = {
    ("N", "O"): ["NO", "NO2", "N2O", "N2O3", "N2O4", "N2O5"],
}


def parse_covalent_name(name: str) -> CovalentParseResult:
    words = name.strip().lower().split()
    if len(words) != 2:
        return CovalentParseResult(None, None, None)

    first_candidates = _all_prefix_candidates(words[0], _ELEMENT_LOOKUP)
    second_candidates = _all_prefix_candidates(words[1], IDE_FORMS)

    if not first_candidates or not second_candidates:
        return CovalentParseResult(None, None, None)

    # Combine every (first, second) pairing into a real candidate formula.
    # Reject any pairing where BOTH sides resolve to the SAME element -
    # real bug found via live user testing: "trinitrogen nitride" was
    # producing the nonsensical "N3N" (nitrogen appearing twice in one
    # formula, never how a real formula is written - even if this
    # somehow represented a real compound, it should combine to "N4",
    # not repeat the symbol). More fundamentally, a binary covalent name
    # genuinely needs two DIFFERENT elements - "X X-ide" isn't a valid
    # real naming pattern at all, so this is rejected outright rather
    # than combined.
    results = []
    for c1, s1 in first_candidates:
        for c2, s2 in second_candidates:
            if s1 == s2:
                continue
            formula = s1 + (str(c1) if c1 > 1 else "") + s2 + (str(c2) if c2 > 1 else "")
            results.append((formula, c1, c2))

    if not results:
        return CovalentParseResult(None, None, None)

    unique_by_formula = list({r[0]: r for r in results}.values())

    if len(unique_by_formula) == 1:
        formula, count1, count2 = unique_by_formula[0]

        # Real ambiguity check: only when BOTH words matched with no
        # prefix at all (a genuinely bare name), and the element pair
        # is a confirmed, real "multiple known compounds" case. A name
        # with an EXPLICIT prefix ("dinitrogen pentoxide") is a specific,
        # correctly-identified compound, never flagged here. Uses
        # first_candidates[0][1]/second_candidates[0][1] explicitly
        # (not leftover s1/s2 from the loop above) - a bare word always
        # produces exactly one candidate (confirmed directly), but
        # relying on loop-leftover variables here would be fragile and
        # non-obviously correct, not actually wrong today but not
        # worth keeping that way.
        if words[0] in _ELEMENT_LOOKUP and words[1] in IDE_FORMS:
            bare_symbol1 = first_candidates[0][1]
            bare_symbol2 = second_candidates[0][1]
            known_compounds = KNOWN_MULTI_COMPOUND_PAIRS.get((bare_symbol1, bare_symbol2))
            if known_compounds:
                return CovalentParseResult(
                    None, None, None, ambiguous=True, all_candidates=list(known_compounds),
                )

        return CovalentParseResult(formula, count1, count2, ambiguous=False)

    # Genuine ambiguity - more than one distinct, independently valid
    # formula. Flagged explicitly, never silently resolved to whichever
    # candidate happened to be generated first.
    return CovalentParseResult(
        None, None, None, ambiguous=True,
        all_candidates=[r[0] for r in unique_by_formula],
    )


if __name__ == "__main__":
    test_cases = [
        ("dinitrogen pentoxide", "N2O5"),      # elided form
        ("dinitrogen pentaoxide", "N2O5"),     # strict, non-elided IUPAC form - both must work
        ("carbon monoxide", "CO"),             # mono elided, count=1 implied on first word
        ("carbon dioxide", "CO2"),             # di does NOT elide - confirmed
        ("sulfur hexafluoride", "SF6"),        # no elision question (consonant follows)
        ("carbon tetrachloride", "CCl4"),      # no elision question (consonant follows)
        ("dinitrogen tetroxide", "N2O4"),      # tetra elided - real, well-known compound
        ("phosphorus pentachloride", "PCl5"),  # no elision question
    ]

    all_passed = True
    for name, expected in test_cases:
        result = parse_covalent_name(name)
        status = "PASS" if result.formula == expected else "FAIL"
        if status == "FAIL":
            all_passed = False
        print(f"[{status}] '{name}' -> {result.formula} (expected {expected})")

    print("\n=== Proving the ambiguity-detection mechanism itself works ===")
    print("(Constructs a deliberately overlapping fake dictionary - our real")
    print(" IDE_FORMS has no such overlap today, but this proves the machinery")
    print(" would correctly catch it if one is ever introduced.)\n")

    fake_lookup = {"oxide": "O", "xide": "Xx"}  # deliberately overlapping
    candidates = _all_prefix_candidates("monoxide", fake_lookup)
    print(f"Candidates for 'monoxide' against a deliberately ambiguous dictionary: {candidates}")
    assert len(candidates) == 2, "Should find BOTH the exact and elided readings as independently valid"
    print("PASS - genuine ambiguity correctly surfaced, not silently resolved to one answer\n")

    print("ALL TESTS PASSED" if all_passed else "\nSOME TESTS FAILED")
