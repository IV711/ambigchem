"""
test_structure_convert.py

Real pytest coverage for cif_to_xyz()/xyz_to_cif(), including the
honest MissingLatticeError case - confirming this library refuses to
silently guess a unit cell rather than testing only the happy path.
"""

import os
import tempfile
import pytest
from ase.io import write, read
from ase.build import bulk
from ambigchem.structure_convert import cif_to_xyz, xyz_to_cif, MissingLatticeError


@pytest.fixture
def tmpdir():
    with tempfile.TemporaryDirectory() as d:
        yield d


def test_full_round_trip_is_byte_identical(tmpdir):
    """The core proof this module works correctly: a real crystal
    structure survives a complete cif -> xyz -> cif round trip with
    zero data loss."""
    atoms = bulk("Cu", crystalstructure="fcc", a=3.61)
    cif1 = os.path.join(tmpdir, "copper.cif")
    xyz1 = os.path.join(tmpdir, "copper.xyz")
    cif2 = os.path.join(tmpdir, "copper_roundtrip.cif")

    write(cif1, atoms)
    cif_to_xyz(cif1, xyz1)
    xyz_to_cif(xyz1, cif2)

    with open(cif1) as f:
        original = f.read()
    with open(cif2) as f:
        roundtripped = f.read()
    assert original == roundtripped


def test_cif_to_xyz_preserves_periodicity(tmpdir):
    """Confirms the intermediate xyz genuinely carries real lattice
    info, not just that the final round trip happens to work out."""
    atoms = bulk("Cu", crystalstructure="fcc", a=3.61)
    cif_path = os.path.join(tmpdir, "copper.cif")
    xyz_path = os.path.join(tmpdir, "copper.xyz")
    write(cif_path, atoms)
    cif_to_xyz(cif_path, xyz_path)

    result = read(xyz_path)
    assert all(result.pbc)


def test_plain_xyz_without_cell_raises_honest_error(tmpdir):
    """The real point of this module: a genuinely underspecified
    conversion (plain molecule xyz, no periodicity info at all) must
    fail with a clear, honest error - never silently guess a unit cell."""
    water_xyz = os.path.join(tmpdir, "water.xyz")
    with open(water_xyz, "w") as f:
        f.write("3\nWater, plain xyz\nO 0.0 0.0 0.0\nH 0.757 0.586 0.0\nH -0.757 0.586 0.0\n")

    with pytest.raises(MissingLatticeError):
        xyz_to_cif(water_xyz, os.path.join(tmpdir, "water.cif"))


def test_plain_xyz_with_explicit_cell_succeeds(tmpdir):
    """The same underspecified case, resolved correctly once real
    lattice parameters are explicitly supplied."""
    water_xyz = os.path.join(tmpdir, "water.xyz")
    with open(water_xyz, "w") as f:
        f.write("3\nWater, plain xyz\nO 0.0 0.0 0.0\nH 0.757 0.586 0.0\nH -0.757 0.586 0.0\n")

    cif_path = os.path.join(tmpdir, "water.cif")
    xyz_to_cif(water_xyz, cif_path, cell=(10.0, 10.0, 10.0, 90.0, 90.0, 90.0))

    result = read(cif_path)
    assert all(result.pbc)


def test_extended_xyz_needs_no_explicit_cell(tmpdir):
    """An xyz file that already carries real lattice info (produced by
    cif_to_xyz itself) should convert directly - the explicit `cell`
    argument is only needed for genuinely plain xyz files."""
    atoms = bulk("Cu", crystalstructure="fcc", a=3.61)
    cif1 = os.path.join(tmpdir, "copper.cif")
    xyz1 = os.path.join(tmpdir, "copper.xyz")
    cif2 = os.path.join(tmpdir, "no_cell_needed.cif")

    write(cif1, atoms)
    cif_to_xyz(cif1, xyz1)
    xyz_to_cif(xyz1, cif2)  # no cell= argument at all

    result = read(cif2)
    assert all(result.pbc)
