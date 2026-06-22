from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def auditar_dataset(
    csv_path: str | Path = "mhc_data/TCR3d_data.csv",
    manifest_path: str | Path = "rcsb_processed_targets/manifest.json",
    structures_dir: str | Path = "rcsb_processed_targets/structures",
) -> None:
    csv_path = _resolve(csv_path)
    manifest_path = _resolve(manifest_path)
    structures_dir = _resolve(structures_dir)

    print("Iniciando Auditoria de Arquivos Físicos no CMCAD...\n")

    try:
        df = pd.read_csv(csv_path)
        ids_csv = set(df["PDB ID"].str.lower().dropna())
        print(f"[*] Total de IDs únicas no nosso CSV: {len(ids_csv)}")

        print(f"[*] Lendo o manifesto gigante ({manifest_path}). Isso pode levar alguns segundos...")
        with manifest_path.open(encoding="utf-8") as handle:
            manifest_data = json.load(handle)

        ids_manifesto = {item.get("id", "").lower() for item in manifest_data}
        print(f"[*] Total de proteínas mapeadas no manifesto oficial do Boltz: {len(ids_manifesto)}")

        proteinas_sobreviventes: list[str] = []
        motivos_descarte = {"nao_no_manifesto": [], "sem_arquivo_npz": []}

        print("\n[*] Cruzando os dados e checando os arquivos físicos .npz...")
        for pdb_id in ids_csv:
            if pdb_id in ids_manifesto:
                caminho_npz = os.path.join(structures_dir, f"{pdb_id}.npz")
                if os.path.exists(caminho_npz):
                    proteinas_sobreviventes.append(pdb_id)
                else:
                    motivos_descarte["sem_arquivo_npz"].append(pdb_id)
            else:
                motivos_descarte["nao_no_manifesto"].append(pdb_id)

        print("\n================ RELATÓRIO FINAL ================")
        print(f"TOTAL ALMEJADO (CSV): {len(ids_csv)}")
        print(f"TOTAL PRONTO PARA TREINO (Sobreviventes): {len(proteinas_sobreviventes)}")
        print(f"TOTAL DESCARTADO: {len(motivos_descarte['nao_no_manifesto']) + len(motivos_descarte['sem_arquivo_npz'])}")
        print("\n--- POR QUE FORAM DESCARTADAS? ---")
        print(f"1. Não existem no manifesto do Boltz: {len(motivos_descarte['nao_no_manifesto'])} proteínas")
        print(f"2. Estão no manifesto, mas o arquivo .npz sumiu/corrompeu: {len(motivos_descarte['sem_arquivo_npz'])} proteínas")
        print("=================================================\n")
    except Exception as exc:
        print(f"ERRO durante a execução: {exc}")


def auditar_mascaras(pdb_id: str = "1a1m") -> None:
    caminho_velho = REPO_ROOT / f"rcsb_processed_targets/structures/{pdb_id}.npz"
    caminho_novo = REPO_ROOT / f"mhc_data/dataset_limpo/structures/{pdb_id}.npz"

    if not caminho_velho.exists() or not caminho_novo.exists():
        print(f"Arquivos do PDB {pdb_id} não encontrados para comparação.")
        return

    velho = dict(np.load(caminho_velho))
    novo = dict(np.load(caminho_novo))

    mascara_velha = velho["mask"]
    mascara_nova = novo["mask"]

    print(f"\n{'='*50}")
    print(f"📊 RELATÓRIO DE AUDITORIA: PDB {pdb_id.upper()}")
    print(f"{'='*50}")

    total_cadeias = len(mascara_velha)
    print(f"Total de cadeias no cristal original: {total_cadeias}\n")

    for indice in range(total_cadeias):
        status_velho = "ATIVO (True)" if mascara_velha[indice] else "INATIVO (False)"
        status_novo = "MANTIDO (True)" if mascara_nova[indice] else "DESCARTADO (False)"
        cor_velho = "\033[92m" if mascara_velha[indice] else "\033[91m"
        cor_novo = "\033[92m" if mascara_nova[indice] else "\033[91m"
        reset = "\033[0m"
        mudou = "🔄 ALTERADO" if mascara_velha[indice] != mascara_nova[indice] else "✅ INTACTO"

        print(f"Cadeia {indice}:")
        print(f"  Antes:  {cor_velho}{status_velho}{reset}")
        print(f"  Depois: {cor_novo}{status_novo}{reset} -> {mudou}")
        print("-" * 30)


def auditar_lote_tabela(
    diretorio_novo: str | Path = "mhc_data/dataset_limpo/structures",
    diretorio_velho: str | Path = "rcsb_processed_targets/structures",
    arquivo_saida: str | Path = "mhc_data/relatorio_auditoria_tabela.txt",
) -> None:
    diretorio_novo = _resolve(diretorio_novo)
    diretorio_velho = _resolve(diretorio_velho)
    arquivo_saida = _resolve(arquivo_saida)

    arquivos_limpos = sorted([f for f in os.listdir(diretorio_novo) if f.endswith(".npz")])
    print(f"Gerando relatório tabelado para {len(arquivos_limpos)} proteínas...")

    with arquivo_saida.open("w", encoding="utf-8") as handle:
        handle.write("=" * 85 + "\n")
        handle.write(f"{'PDB ID':<8} | {'Total Cadeias':<15} | {'Índices Mantidos (MHC + Pep)':<30} | {'Status'}\n")
        handle.write("=" * 85 + "\n")

        for arquivo in arquivos_limpos:
            pdb_id = arquivo.replace(".npz", "").upper()
            caminho_novo = diretorio_novo / arquivo
            caminho_velho = diretorio_velho / arquivo

            try:
                novo = dict(np.load(caminho_novo))
                _ = caminho_velho
                mascara_nova = novo["mask"]
                total_cadeias = len(mascara_nova)
                indices_mantidos = [indice for indice, valor in enumerate(mascara_nova) if valor]
                handle.write(f"{pdb_id:<8} | {total_cadeias:<15} | {str(indices_mantidos):<30} | OK\n")
            except Exception:
                handle.write(f"{pdb_id:<8} | {'ERRO':<15} | {'-':<30} | FALHA DE LEITURA\n")

        handle.write("=" * 85 + "\n")
        handle.write(f"Total Auditado: {len(arquivos_limpos)} arquivos.\n")

    print(f"Auditoria gerada em: {arquivo_saida}")


def investigar_descartes_detalhado(
    arquivo_originais: str | Path = "mhc_data/mhc_split.txt",
    dir_novo: str | Path = "mhc_data/dataset_limpo/structures",
    manifesto_path: str | Path = "rcsb_processed_targets/manifest.json",
    arquivo_saida: str | Path = "mhc_data/relatorio_descartes_detalhado.txt",
) -> None:
    arquivo_originais = _resolve(arquivo_originais)
    dir_novo = _resolve(dir_novo)
    manifesto_path = _resolve(manifesto_path)
    arquivo_saida = _resolve(arquivo_saida)

    try:
        with arquivo_originais.open(encoding="utf-8") as handle:
            originais = {linha.strip().upper() for linha in handle if linha.strip()}
    except FileNotFoundError:
        print(f"Erro: O arquivo {arquivo_originais} não encontrado.")
        return

    novos = {f.replace(".npz", "").upper() for f in os.listdir(dir_novo) if f.endswith(".npz")}
    descartados = sorted(originais - novos)

    if not manifesto_path.exists():
        print("Manifesto não encontrado.")
        return

    with manifesto_path.open(encoding="utf-8") as handle:
        manifesto_lista = json.load(handle)
    manifesto_dict = {item.get("id", "").upper(): item for item in manifesto_lista}

    with arquivo_saida.open("w", encoding="utf-8") as out:
        header = f"{'PDB ID':<8} | {'Cadeias':<8} | {'Maior':<8} | {'Menor':<8} | {'Diagnóstico'}"
        out.write("=" * 75 + "\n")
        out.write(f"🕵️ RELATÓRIO DETALHADO DE DESCARTE ({len(descartados)} proteínas)\n")
        out.write("=" * 75 + "\n")
        out.write(header + "\n")
        out.write("-" * 75 + "\n")

        for pdb_id in descartados:
            proteina_info = manifesto_dict.get(pdb_id)
            if proteina_info:
                cadeias = proteina_info.get("chains", [])
                num_cadeias = len(cadeias)
                tamanhos = [cadeia.get("num_residues", 0) for cadeia in cadeias]
                maior = max(tamanhos) if tamanhos else 0
                menor = min(tamanhos) if tamanhos else 0
                motivos = []
                if maior <= 200:
                    motivos.append("MHC Incompleto")
                if menor >= 25:
                    motivos.append("Pep. Ausente")
                diag = " + ".join(motivos) if motivos else "Outro"
                out.write(f"{pdb_id:<8} | {num_cadeias:<8} | {maior:<8} | {menor:<8} | ❌ {diag}\n")
            else:
                out.write(f"{pdb_id:<8} | {'?':<8} | {'-':<8} | {'-':<8} | ⚠️ Não consta no manifesto\n")

        out.write("=" * 75 + "\n")

    print(f"Relatório detalhado gerado em: {arquivo_saida}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ferramentas de auditoria para o dataset MHC.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    dataset = subparsers.add_parser("dataset", help="Audita CSV, manifest e arquivos físicos.")
    dataset.add_argument("--csv", default="mhc_data/TCR3d_data.csv")
    dataset.add_argument("--manifest", default="rcsb_processed_targets/manifest.json")
    dataset.add_argument("--structures", default="rcsb_processed_targets/structures")

    mask = subparsers.add_parser("mask", help="Compara a máscara antes e depois da limpeza.")
    mask.add_argument("pdb_id", nargs="?", default="1a1m")

    batch = subparsers.add_parser("batch-table", help="Gera relatório tabulado da limpeza em lote.")
    batch.add_argument("--clean-dir", default="mhc_data/dataset_limpo/structures")
    batch.add_argument("--old-dir", default="rcsb_processed_targets/structures")
    batch.add_argument("--output", default="mhc_data/relatorio_auditoria_tabela.txt")

    discard = subparsers.add_parser("discard-detail", help="Gera o relatório detalhado de descartes.")
    discard.add_argument("--origins", default="mhc_data/mhc_split.txt")
    discard.add_argument("--clean-dir", default="mhc_data/dataset_limpo/structures")
    discard.add_argument("--manifest", default="rcsb_processed_targets/manifest.json")
    discard.add_argument("--output", default="mhc_data/relatorio_descartes_detalhado.txt")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "dataset":
        auditar_dataset(args.csv, args.manifest, args.structures)
    elif args.command == "mask":
        auditar_mascaras(args.pdb_id)
    elif args.command == "batch-table":
        auditar_lote_tabela(args.clean_dir, args.old_dir, args.output)
    elif args.command == "discard-detail":
        investigar_descartes_detalhado(args.origins, args.clean_dir, args.manifest, args.output)


if __name__ == "__main__":
    main()
