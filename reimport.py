import gzip, shutil, os
from ambigchem.local_database import create_database, count_records, lookup
from ambigchem.bulk_import import import_sdf

if not os.path.exists("CID-Synonym-filtered.txt") and os.path.exists("CID-Synonym-filtered.gz"):
    print("Decompressing synonym file...")
    with gzip.open("CID-Synonym-filtered.gz", "rb") as f_in:
        with open("CID-Synonym-filtered.txt", "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

create_database("compounds.db")
count = import_sdf(
    "Compound_000000001_000500000.sdf", "compounds.db",
    source="pubchem", synonym_path="CID-Synonym-filtered.txt",
)
print(f"Imported {count} records")
print("aspirin:", lookup("compounds.db", "aspirin"))