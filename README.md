# ambigchem

A disambiguation-first chemistry name and formula resolution library.

Unlike existing cheminformatics tools, which assume you already have a clean formula or structure, `ambigchem` is built to handle **messy, real-world chemistry text** — extracting compound names, resolving them to real chemical formulas and structures, and honestly flagging genuine chemical ambiguity (e.g. "iron oxide" legitimately maps to more than one real compound) instead of silently guessing.

## Status

Core library complete and extensively tested — 14 real modules, 166 automated tests, live-verified against real chemical data (including a genuine 1.4-million-record offline PubChem import) and extensive hands-on manual testing that found and fixed dozens of genuine bugs, several severe (including a real, ~2,800x performance fix). Pre-1.0.

## What it does

```python
from ambigchem.orchestrator import parse_compound_name

parse_compound_name("dinitrogen pentoxide")            # -> N2O5, via the covalent engine
parse_compound_name("aluminum oxide")                   # -> Al2O3, via the ionic engine
parse_compound_name("ethanol")                           # -> C2H6O, via OPSIN (organic engine)
parse_compound_name("iron oxide")                        # -> ambiguous: FeO or Fe2O3, correctly flagged, not guessed
parse_compound_name("nitrogen oxide")                     # -> ambiguous: 6 real nitrogen oxides, correctly flagged
parse_compound_name("cuprous oxide")                       # -> Cu2O, real classical -ous/-ic naming
parse_compound_name("copper(II) sulfate pentahydrate")      # -> CuSO4·5H2O, real hydrate notation
```

One entry point. You never have to know in advance whether a compound is covalent, ionic, organic, or a hydrate — `ambigchem` figures that out and routes accordingly, using real chemistry signals, not guesswork.

## Installation

```bash
pip install ambigchem                # core library
pip install ambigchem[test]          # + pytest, for running the test suite
pip install ambigchem[organic]       # + py2opsin and rdkit, for organic name parsing and 3D structures
```

Or from source:

```bash
git clone https://github.com/IV711/ambigchem.git
cd ambigchem
pip install -e ".[test,organic]"
```

The `organic` extra also requires a real Java runtime (OPSIN is Java-based) — install a JDK (e.g. [Adoptium Temurin](https://adoptium.net)) if you see Java errors.

### Command-line interface

Once installed, explore the library directly from a terminal — no Python script needed:

```bash
ambigchem "aluminum oxide"                # single-shot mode
ambigchem                                  # interactive mode
ambigchem --db compounds.db                # interactive mode, using your own offline database
```

## The modules

**Naming engines**
| Module | What it resolves |
|---|---|
| `elements.py` | Bidirectional lookup across all 118 elements — name ↔ symbol, including real spelling variants (aluminum/aluminium, sulfur/sulphur) |
| `covalent.py` | Binary covalent names via Greek numeric prefixes ("dinitrogen pentoxide" → N2O5), real IUPAC vowel-elision rules, and genuine bare-name ambiguity detection (e.g. "nitrogen oxide" → 6 real candidates, not a silent guess) |
| `ionic.py` | Ionic names via real charge data and LCM-based balancing ("aluminum carbonate" → Al2(CO3)3), real classical `-ous`/`-ic` naming (cuprous/cupric, ferrous/ferric...), and real SMILES generation for monatomic-ion pairs. Detects genuine ambiguity for variable-charge metals algorithmically |
| `organic.py` | Systematic/IUPAC organic names via a real OPSIN + RDKit pipeline ("2,3-dimethylbutane" → C6H14), with real charged-species rejection so a misleading formula is never silently returned |
| `hydrates.py` | Real crystalline hydrate names ("magnesium sulfate heptahydrate" → MgSO4·7H2O), reusing the orchestrator for the base compound |
| `orchestrator.py` | Routes a name to the right engine automatically — covalent, ionic, organic, or hydrate — resolving real disagreements between engines and propagating genuine ambiguity from any of them |

**Full-sentence extraction**
| Module | Purpose |
|---|---|
| `text_extraction.py` | Finds real compound mentions (and separately, property-concept mentions) anywhere in free-form text — five independently-proven phases (offline database, formula regex, OPSIN-validated organic suffixes, and orchestrator-based multi-word covalent/ionic names), combined with zero redundant work between phases |

**Disambiguation**
| Module | Purpose |
|---|---|
| `clarification.py` | Turns genuine, finite ambiguity into a real, displayable question with the actual candidate answers — never a silent guess |

**Structure**
| Module | Purpose |
|---|---|
| `organic_structure.py` | Generates real 3D coordinates for organic molecules (OPSIN → SMILES → RDKit 3D embedding), cross-checked against the formula independently computed by `organic.py` |
| `structure_convert.py` | Converts between `.xyz` and `.cif`. Honest about the real asymmetry between the formats — a plain `.xyz` with no periodicity information will never be silently assigned an invented unit cell |

**Offline database**
| Module | Purpose |
|---|---|
| `local_database.py` | A real, SQLite-backed offline datastore — download real chemical data once, query it forever with zero network access |
| `bulk_import.py` | Imports real PubChem/ChEBI bulk SDF exports, plus PubChem's separate synonym file, with a real, live-tested name-quality filter to keep out short/common-word noise |
| `database_lookup.py` | Tries `organic.py`/OPSIN first, falling back to the offline database only for genuine gaps |

## Extracting compounds from real sentences

```python
from ambigchem.text_extraction import extract_all, load_or_build_trie

trie = load_or_build_trie("compounds.db", trie_cache_path="compounds.db.trie_cache")

text = "We tested carbon monoxide and iron(III) oxide, along with aspirin."
for match in extract_all(text, trie, db_path="compounds.db"):
    print(match.text, match.method, match.formula)
# carbon monoxide     covalent   CO
# iron(III) oxide     ionic      Fe2O3
# aspirin             database   C9H8O4
```

## Building your own offline database

```python
from ambigchem.local_database import create_database
from ambigchem.bulk_import import import_sdf

create_database("compounds.db")

# Real PubChem bulk data: https://ftp.ncbi.nlm.nih.gov/pubchem/Compound/CURRENT-Full/SDF/
# Real synonym file (for trade names): https://ftp.ncbi.nlm.nih.gov/pubchem/Compound/Extras/CID-Synonym-filtered.gz
count = import_sdf(
    "Compound_000000001_000500000.sdf", "compounds.db",
    source="pubchem", synonym_path="CID-Synonym-filtered.txt",
)
```

Live-tested at real scale: a genuine run against this exact file range imported 1,408,594 name-to-formula records, entirely offline after the initial download.

## Running the tests

```bash
pytest -v
```

166 tests across 14 modules. A handful of tests print real OPSIN warnings for deliberately invalid input — expected, not failures.

## Known, honestly-documented limitations

- Covalent bare-name ambiguity detection (e.g. "nitrogen oxide" → 6 real candidates) is a real, curated set — confirmed individually for nitrogen, sulfur, carbon, and phosphorus oxides; not every element with multiple real compounds is covered yet.
- `ionic.py`'s cation data is a real, evidence-backed starter set, not exhaustive — several transition metals' variable charges and classical `-ous`/`-ic` names were confirmed via direct search, others (e.g. gold, cobalt's `-ous` form) remain unverified and deliberately excluded.
- Mixed-valence compounds (e.g. Pb3O4, "red lead") are not supported — the real atom ratio genuinely varies compound-by-compound (confirmed: Pb3O4 and Fe3O4 have *opposite* ratios) and can't be derived from charge-balancing alone.
- Ionic SMILES generation only covers purely monatomic-ion pairs (NaCl, CaCl2) — polyatomic ions (sulfate, carbonate) need their own, individually-verified SMILES strings, not yet done.
- `text_extraction.py`'s multi-word covalent/ionic matching has a real, documented pre-filter gap: multi-word organic names without an anion-like second word (e.g. "acetic acid") aren't caught by that phase.
- ChEBI's SDF property tag names in `bulk_import.py` are a reasonable, documented guess, not independently verified the way PubChem's were.
- `structure_convert.py` will not guess a unit cell for a plain (non-extended) `.xyz` file — real lattice parameters must be supplied explicitly.

## License

MIT — see [LICENSE](LICENSE).

## Author

Built by Madumitha I V.
