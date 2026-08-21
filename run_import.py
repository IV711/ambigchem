import gzip
import shutil
import os
from ambigchem.local_database import create_database, count_records
from ambigchem.bulk_import import import_sdf

gz_path = "Compound_000000001_000500000.sdf.gz"
sdf_path = "Compound_000000001_000500000.sdf"
db_path = "compounds.db"

if not os.path.exists(sdf_path):
    print("Decompressing (this file is large, may take a minute)...")
    with gzip.open(gz_path, "rb") as f_in:
        with open(sdf_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
    print("Decompressed.")

create_database(db_path)
print("Importing - this file has up to 500,000 real compound entries.")
print("This will genuinely take real time (likely several minutes) - not stuck, just large.")
count = import_sdf(sdf_path, db_path, source="pubchem")
print(f"Imported {count} name-formula records")
print(f"Total records in database: {count_records(db_path)}")