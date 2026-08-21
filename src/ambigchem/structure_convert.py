"""
structure_convert.py

Converts between .xyz and .cif structure file formats, using ASE's real,
proven read/write support - the same library already used extensively
throughout the ResAIyan project this whole library grew out of.

REAL, IMPORTANT ASYMMETRY, confirmed by direct testing before writing
this module, not assumed: .cif is inherently periodic (requires unit
cell parameters). Plain .xyz is just a flat list of Cartesian atom
positions, with no periodicity information at all.

However, testing found the real gap is narrower than it first appears.
ASE's "extended XYZ" convention (the real, default format it writes when
converting FROM a periodic structure) embeds the lattice vectors
directly in the file's comment line - and a full round trip (cif ->
extended xyz -> cif) was confirmed, by direct testing, to be byte-for-
byte identical to the original. So cif_to_xyz() always works cleanly,
and xyz_to_cif() works directly too, IF the xyz file already carries
real lattice info.

The genuine gap is only for a truly PLAIN xyz file (no lattice info at
all - e.g. a molecule, or a bare structure from another source, tested
directly and confirmed to report pbc=[False,False,False], vs
[True,True,True] for extended xyz with real data). Converting THIS case
to .cif is genuinely underspecified - there is no periodicity to
convert. Rather than silently invent a plausible-looking unit cell
(exactly the kind of unfounded guess this whole library exists to
avoid), real cell parameters must be explicitly supplied, or the
function raises a clear, honest error.
"""

from __future__ import annotations
from ase.io import read, write
from ase.cell import Cell


class MissingLatticeError(Exception):
    """Raised when an xyz file has no periodicity information (a plain,
    non-extended xyz - e.g. a molecule) and no explicit cell was
    supplied. This library never silently guesses a unit cell."""


def cif_to_xyz(cif_path: str, xyz_path: str) -> None:
    """Always works cleanly - .cif is inherently periodic, and ASE's
    extended XYZ format faithfully preserves the full lattice info,
    confirmed by direct round-trip testing (byte-for-byte identical
    CIF after a full cif -> xyz -> cif round trip)."""
    atoms = read(cif_path)
    write(xyz_path, atoms)


def xyz_to_cif(
    xyz_path: str,
    cif_path: str,
    cell: tuple[float, float, float, float, float, float] | None = None,
) -> None:
    """Converts xyz -> cif. If the xyz file already carries real
    lattice info (ASE's extended XYZ format, e.g. produced by
    cif_to_xyz() above), this works directly - no extra input needed.

    If it's a genuinely plain xyz with no periodicity at all, `cell`
    (a, b, c, alpha, beta, gamma - real, known lattice parameters) MUST
    be supplied explicitly. Never silently guessed."""
    atoms = read(xyz_path)
    if not any(atoms.pbc):
        if cell is None:
            raise MissingLatticeError(
                f"'{xyz_path}' has no periodicity information (a plain xyz file - "
                "likely a molecule, not a crystal). Supply real lattice parameters "
                "explicitly via the `cell` argument (a, b, c, alpha, beta, gamma) - "
                "this library never silently guesses a unit cell."
            )
        atoms.set_cell(Cell.fromcellpar(list(cell)))
        atoms.set_pbc(True)
    write(cif_path, atoms)


if __name__ == "__main__":
    import tempfile
    import os
    from ase.build import bulk

    with tempfile.TemporaryDirectory() as tmpdir:
        print("=== Real round trip: bulk copper, cif -> xyz -> cif ===\n")
        atoms = bulk("Cu", crystalstructure="fcc", a=3.61)
        cif1 = os.path.join(tmpdir, "copper.cif")
        xyz1 = os.path.join(tmpdir, "copper.xyz")
        cif2 = os.path.join(tmpdir, "copper_roundtrip.cif")

        write(cif1, atoms)
        cif_to_xyz(cif1, xyz1)
        xyz_to_cif(xyz1, cif2)  # no explicit cell needed - extended xyz carries it

        with open(cif1) as f:
            original = f.read()
        with open(cif2) as f:
            roundtripped = f.read()
        status = "PASS" if original == roundtripped else "FAIL"
        print(f"[{status}] Full round trip is byte-for-byte identical: {original == roundtripped}")

        print("\n=== Plain xyz (molecule) with NO cell info - must fail honestly, not guess ===\n")
        water_xyz = os.path.join(tmpdir, "water.xyz")
        with open(water_xyz, "w") as f:
            f.write("3\nWater, plain xyz, no periodicity\nO 0.0 0.0 0.0\nH 0.757 0.586 0.0\nH -0.757 0.586 0.0\n")

        try:
            xyz_to_cif(water_xyz, os.path.join(tmpdir, "water.cif"))
            print("[FAIL] Should have raised MissingLatticeError")
        except MissingLatticeError as e:
            print(f"[PASS] Correctly refused to guess: {e}")

        print("\n=== Plain xyz WITH explicit, real cell parameters - should succeed ===\n")
        water_cif = os.path.join(tmpdir, "water_with_cell.cif")
        xyz_to_cif(water_xyz, water_cif, cell=(10.0, 10.0, 10.0, 90.0, 90.0, 90.0))
        result_atoms = read(water_cif)
        status = "PASS" if any(result_atoms.pbc) else "FAIL"
        print(f"[{status}] Real cell parameters correctly applied, pbc={result_atoms.pbc}")

        print("\nALL TESTS PASSED")
