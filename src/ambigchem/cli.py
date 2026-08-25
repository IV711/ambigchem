"""
cli.py

A real, standalone, interactive command-line tool for exploring
ambigchem directly - no test files involved. Installed as a real
console entry point (`ambigchem`, see pyproject.toml's [project.scripts])
so trying the library is genuinely one command away after installation.

Runs every input through THREE real capabilities at once, since a user
exploring the library interactively benefits from seeing all of them
together, not guessing which mode applies:
    1. Single-compound resolution (orchestrator.parse_compound_name)
    2. Full-sentence compound extraction (text_extraction.extract_all)
    3. Property concept extraction (text_extraction.extract_property_concepts_from_text)
"""

from __future__ import annotations
import argparse
import sys


def _print_header(title: str) -> None:
    print(f"--- {title} ---")


def run_repl(db_path: str | None) -> None:
    from ambigchem.orchestrator import parse_compound_name
    from ambigchem.text_extraction import (
        extract_all, extract_property_concepts_from_text, load_or_build_trie,
    )
    import marisa_trie

    if db_path:
        print(f"Loading/building trie from {db_path} ...")
        trie = load_or_build_trie(db_path, trie_cache_path=db_path + ".trie_cache")
        print("Ready.\n")
    else:
        print("No database given (--db path/to/compounds.db) - running without")
        print("offline database lookup. Single-compound resolution, formula regex,")
        print("and OPSIN-validated suffix candidates still fully work.\n")
        trie = marisa_trie.Trie([])

    print("=" * 60)
    print("ambigchem interactive CLI")
    print("=" * 60)
    print("Enter a compound name (e.g. 'aluminum oxide') OR a full")
    print("sentence (e.g. 'The band gap of TiO2 was measured.').")
    print("Type 'quit' or 'exit' to stop.\n")

    while True:
        try:
            text = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if text.lower() in ("quit", "exit"):
            print("Goodbye.")
            break
        if not text:
            continue

        print()
        _print_header("Single-compound resolution (orchestrator)")
        result = parse_compound_name(text)
        if result.ambiguous:
            print(f"  AMBIGUOUS: could be {result.all_candidates}")
        elif result.formula:
            print(f"  {result.formula}  (method={result.method})")
        else:
            print("  (not resolvable as a single compound name)")

        _print_header("Full-sentence compound extraction")
        extracted = extract_all(text, trie, db_path=db_path)
        if extracted:
            for e in extracted:
                print(f"  {e.text!r}  formula={e.formula}  method={e.method}  [{e.start}:{e.end}]")
        else:
            print("  (no compounds found)")

        _print_header("Property concepts found")
        props = extract_property_concepts_from_text(text)
        if props:
            for p in props:
                print(f"  {p.text!r}  [{p.start}:{p.end}]")
        else:
            print("  (no property concepts found)")

        print()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ambigchem",
        description="Interactively explore the ambigchem library from the command line.",
    )
    parser.add_argument(
        "--db", default=None,
        help="Path to a real local_database.py SQLite database (optional - "
             "enables offline database lookup and real formula attachment "
             "for database matches).",
    )
    parser.add_argument(
        "query", nargs="?", default=None,
        help="Run a single query non-interactively and exit, instead of "
             "starting the interactive prompt.",
    )
    args = parser.parse_args()

    if args.query:
        # Non-interactive, single-shot mode - useful for scripting/piping.
        from ambigchem.orchestrator import parse_compound_name
        from ambigchem.text_extraction import extract_all, load_or_build_trie
        import marisa_trie

        trie = load_or_build_trie(args.db, trie_cache_path=args.db + ".trie_cache") if args.db else marisa_trie.Trie([])
        result = parse_compound_name(args.query)
        if result.formula:
            print(result.formula)
        elif result.ambiguous:
            print(f"AMBIGUOUS: {result.all_candidates}")
        else:
            extracted = extract_all(args.query, trie, db_path=args.db)
            if extracted:
                for e in extracted:
                    print(f"{e.text}\t{e.formula}\t{e.method}")
            else:
                print("No compounds found.", file=sys.stderr)
                sys.exit(1)
        return

    run_repl(args.db)


if __name__ == "__main__":
    main()
