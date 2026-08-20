# ambigchem

A disambiguation-first chemistry name and formula resolution library.

Unlike existing cheminformatics tools, which assume you already have a clean formula or structure, `ambigchem` is built to handle **messy, real-world chemistry text** — extracting compound names, resolving them to real chemical formulas, and honestly flagging genuine chemical ambiguity (e.g. "iron oxide" legitimately maps to more than one real compound) instead of silently guessing.

## Status

Early development. Not yet published to PyPI.

## Installation (development)

```bash
git clone <repo-url>
cd ambigchem
pip install -e ".[test]"
```

## License

MIT — see [LICENSE](LICENSE).
