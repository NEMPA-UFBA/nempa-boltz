import pandas as pd
import json


mhc_csv_path = "mhc_data/TCR3d_data.csv"
df = pd.read_csv(mhc_csv_path)

pdb_ids = df["PDB ID"].dropna().unique().tolist()
pdb_ids_lower = [pdb.lower() for pdb in pdb_ids]


print(f"Found {len(pdb_ids_lower)} unique PDB IDs in the CSV.")


split_txt_path = "mhc_data/mhc_split.txt"
with open(split_txt_path, "w") as file_handler:
    for pdb in pdb_ids_lower:
        file_handler.write(f"{pdb}\n")
print(f"Split file created at: {split_txt_path}")


manifest_path = "rcsb_processed_targets/manifest.json"
filtered_manifest_path = "mhc_data/mhc_manifest_filtered.json"

try:
    with open(manifest_path, "r") as file_handler:
        manifest_data = json.load(file_handler)
    

    filtered_manifest = [item for item in manifest_data if item.get("id", "").lower() in pdb_ids_lower]
    
    with open(filtered_manifest_path, "w") as file_handler:
        json.dump(filtered_manifest, file_handler, indent=4)

    print(f"Filtered JSON manifest created at: {filtered_manifest_path}")

except FileNotFoundError:
    print(f"Warning: File {manifest_path} not found.")