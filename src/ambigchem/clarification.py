"""
clarification.py

When compound/formula resolution is ambiguous between a small, KNOWN,
finite set of real candidates - not "we don't know what you mean" but
"we know exactly which real options exist, and can't pick between them
algorithmically" - ask, instead of silently failing or guessing.

Ported from the ResAIyan extraction pipeline project, where this same
mechanism was first built and proven (real, live-tested clarification
requests for both a compound-formula ambiguity and a structure-type
ambiguity). Only the genuinely generic core is ported here: the
ClarificationRequest shape and from_formula_ambiguity(). The original
also had a from_structure_type_ambiguity() function (molecule vs.
crystal, for routing predictions to the right MLIP model) - deliberately
NOT ported, since that's a ResAIyan-specific concept with no place in a
general-purpose chemistry-naming library.

from_ionic_ambiguity() is new, built specifically for ionic.py's genuine,
algorithmic ambiguity trigger (a variable-charge metal named with no
Roman numeral) - given its own distinct 'kind' rather than reusing
from_formula_ambiguity()'s wording, since the ROOT CAUSE is genuinely
different even though the shape of the ambiguity (multiple real
candidates) is the same: a metal having more than one common real charge
is a different kind of fact than a name segmenting two different ways.
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass
class ClarificationRequest:
    kind: str              # "compound_formula" | "variable_oxidation_state"
    original_text: str     # what the user actually typed
    candidates: list[str]  # the real, specific options to choose between
    question: str          # a ready-to-display question


def from_formula_ambiguity(original_text: str, candidates: list[str]) -> ClarificationRequest:
    """Builds a clarification request from a formula-segmentation
    ambiguity (e.g. 'cocl2' -> CoCl2 or COCl2, both real compounds).
    Wording must handle any candidate count, not just exactly two -
    found via real testing in the original project, not anticipated in
    advance."""
    options = " or ".join(candidates)
    plural_phrase = "they are both real compounds" if len(candidates) == 2 else "they are all real compounds"
    return ClarificationRequest(
        kind="compound_formula",
        original_text=original_text,
        candidates=list(candidates),
        question=f"'{original_text}' could mean {options} - {plural_phrase}. Which did you mean?",
    )


def from_ionic_ambiguity(original_text: str, candidates: list[str]) -> ClarificationRequest:
    """Builds a clarification request from ionic.py's genuine, algorithmic
    ambiguity case - a metal with more than one real, common oxidation
    state, named with no Roman numeral (e.g. 'iron oxide' -> FeO or
    Fe2O3). Deliberately explains WHY it's ambiguous, not just THAT it
    is - more informative than generic formula-ambiguity wording, since
    the real cause here is a specific, nameable chemistry fact."""
    options = " or ".join(candidates)
    plural_phrase = "they are both real compounds" if len(candidates) == 2 else "they are all real compounds"
    return ClarificationRequest(
        kind="variable_oxidation_state",
        original_text=original_text,
        candidates=list(candidates),
        question=(
            f"'{original_text}' is ambiguous because this metal has more than one common charge. "
            f"It could be {options} - {plural_phrase}. Which did you mean?"
        ),
    )


if __name__ == "__main__":
    print("=== Building a real clarification request from ionic.py's genuine ambiguity ===\n")

    from ambigchem.ionic import parse_ionic_name

    result = parse_ionic_name("iron oxide")
    assert result.ambiguous is True

    clarification = from_ionic_ambiguity("iron oxide", result.all_candidates)
    print(clarification)
    assert set(clarification.candidates) == {"FeO", "Fe2O3"}
    assert clarification.kind == "variable_oxidation_state"
    print("\nPASS - real ambiguity from ionic.py turned into a real, displayable question")
