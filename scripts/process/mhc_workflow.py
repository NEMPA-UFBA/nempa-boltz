from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import pandas as pd
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def generate_subsamples(
    source_dir: str | Path = "rcsb_processed_targets",
    msa_source: str | Path = "rcsb_processed_msa",
    target_dir: str | Path = "mhc_data/dataset_limpo",
    template_files: tuple[str, ...] = ("train_templated.json", "val_templated.json"),
) -> None:
    source_dir = _resolve(source_dir)
    msa_source = _resolve(msa_source)
    target_dir = _resolve(target_dir)
    manifest_path = source_dir / "manifest.json"

    (target_dir / "msa").mkdir(parents=True, exist_ok=True)
    (target_dir / "structures").mkdir(parents=True, exist_ok=True)

    with manifest_path.open(encoding="utf-8") as handle:
        master_manifest = {sample["id"].lower(): sample for sample in json.load(handle)}

    target_samples: list[dict] = []
    for template_file in template_files:
        with _resolve(template_file).open(encoding="utf-8") as handle:
            target_samples.extend(json.load(handle))

    new_manifest: list[dict] = []

    for sample in target_samples:
        pdb_id = sample["pdb_id"].lower()
        if pdb_id not in master_manifest:
            continue

        data = master_manifest[pdb_id]
        peptide_target = sample["peptide_chain"] + "1"
        protein_targets = [chain + "1" for chain in sample["protein_chains"]]

        valid_chain_ids: list[str | int] = []
        for chain in data["chains"]:
            is_target = chain["chain_name"] == peptide_target or chain["chain_name"] in protein_targets
            chain["valid"] = bool(is_target)
            if is_target:
                valid_chain_ids.append(chain["chain_id"])
                if chain["msa_id"] != -1:
                    msa_file = f"{chain['msa_id']}.npz"
                    if (msa_source / msa_file).exists():
                        shutil.copy(msa_source / msa_file, target_dir / "msa" / msa_file)

        for interface in data["interfaces"]:
            interface["valid"] = interface["chain_1"] in valid_chain_ids and interface["chain_2"] in valid_chain_ids

        struct_file = f"{pdb_id}.npz"
        if (source_dir / "structures" / struct_file).exists():
            shutil.copy(source_dir / "structures" / struct_file, target_dir / "structures" / struct_file)

        new_manifest.append(data)

    with (target_dir / "manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(new_manifest, handle, indent=4)

    print(f"Processamento concluído. Dataset limpo em: {target_dir}")


def filter_mhc(
    csv_path: str | Path = "mhc_data/TCR3d_data.csv",
    manifest_path: str | Path = "rcsb_processed_targets/manifest.json",
    split_txt_path: str | Path = "mhc_data/mhc_split.txt",
    filtered_manifest_path: str | Path = "mhc_data/mhc_manifest_filtered.json",
) -> None:
    csv_path = _resolve(csv_path)
    manifest_path = _resolve(manifest_path)
    split_txt_path = _resolve(split_txt_path)
    filtered_manifest_path = _resolve(filtered_manifest_path)

    df = pd.read_csv(csv_path)
    pdb_ids = df["PDB ID"].dropna().unique().tolist()
    pdb_ids_lower = [pdb.lower() for pdb in pdb_ids]

    with split_txt_path.open("w", encoding="utf-8") as handle:
        for pdb in pdb_ids_lower:
            handle.write(f"{pdb}\n")

    try:
        with manifest_path.open(encoding="utf-8") as handle:
            manifest_data = json.load(handle)
        filtered_manifest = [item for item in manifest_data if item.get("id", "").lower() in pdb_ids_lower]
        with filtered_manifest_path.open("w", encoding="utf-8") as handle:
            json.dump(filtered_manifest, handle, indent=4)
        print(f"Filtered JSON manifest created at: {filtered_manifest_path}")
    except FileNotFoundError:
        print(f"Warning: File {manifest_path} not found.")

    print(f"Split file created at: {split_txt_path}")
    print(f"Found {len(pdb_ids_lower)} unique PDB IDs in the CSV.")


def generate_validation_split(
    csv_path: str | Path = "mhc_data/TCR3d_data.csv",
    output_path: str | Path = "scripts/train/assets/validation_ids.txt",
) -> None:
    csv_path = _resolve(csv_path)
    output_path = _resolve(output_path)

    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"Erro: Arquivo {csv_path} não encontrado.")
        return

    df["Release date"] = pd.to_datetime(df["Release date"])
    start_date = "2021-10-01"
    end_date = "2022-12-31"
    mask = (df["Release date"] >= start_date) & (df["Release date"] <= end_date)
    filtered_df = df.loc[mask]
    val_ids = filtered_df["PDB ID"].dropna().str.lower().unique().tolist()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for pdb_id in val_ids:
            handle.write(f"{pdb_id}\n")

    print(f"Sucesso! Arquivo gerado em: {output_path}")
    print(f"Total de proteínas na validação: {len(val_ids)}")


def clean_chains(
    manifest_path: str | Path = "mhc_data/mhc_manifest_filtered.json",
    npz_source_dir: str | Path = "rcsb_processed_targets/structures",
    target_dir: str | Path = "mhc_data/dataset_limpo",
) -> None:
    manifest_path = _resolve(manifest_path)
    npz_source_dir = _resolve(npz_source_dir)
    target_dir = _resolve(target_dir)

    (target_dir / "structures").mkdir(parents=True, exist_ok=True)

    with manifest_path.open(encoding="utf-8") as handle:
        data = json.load(handle)

    new_manifest: list[dict] = []
    print("Iniciando a cirurgia nos arquivos...")

    for sample in data:
        pdb_id = sample["id"]
        chains = sample["chains"]
        if len(chains) < 2:
            continue

        chains_sorted_by_size = sorted(chains, key=lambda item: item["num_residues"], reverse=True)
        mhc_chain = chains_sorted_by_size[0]
        peptide_chain = chains_sorted_by_size[-1]

        if mhc_chain["num_residues"] < 200 or peptide_chain["num_residues"] > 25:
            print(
                f"[{pdb_id}] Tamanhos anormais (Maior: {mhc_chain['num_residues']}, "
                f"Menor: {peptide_chain['num_residues']}). Pulando..."
            )
            continue

        valid_chain_ids = [mhc_chain["chain_id"], peptide_chain["chain_id"]]

        for chain in sample["chains"]:
            chain["valid"] = chain["chain_id"] in valid_chain_ids

        for interface in sample["interfaces"]:
            interface["valid"] = interface["chain_1"] in valid_chain_ids and interface["chain_2"] in valid_chain_ids

        new_manifest.append(sample)

        npz_path = npz_source_dir / f"{pdb_id}.npz"
        if npz_path.exists():
            npz_data = dict(np.load(npz_path))
            for index in range(len(npz_data["mask"])):
                npz_data["mask"][index] = index in valid_chain_ids
            np.savez(target_dir / "structures" / f"{pdb_id}.npz", **npz_data)

    with (target_dir / "manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(new_manifest, handle, indent=2)

    print(f"Limpeza concluída! Das {len(data)} proteínas, {len(new_manifest)} foram limpas e salvas em {target_dir}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ferramentas de preparação de MHC.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("subsamples", help="Gera o dataset limpo a partir dos templates.")
    subparsers.add_parser("filter-mhc", help="Filtra o manifest para IDs do CSV.")
    subparsers.add_parser("validation", help="Gera a lista de validação.")
    subparsers.add_parser("clean-chains", help="Mantém apenas as cadeias MHC e peptídeo.")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "subsamples":
        generate_subsamples()
    elif args.command == "filter-mhc":
        filter_mhc()
    elif args.command == "validation":
        generate_validation_split()
    elif args.command == "clean-chains":
        clean_chains()


if __name__ == "__main__":
    main()
