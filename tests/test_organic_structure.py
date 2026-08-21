"""
test_organic_structure.py

Real pytest coverage for generate_3d_structure()/save_3d_structure(),
including a genuine cross-module integration test: a real, generated
molecule correctly triggers structure_convert.py's MissingLatticeError,
since a real molecule genuinely has no periodicity - proving the two
modules agree on this, not just each module's own isolated tests.
"""

import os
import tempfile
import re
import pytest
from ambigchem.organic import parse_organic_name
from ambigchem.organic_structure import generate_3d_structure, save_3d_structure
from ambigchem.structure_convert import xyz_to_cif, MissingLatticeError


@pytest.fixture
def tmpdir():
    with tempfile.TemporaryDirectory() as d:
        yield d


def _atom_count_from_formula(formula: str) -> int:
    atom_counts = re.findall(r"([A-Z][a-z]?)(\d*)", formula)
    return sum(int(count) if count else 1 for symbol, count in atom_counts if symbol)


def test_generated_structure_matches_organic_py_formula():
    """The core real cross-check: the atom count in a genuinely
    generated 3D structure must match the formula organic.py already
    independently confirmed via OPSIN - two different real code paths
    (name-based formula lookup vs. RDKit 3D embedding) agreeing."""
    for name in ["ethanol", "methane", "benzene"]:
        formula_result = parse_organic_name(name)
        structure_result = generate_3d_structure(name)
        assert structure_result.success
        assert structure_result.num_atoms == _atom_count_from_formula(formula_result.formula)


def test_direct_smiles_input_also_works():
    """Confirms the is_smiles=True path, not just the name-resolution path."""
    result = generate_3d_structure("CCO", is_smiles=True)  # ethanol's SMILES
    assert result.success
    assert result.num_atoms == 9


def test_invalid_name_fails_cleanly():
    result = generate_3d_structure("not a real chemical name xyz123")
    assert result.success is False
    assert result.error is not None


def test_save_3d_structure_writes_a_real_file(tmpdir):
    xyz_path = os.path.join(tmpdir, "ethanol.xyz")
    result = save_3d_structure("ethanol", xyz_path)
    assert result.success
    assert os.path.exists(xyz_path)
    with open(xyz_path) as f:
        content = f.read()
    assert content.startswith("9\n")  # real xyz format: first line is atom count


def test_real_cross_module_integration_with_structure_convert(tmpdir):
    """A genuine, real molecule (generated here, not hand-written) has
    no periodicity - confirms structure_convert.py's honest
    MissingLatticeError fires correctly on a REAL generated structure,
    not just the hand-written test fixture in its own test file."""
    xyz_path = os.path.join(tmpdir, "generated_ethanol.xyz")
    save_3d_structure("ethanol", xyz_path)

    with pytest.raises(MissingLatticeError):
        xyz_to_cif(xyz_path, os.path.join(tmpdir, "should_not_be_created.cif"))
