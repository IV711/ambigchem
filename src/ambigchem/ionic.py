"""
ionic.py

Names ionic (metal cation + anion) compounds algorithmically, using real
charge data and LCM-based charge balancing - e.g. "aluminum carbonate"
-> Al2(CO3)3, matching the original worked example this engine was
designed from.

CORE ALGORITHM:
    1. Split into cation text (everything but the last word) and anion
       word (the last word) - a real, deliberate scope limit: two-word
       anion names ("hydrogen carbonate") aren't handled yet.
    2. Look up the cation's real charge(s). Fixed-charge metals (most
       main group) give exactly one. VARIABLE-charge metals (most
       transition metals) give MULTIPLE real possibilities - and if the
       query doesn't specify which one (no Roman numeral), that is a
       genuine, deterministic, ALGORITHMIC trigger for ambiguity - no
       database lookup needed to know iron could be +2 or +3, this
       falls straight out of real periodic table knowledge.
    3. Look up the anion's real charge - either a simple monatomic ion
       (charge derivable from periodic group, for the well-established
       cases - halogens, chalcogens, pnictogens) or a polyatomic ion
       (charge is NOT derivable, must be a real, looked-up fact).
    4. Compute the LCM of the absolute charges, giving each ion's count
       multiplier.
    5. Assemble the formula. BOTH cation and anion get wrapped in
       parentheses if they are polyatomic AND their count exceeds 1 -
       found via tracing "ammonium sulfate" by hand before writing any
       code: NH4+ is a polyatomic CATION, and naively only handling
       parenthesization on the anion side would have produced the
       nonsensical "NH42SO4" instead of the real "(NH4)2SO4".

HONEST SCOPE: cation/anion charge data below is a real, verified starter
set, not exhaustive - same honest framing as every other starter
dictionary in this project. Deliberately excludes carbide/boride from
simple monatomic charge assignment - real carbide chemistry is genuinely
variable (C4- in Al4C3, but the very common CaC2 uses the C2^2- acetylide
ion instead) - a fixed single-charge rule would get a well-known real
compound wrong.
"""

from __future__ import annotations
import math
import re
from dataclasses import dataclass

ROMAN_TO_INT: dict[str, int] = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7,
}

# Fixed-charge cations: (symbol, charge, is_polyatomic). Main group
# metals with one, reliable, real charge - plus ammonium, a real, common
# polyatomic cation. "scandium" added here (not as variable) after real
# search evidence: appears consistently with NO Roman numeral across
# real compound listings, consistent with Sc's well-established, always
# +3 behavior, much like aluminum.
FIXED_CATIONS: dict[str, tuple[str, int, bool]] = {
    "lithium": ("Li", 1, False), "sodium": ("Na", 1, False),
    "potassium": ("K", 1, False), "rubidium": ("Rb", 1, False),
    "caesium": ("Cs", 1, False), "cesium": ("Cs", 1, False),
    "beryllium": ("Be", 2, False), "magnesium": ("Mg", 2, False),
    "calcium": ("Ca", 2, False), "strontium": ("Sr", 2, False),
    "barium": ("Ba", 2, False),
    "aluminum": ("Al", 3, False), "aluminium": ("Al", 3, False),
    "zinc": ("Zn", 2, False), "silver": ("Ag", 1, False),
    "cadmium": ("Cd", 2, False),
    "scandium": ("Sc", 3, False),
    "ammonium": ("NH4", 1, True),
}

# Variable-charge cations: (symbol, [real possible charges]). Genuinely
# multiple real oxidation states - confirmed via direct search against
# real compound listings (patents, Wikipedia), not assumed. titanium,
# chromium, cobalt, manganese, nickel added after finding real, explicit
# Roman-numeral usage (e.g. "chromium(II) iodide", "chromium(III)
# iodide", "cobalt(III) iodide", "manganese(II) iodide") across extensive
# real sources. Deliberately conservative: only the states directly
# confirmed in real usage are included (e.g. manganese's real +4/+7
# states, tied to specific oxide/oxyanion contexts like MnO2/permanganate
# rather than typical simple binary salts, are left out).
VARIABLE_CATIONS: dict[str, tuple[str, list[int]]] = {
    "iron": ("Fe", [2, 3]),
    "copper": ("Cu", [1, 2]),
    "tin": ("Sn", [2, 4]),
    "lead": ("Pb", [2, 4]),
    "titanium": ("Ti", [3, 4]),
    "chromium": ("Cr", [2, 3]),
    "cobalt": ("Co", [2, 3]),
    "manganese": ("Mn", [2, 3]),
    "nickel": ("Ni", [2, 3]),
}

# Real, looked-up polyatomic anions - charge is not derivable from any
# rule, must be a real fact. (formula, charge)
POLYATOMIC_ANIONS: dict[str, tuple[str, int]] = {
    "carbonate": ("CO3", -2), "sulfate": ("SO4", -2),
    "nitrate": ("NO3", -1), "phosphate": ("PO4", -3),
    "hydroxide": ("OH", -1), "cyanide": ("CN", -1),
    "acetate": ("C2H3O2", -1),
}

# Simple monatomic anion charge, reliable ONLY for these groups
# (halogens -1, chalcogens -2, pnictogens -3). Deliberately excludes
# carbide/boride - see module docstring for why.
_MONATOMIC_ANION_CHARGE: dict[str, int] = {
    "F": -1, "Cl": -1, "Br": -1, "I": -1, "At": -1,
    "O": -2, "S": -2, "Se": -2, "Te": -2,
    "N": -3, "P": -3, "As": -3,
}


@dataclass
class IonicParseResult:
    formula: str | None
    ambiguous: bool = False
    all_candidates: list[str] | None = None


def _lookup_anion(word: str) -> tuple[str, int, bool] | None:
    """Returns (symbol_or_formula, charge, is_polyatomic), or None."""
    if word in POLYATOMIC_ANIONS:
        symbol, charge = POLYATOMIC_ANIONS[word]
        return (symbol, charge, True)
    from ambigchem.covalent import IDE_FORMS
    symbol = IDE_FORMS.get(word)
    if symbol and symbol in _MONATOMIC_ANION_CHARGE:
        return (symbol, _MONATOMIC_ANION_CHARGE[symbol], False)
    return None


def _parse_cation(text: str) -> list[tuple[str, int, bool]]:
    """Returns EVERY real, possible (symbol, charge, is_polyatomic)
    reading. Fixed-charge cations give exactly one. Variable-charge
    cations WITHOUT an explicit Roman numeral give MULTIPLE - genuine,
    algorithmic ambiguity."""
    text = text.strip().lower()
    roman_match = re.search(r"\(([ivx]+)\)", text)
    explicit_charge = None
    if roman_match:
        explicit_charge = ROMAN_TO_INT.get(roman_match.group(1).upper())
        text = text[:roman_match.start()].strip()

    if text in FIXED_CATIONS:
        symbol, charge, is_poly = FIXED_CATIONS[text]
        return [(symbol, charge, is_poly)]

    if text in VARIABLE_CATIONS:
        symbol, charges = VARIABLE_CATIONS[text]
        if explicit_charge is not None:
            if explicit_charge in charges:
                return [(symbol, explicit_charge, False)]
            return []  # explicitly specified a charge this element doesn't real have
        return [(symbol, c, False) for c in charges]

    return []


def _balance(cation_symbol: str, cation_charge: int, cation_is_poly: bool,
             anion_symbol: str, anion_charge: int, anion_is_poly: bool) -> str:
    a, b = abs(cation_charge), abs(anion_charge)
    lcm = a * b // math.gcd(a, b)
    cation_count = lcm // a
    anion_count = lcm // b

    if cation_count > 1 and cation_is_poly:
        cation_part = f"({cation_symbol}){cation_count}"
    else:
        cation_part = cation_symbol + (str(cation_count) if cation_count > 1 else "")

    if anion_count > 1 and anion_is_poly:
        anion_part = f"({anion_symbol}){anion_count}"
    else:
        anion_part = anion_symbol + (str(anion_count) if anion_count > 1 else "")

    return cation_part + anion_part


def parse_ionic_name(name: str) -> IonicParseResult:
    name = name.strip().lower()
    parts = name.rsplit(" ", 1)
    if len(parts) != 2:
        return IonicParseResult(None)
    cation_text, anion_word = parts

    anion = _lookup_anion(anion_word)
    if anion is None:
        return IonicParseResult(None)
    anion_symbol, anion_charge, anion_is_poly = anion

    cation_candidates = _parse_cation(cation_text)
    if not cation_candidates:
        return IonicParseResult(None)

    formulas = [
        _balance(c_sym, c_chg, c_poly, anion_symbol, anion_charge, anion_is_poly)
        for c_sym, c_chg, c_poly in cation_candidates
    ]
    unique = list(dict.fromkeys(formulas))

    if len(unique) == 1:
        return IonicParseResult(unique[0], ambiguous=False)
    return IonicParseResult(None, ambiguous=True, all_candidates=unique)


if __name__ == "__main__":
    test_cases = [
        ("aluminum carbonate", "Al2(CO3)3"),      # the original worked example
        ("ammonium sulfate", "(NH4)2SO4"),        # polyatomic CATION, the bug found by hand-tracing
        ("iron(III) oxide", "Fe2O3"),             # explicit Roman numeral resolves ambiguity
        ("iron(II) oxide", "FeO"),
        ("sodium chloride", "NaCl"),
        ("calcium hydroxide", "Ca(OH)2"),
        ("magnesium nitride", "Mg3N2"),
    ]
    all_passed = True
    for name, expected in test_cases:
        result = parse_ionic_name(name)
        status = "PASS" if result.formula == expected else "FAIL"
        if status == "FAIL":
            all_passed = False
        print(f"[{status}] '{name}' -> {result.formula} (expected {expected})")

    print("\n=== The real, algorithmic ambiguity trigger - no database needed ===")
    result = parse_ionic_name("iron oxide")
    print(f"'iron oxide' (no Roman numeral) -> ambiguous={result.ambiguous}, candidates={result.all_candidates}")
    assert result.ambiguous and set(result.all_candidates) == {"FeO", "Fe2O3"}
    print("PASS - genuine ambiguity correctly detected purely from iron's known variable charge\n")

    print("ALL TESTS PASSED" if all_passed else "SOME TESTS FAILED")