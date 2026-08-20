"""
elements.py

Bidirectional lookup between element symbols and names, for all 118
real, officially-named periodic table elements.

Handles a real, legitimate complication worth being explicit about:
several elements have genuinely different accepted spellings depending
on regional convention (British vs. American English) - "aluminium" vs
"aluminum", "sulfur" vs "sulphur", "caesium" vs "cesium". Both spellings
are treated as valid input, mapping to the same real element.
"""

from __future__ import annotations

# (symbol, canonical IUPAC name) for all 118 elements.
ELEMENT_DATA: list[tuple[str, str]] = [
    ("H", "Hydrogen"), ("He", "Helium"), ("Li", "Lithium"), ("Be", "Beryllium"),
    ("B", "Boron"), ("C", "Carbon"), ("N", "Nitrogen"), ("O", "Oxygen"),
    ("F", "Fluorine"), ("Ne", "Neon"), ("Na", "Sodium"), ("Mg", "Magnesium"),
    ("Al", "Aluminium"), ("Si", "Silicon"), ("P", "Phosphorus"), ("S", "Sulfur"),
    ("Cl", "Chlorine"), ("Ar", "Argon"), ("K", "Potassium"), ("Ca", "Calcium"),
    ("Sc", "Scandium"), ("Ti", "Titanium"), ("V", "Vanadium"), ("Cr", "Chromium"),
    ("Mn", "Manganese"), ("Fe", "Iron"), ("Co", "Cobalt"), ("Ni", "Nickel"),
    ("Cu", "Copper"), ("Zn", "Zinc"), ("Ga", "Gallium"), ("Ge", "Germanium"),
    ("As", "Arsenic"), ("Se", "Selenium"), ("Br", "Bromine"), ("Kr", "Krypton"),
    ("Rb", "Rubidium"), ("Sr", "Strontium"), ("Y", "Yttrium"), ("Zr", "Zirconium"),
    ("Nb", "Niobium"), ("Mo", "Molybdenum"), ("Tc", "Technetium"), ("Ru", "Ruthenium"),
    ("Rh", "Rhodium"), ("Pd", "Palladium"), ("Ag", "Silver"), ("Cd", "Cadmium"),
    ("In", "Indium"), ("Sn", "Tin"), ("Sb", "Antimony"), ("Te", "Tellurium"),
    ("I", "Iodine"), ("Xe", "Xenon"), ("Cs", "Caesium"), ("Ba", "Barium"),
    ("La", "Lanthanum"), ("Ce", "Cerium"), ("Pr", "Praseodymium"), ("Nd", "Neodymium"),
    ("Pm", "Promethium"), ("Sm", "Samarium"), ("Eu", "Europium"), ("Gd", "Gadolinium"),
    ("Tb", "Terbium"), ("Dy", "Dysprosium"), ("Ho", "Holmium"), ("Er", "Erbium"),
    ("Tm", "Thulium"), ("Yb", "Ytterbium"), ("Lu", "Lutetium"), ("Hf", "Hafnium"),
    ("Ta", "Tantalum"), ("W", "Tungsten"), ("Re", "Rhenium"), ("Os", "Osmium"),
    ("Ir", "Iridium"), ("Pt", "Platinum"), ("Au", "Gold"), ("Hg", "Mercury"),
    ("Tl", "Thallium"), ("Pb", "Lead"), ("Bi", "Bismuth"), ("Po", "Polonium"),
    ("At", "Astatine"), ("Rn", "Radon"), ("Fr", "Francium"), ("Ra", "Radium"),
    ("Ac", "Actinium"), ("Th", "Thorium"), ("Pa", "Protactinium"), ("U", "Uranium"),
    ("Np", "Neptunium"), ("Pu", "Plutonium"), ("Am", "Americium"), ("Cm", "Curium"),
    ("Bk", "Berkelium"), ("Cf", "Californium"), ("Es", "Einsteinium"), ("Fm", "Fermium"),
    ("Md", "Mendelevium"), ("No", "Nobelium"), ("Lr", "Lawrencium"), ("Rf", "Rutherfordium"),
    ("Db", "Dubnium"), ("Sg", "Seaborgium"), ("Bh", "Bohrium"), ("Hs", "Hassium"),
    ("Mt", "Meitnerium"), ("Ds", "Darmstadtium"), ("Rg", "Roentgenium"), ("Cn", "Copernicium"),
    ("Nh", "Nihonium"), ("Fl", "Flerovium"), ("Mc", "Moscovium"), ("Lv", "Livermorium"),
    ("Ts", "Tennessine"), ("Og", "Oganesson"),
]

# Real, legitimate alternate spellings - both map to the same symbol.
_SPELLING_VARIANTS: dict[str, str] = {
    "aluminum": "Al",
    "sulphur": "S",
    "cesium": "Cs",
}

SYMBOL_TO_NAME: dict[str, str] = dict(ELEMENT_DATA)
_NAME_TO_SYMBOL: dict[str, str] = {name.lower(): symbol for symbol, name in ELEMENT_DATA}


def symbol_to_name(symbol: str) -> str | None:
    """Returns the canonical element name for a real symbol, or None."""
    return SYMBOL_TO_NAME.get(symbol)


def name_to_symbol(name: str) -> str | None:
    """Returns the real element symbol for a name (case-insensitive,
    accepts common spelling variants), or None."""
    lowered = name.lower()
    return _NAME_TO_SYMBOL.get(lowered) or _SPELLING_VARIANTS.get(lowered)
