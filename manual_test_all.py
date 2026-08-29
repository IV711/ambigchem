"""
manual_test_all.py

A real, standalone, menu-driven script for manually testing EVERY module
in ambigchem with your own inputs - no pytest involved. Run it, pick a
number, type your own real input, see genuine output.

    python manual_test_all.py
"""

import os


def _organic_available():
    try:
        import py2opsin  # noqa
        import rdkit  # noqa
        return True
    except ImportError:
        return False


def test_elements():
    from ambigchem.elements import name_to_symbol, symbol_to_name
    print("\n-- elements.py: name <-> symbol lookup --")
    while True:
        text = input("Enter an element NAME or SYMBOL (blank to go back): ").strip()
        if not text:
            return
        symbol = name_to_symbol(text)
        name = symbol_to_name(text)
        if symbol:
            print(f"  name_to_symbol({text!r}) -> {symbol!r}")
        if name:
            print(f"  symbol_to_name({text!r}) -> {name!r}")
        if not symbol and not name:
            print(f"  Not recognized as either a real element name or symbol.")


def test_covalent():
    from ambigchem.covalent import parse_covalent_name
    print("\n-- covalent.py: e.g. 'dinitrogen pentoxide', 'carbon monoxide' --")
    while True:
        text = input("Enter a covalent compound name (blank to go back): ").strip()
        if not text:
            return
        result = parse_covalent_name(text)
        print(f"  formula={result.formula}")


def test_ionic():
    from ambigchem.ionic import parse_ionic_name
    print("\n-- ionic.py: e.g. 'aluminum carbonate', 'iron oxide', 'iron(III) oxide' --")
    while True:
        text = input("Enter an ionic compound name (blank to go back): ").strip()
        if not text:
            return
        result = parse_ionic_name(text)
        if result.ambiguous:
            print(f"  AMBIGUOUS - real candidates: {result.all_candidates}")
        else:
            print(f"  formula={result.formula}")


def test_organic():
    if not _organic_available():
        print("\n  Skipped - the 'organic' extra isn't installed here (pip install ambigchem[organic]).")
        return
    from ambigchem.organic import parse_organic_name
    print("\n-- organic.py: e.g. 'ethanol', 'benzene', '2,3-dimethylbutane' --")
    while True:
        text = input("Enter an organic compound name (blank to go back): ").strip()
        if not text:
            return
        result = parse_organic_name(text)
        print(f"  formula={result.formula}  smiles={result.smiles}")


def test_orchestrator():
    from ambigchem.orchestrator import parse_compound_name
    print("\n-- orchestrator.py: tries covalent/ionic/organic automatically --")
    while True:
        text = input("Enter ANY compound name (blank to go back): ").strip()
        if not text:
            return
        result = parse_compound_name(text)
        if result.ambiguous:
            print(f"  AMBIGUOUS - candidates: {result.all_candidates}  (method={result.method})")
        else:
            print(f"  formula={result.formula}  method={result.method}")


def test_clarification():
    from ambigchem.orchestrator import parse_compound_name
    from ambigchem.clarification import from_ionic_ambiguity, from_formula_ambiguity
    print("\n-- clarification.py: enter something genuinely ambiguous, e.g. 'manganese oxide' --")
    while True:
        text = input("Enter a compound name (blank to go back): ").strip()
        if not text:
            return
        result = parse_compound_name(text)
        if not result.ambiguous:
            print(f"  Not ambiguous - resolved directly to {result.formula} (method={result.method})")
            continue
        clarification = from_ionic_ambiguity(text, result.all_candidates)
        print(f"  {clarification.question}")


def test_structure_generation():
    if not _organic_available():
        print("\n  Skipped - the 'organic' extra isn't installed here (pip install ambigchem[organic]).")
        return
    from ambigchem.organic_structure import generate_3d_structure
    print("\n-- organic_structure.py: real 3D coordinates for an organic molecule --")
    while True:
        text = input("Enter an organic compound name (blank to go back): ").strip()
        if not text:
            return
        result = generate_3d_structure(text)
        if result.success:
            print(f"  Success - {result.num_atoms} atoms. First few lines of xyz:")
            print("  " + "\n  ".join(result.xyz_content.splitlines()[:5]))
        else:
            print(f"  Failed: {result.error}")


def test_structure_convert():
    from ambigchem.structure_convert import cif_to_xyz, xyz_to_cif, MissingLatticeError
    print("\n-- structure_convert.py: needs a REAL .cif or .xyz file path on disk --")
    direction = input("Convert (1) cif->xyz or (2) xyz->cif? [1/2, blank to go back]: ").strip()
    if not direction:
        return
    if direction == "1":
        src = input("Path to a real .cif file: ").strip()
        dst = input("Output .xyz path: ").strip()
        if not os.path.exists(src):
            print(f"  '{src}' does not exist.")
            return
        cif_to_xyz(src, dst)
        print(f"  Wrote {dst}")
    elif direction == "2":
        src = input("Path to a real .xyz file: ").strip()
        dst = input("Output .cif path: ").strip()
        if not os.path.exists(src):
            print(f"  '{src}' does not exist.")
            return
        try:
            xyz_to_cif(src, dst)
            print(f"  Wrote {dst}")
        except MissingLatticeError as e:
            print(f"  MissingLatticeError (expected for a plain molecule .xyz): {e}")
            provide = input("  Supply real cell params 'a b c alpha beta gamma'? (blank to skip): ").strip()
            if provide:
                a, b, c, alpha, beta, gamma = map(float, provide.split())
                xyz_to_cif(src, dst, cell=(a, b, c, alpha, beta, gamma))
                print(f"  Wrote {dst}")


def test_local_database():
    from ambigchem.local_database import lookup
    print("\n-- local_database.py: needs a REAL database you've already built --")
    db_path = input("Path to your real database (e.g. compounds.db): ").strip()
    if not db_path or not os.path.exists(db_path):
        print(f"  '{db_path}' does not exist.")
        return
    while True:
        text = input("Enter a compound name to look up (blank to go back): ").strip()
        if not text:
            return
        result = lookup(db_path, text)
        print(f"  {result}")


def test_database_lookup():
    from ambigchem.database_lookup import resolve_via_database, MockPubChemLookup
    print("\n-- database_lookup.py: tries OPSIN first, falls back to database --")
    print("(Using an EMPTY mock database here - only OPSIN-resolvable names will work)")
    empty_mock = MockPubChemLookup(fake_results={})
    while True:
        text = input("Enter a compound name (blank to go back): ").strip()
        if not text:
            return
        result = resolve_via_database(text, empty_mock)
        print(f"  {result}")


MENU = {
    "1": ("elements.py - name <-> symbol", test_elements),
    "2": ("covalent.py - covalent naming", test_covalent),
    "3": ("ionic.py - ionic naming (may be ambiguous)", test_ionic),
    "4": ("organic.py - organic naming", test_organic),
    "5": ("orchestrator.py - unified single-compound resolution", test_orchestrator),
    "6": ("clarification.py - real ambiguity questions", test_clarification),
    "7": ("organic_structure.py - real 3D structure generation", test_structure_generation),
    "8": ("structure_convert.py - cif <-> xyz (needs real files)", test_structure_convert),
    "9": ("local_database.py - offline lookup (needs your real db)", test_local_database),
    "10": ("database_lookup.py - OPSIN-first fallback resolution", test_database_lookup),
}


def main():
    print("=" * 60)
    print("ambigchem - manual module testing")
    print("=" * 60)
    print("(For full-sentence text extraction, use test_extraction_manually.py instead)")
    while True:
        print("\nWhich module do you want to test?")
        for key, (label, _) in MENU.items():
            print(f"  {key}. {label}")
        print("  0. Exit")
        choice = input("> ").strip()
        if choice == "0" or choice.lower() in ("quit", "exit"):
            print("Goodbye.")
            break
        if choice in MENU:
            _, func = MENU[choice]
            try:
                func()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye.")
                break
        else:
            print("Not a valid option.")


if __name__ == "__main__":
    main()
