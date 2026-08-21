from rdkit import Chem

with open("Compound_000000001_000500000.sdf", "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

print("Does '2244' appear anywhere in the raw file?", "2244" in content)
print("Does 'aspirin' (any case) appear anywhere in the raw file?", "aspirin" in content.lower())

supplier = Chem.SDMolSupplier("Compound_000000001_000500000.sdf")
found = False
for mol in supplier:
    if mol is None:
        continue
    if mol.HasProp("PUBCHEM_COMPOUND_CID") and mol.GetProp("PUBCHEM_COMPOUND_CID") == "2244":
        found = True
        print("\nFound CID 2244. Its real, available property tags are:")
        print(list(mol.GetPropNames()))
        break

if not found:
    print("\nCID 2244 was never successfully parsed as a molecule from this file")
    print("(either genuinely absent, or it hit one of those sanitization errors we saw)")