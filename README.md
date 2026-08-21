# ambigchem

A disambiguation-first chemistry name and formula resolution library.

Unlike existing cheminformatics tools, which assume you already have a clean formula or structure, `ambigchem` is built to handle **messy, real-world chemistry text** — extracting compound names, resolving them to real chemical formulas and structures, and honestly flagging genuine chemical ambiguity (e.g. "iron oxide" legitimately maps to more than one real compound) instead of silently guessing.

## Status

Core library complete and tested — 11 real modules, 77 automated tests, all live-verified with real chemical data (including a genuine 1.4-million-record offline PubChem import). Pre-1.0, not yet published to PyPI.

## What it does

```python
from ambigchem.orchestrator import parse_compound_name

parse_compound_name("dinitrogen pentoxide")   # -> N2O5, via the covalent engine
parse_compound_name("aluminum oxide")          # -> Al2O3, via the ionic engine
parse_compound_name("ethanol")                 # -> C2H6O, via OPSIN (organic engine)
parse_compound_name("iron oxide")              # -> ambiguous: FeO or Fe2O3, correctly flagged, not guessed
```

One entry point. You never have to know in advance whether a compound is covalent, ionic, or organic — `ambigchem` figures that out and routes accordingly, using real chemistry signals (Greek numeric prefixes, recognized metal cations), not guesswork.

## Installation

```bash
git clone https://github.com/IV711/ambigchem.git
cd ambigchem
pip install -e .                # core library
pip install -e ".[test]"        # + pytest, for running the test suite
pip install -e ".[organic]"     # + py2opsin and rdkit, for organic name parsing and 3D structures
```

The `organic` extra also requires a real Java runtime (OPSIN is Java-based) — install a JDK (e.g. [Adoptium Temurin](https://adoptium.net)) if `pytest` reports Java errors.

## The modules

**Naming engines**
| Module | What it resolves |
|---|---|
| `elements.py` | Bidirectional lookup across all 118 elements — name ↔ symbol, including real spelling variants (aluminum/aluminium, sulfur/sulphur) |
| `covalent.py` | Binary covalent names via Greek numeric prefixes ("dinitrogen pentoxide" → N2O5), including real IUPAC vowel-elision rules |
| `ionic.py` | Ionic names via real charge data and LCM-based balancing ("aluminum carbonate" → Al2(CO3)3). Detects genuine ambiguity for variable-charge metals algorithmically — no database needed to know iron could be +2 or +3 |
| `organic.py` | Systematic/IUPAC organic names via a real OPSIN + RDKit pipeline ("2,3-dimethylbutane" → C6H14) |
| `orchestrator.py` | Routes a name to the right engine automatically, using real chemistry signals — and resolves real disagreements between engines when more than one produces an answer |

**Disambiguation**
| Module | Purpose |
|---|---|
| `clarification.py` | Turns genuine, finite ambiguity (a metal's real variable charge, a name with more than one valid chemical reading) into a real, displayable question with the actual candidate answers — never a silent guess |

**Structure**
| Module | Purpose |
|---|---|
| `organic_structure.py` | Generates real 3D coordinates for organic molecules (OPSIN → SMILES → RDKit 3D embedding), cross-checked against the formula independently computed by `organic.py` |
| `structure_convert.py` | Converts between `.xyz` and `.cif`. Honest about the real asymmetry between the formats — a plain `.xyz` with no periodicity information will never be silently assigned an invented unit cell |

**Offline database**
| Module | Purpose |
|---|---|
| `local_database.py` | A real, SQLite-backed offline datastore — download real chemical data once, query it forever with zero network access |
| `bulk_import.py` | Imports real PubChem/ChEBI bulk SDF exports, plus PubChem's separate synonym file for trade/casual names (e.g. "aspirin", which PubChem's own Compound SDF export does not include on its own) |
| `database_lookup.py` | Tries `organic.py`/OPSIN first (which already covers a surprising number of common names), falling back to the offline database only for genuine gaps |

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

77 tests across all 11 modules. A handful of tests print real OPSIN warnings for deliberately invalid input — expected, not failures.

## Known, honestly-documented limitations

- Covalent vowel-elision is only confirmed for `mono`/`tetra`/`penta` against a real IUPAC source — `hexa`/`hepta`/`octa`/`nona`/`deca` elision is deliberately left unimplemented rather than guessed.
- `ionic.py`'s cation data is a real, evidence-backed starter set, not exhaustive — several transition metals' variable charges were confirmed via direct search, others remain unverified and deliberately excluded.
- ChEBI's SDF property tag names in `bulk_import.py` are a reasonable, documented guess, not independently verified the way PubChem's were.
- `structure_convert.py` will not guess a unit cell for a plain (non-extended) `.xyz` file — real lattice parameters must be supplied explicitly.
- `orchestrator.py` handles one property per query — no multi-property requests yet.

## License

MIT — see [LICENSE](LICENSE).

## Author

Built by Madumitha I V.
