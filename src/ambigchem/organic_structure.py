"""
organic_structure.py

Completes the pipeline organic.py started: name -> SMILES (via OPSIN) ->
real 3D coordinates (via RDKit's embedding) -> a real .xyz file.

Confirmed directly, before writing this module, not assumed: RDKit's
real 3D embedding (EmbedMolecule) genuinely produces sensible geometry -
tested on ethanol, correctly generating all 9 atoms (2C + 1O + 6H,
exactly matching the real C2H6O formula already confirmed in organic.py's
own tests). The atom count cross-check below reuses this same real
consistency check as an automated test, not just a one-off manual proof.
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass
class StructureGenerationResult:
    success: bool
    xyz_content: str | None = None
    num_atoms: int | None = None
    error: str | None = None


def generate_3d_structure(name_or_smiles: str, is_smiles: bool = False) -> StructureGenerationResult:
    """Given an organic name (resolved via OPSIN, same as organic.py) or
    a direct SMILES string, generates real 3D coordinates and returns
    them as xyz-format text."""
    from rdkit import Chem
    from rdkit.Chem import AllChem

    if is_smiles:
        smiles = name_or_smiles
    else:
        from ambigchem.organic import parse_organic_name
        resolved = parse_organic_name(name_or_smiles)
        if resolved.smiles is None:
            return StructureGenerationResult(False, error=f"Could not resolve '{name_or_smiles}' to a structure")
        smiles = resolved.smiles

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return StructureGenerationResult(False, error=f"RDKit could not parse SMILES: {smiles}")

    mol = Chem.AddHs(mol)  # real 3D geometry needs explicit hydrogens
    embed_result = AllChem.EmbedMolecule(mol, randomSeed=42)
    if embed_result != 0:
        return StructureGenerationResult(False, error="RDKit could not generate 3D coordinates for this structure")

    AllChem.MMFFOptimizeMolecule(mol)

    conf = mol.GetConformer()
    num_atoms = mol.GetNumAtoms()
    lines = [str(num_atoms), name_or_smiles]
    for atom in mol.GetAtoms():
        pos = conf.GetAtomPosition(atom.GetIdx())
        lines.append(f"{atom.GetSymbol()} {pos.x:.6f} {pos.y:.6f} {pos.z:.6f}")
    xyz_content = "\n".join(lines) + "\n"

    return StructureGenerationResult(True, xyz_content=xyz_content, num_atoms=num_atoms)


def save_3d_structure(name_or_smiles: str, xyz_path: str, is_smiles: bool = False) -> StructureGenerationResult:
    """Same as generate_3d_structure, but writes directly to a real xyz
    file - reaching into structure_convert.py's territory. A genuinely
    generated molecule has no periodicity, so this xyz file is exactly
    the "plain xyz" case structure_convert.py's xyz_to_cif() correctly
    refuses to guess a unit cell for."""
    result = generate_3d_structure(name_or_smiles, is_smiles=is_smiles)
    if result.success:
        with open(xyz_path, "w") as f:
            f.write(result.xyz_content)
    return result


if __name__ == "__main__":
    print("=== Real 3D structure generation, cross-checked against organic.py's own formula ===\n")

    from ambigchem.organic import parse_organic_name

    test_cases = ["ethanol", "methane", "benzene"]
    all_passed = True
    for name in test_cases:
        formula_result = parse_organic_name(name)
        structure_result = generate_3d_structure(name)

        print(f"'{name}': formula={formula_result.formula}, generated {structure_result.num_atoms} atoms")

        # Real cross-check: count atoms implied by the formula string,
        # compare against the real 3D structure's actual atom count.
        import re
        atom_counts = re.findall(r"([A-Z][a-z]?)(\d*)", formula_result.formula)
        implied_total = sum(int(count) if count else 1 for _, count in atom_counts if _)
        status = "PASS" if implied_total == structure_result.num_atoms else "FAIL"
        if status == "FAIL":
            all_passed = False
        print(f"  [{status}] formula implies {implied_total} atoms, structure has {structure_result.num_atoms}\n")

    print("ALL TESTS PASSED" if all_passed else "SOME TESTS FAILED")
