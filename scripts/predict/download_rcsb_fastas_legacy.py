#!/usr/bin/env python3

from pathlib import Path
import urllib.request
import urllib.error

INPUT_FILE = Path("/home/gpu/nempa-boltz/mhc_data/test_templated.txt")
OUTPUT_DIR = Path("/home/gpu/test_yamls")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

with INPUT_FILE.open("r") as f:
    pdb_ids = [line.strip().upper() for line in f if line.strip()]

print(f"Total de IDs: {len(pdb_ids)}")
print(f"Destino: {OUTPUT_DIR}")
print()

sucesso = 0
erros = 0

for i, pdb_id in enumerate(pdb_ids, start=1):

    url = f"https://www.rcsb.org/fasta/entry/{pdb_id}/download"
    output_file = OUTPUT_DIR / f"{pdb_id}.fasta"

    print(f"[{i}/{len(pdb_ids)}] {pdb_id} ... ", end="", flush=True)

    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            fasta = response.read()

        output_file.write_bytes(fasta)

        print("OK")
        sucesso += 1

    except (urllib.error.URLError,
            urllib.error.HTTPError,
            TimeoutError) as e:

        print(f"ERRO: {e}")
        erros += 1


print()
print("Download concluído.")
print(f"Sucesso: {sucesso}")
print(f"Erros:   {erros}")