from __future__ import annotations

import argparse
import glob
import os
import urllib.request
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def auditar_fastas_via_api(diretorio_npz: str | Path = "rcsb_processed_targets/structures", limite: int = 20) -> None:
    diretorio_npz = _resolve(diretorio_npz)
    arquivos_npz = glob.glob(os.path.join(diretorio_npz, "*.npz"))

    if not arquivos_npz:
        print(f"Nenhum arquivo .npz encontrado em {diretorio_npz}")
        return

    print("Analisando proteínas baixando o FASTA direto do PDB...\n")
    print(f"{'PDB ID':<8} | {'Total Cadeias':<14} | {'Achou MHC?':<12} | {'Achou Peptídeo?':<15}")
    print("=" * 55)

    proteinas_perfeitas = 0
    erros_download = 0

    for caminho in arquivos_npz[:limite]:
        pdb_id = os.path.basename(caminho)[:4].upper()
        url = f"https://www.rcsb.org/fasta/entry/{pdb_id}/display"

        try:
            resposta = urllib.request.urlopen(url)
            conteudo = resposta.read().decode("utf-8").splitlines()

            total_cadeias = 0
            achou_mhc = False
            achou_peptideo = False

            for linha in conteudo:
                if linha.startswith(">"):
                    total_cadeias += 1
                    linha_lower = linha.lower()
                    if "mhc" in linha_lower or "histocompatibility" in linha_lower:
                        achou_mhc = True
                    if "peptide" in linha_lower:
                        achou_peptideo = True

            status_mhc = "✅ Sim" if achou_mhc else "❌ Não"
            status_pep = "✅ Sim" if achou_peptideo else "❌ Não"
            if achou_mhc and achou_peptideo:
                proteinas_perfeitas += 1
            print(f"{pdb_id:<8} | {total_cadeias:<14} | {status_mhc:<12} | {status_pep:<15}")
        except Exception:
            print(f"{pdb_id:<8} | {'ERRO DOWNLOAD':<14} | {'-':<12} | {'-':<15}")
            erros_download += 1

    print("=" * 55)
    total_analisado = min(len(arquivos_npz), limite) - erros_download
    if total_analisado > 0:
        taxa_sucesso = proteinas_perfeitas / total_analisado * 100
        print(f"Resultado Final: {taxa_sucesso:.1f}% das proteínas analisadas têm marcações perfeitas no texto.")
    else:
        print("Nenhuma proteína pôde ser analisada com sucesso.")


def auditar_cabecalhos_fasta(diretorio_fastas: str | Path = "rcsb_processed_targets/fasta") -> None:
    diretorio_fastas = _resolve(diretorio_fastas)
    arquivos_fasta = glob.glob(os.path.join(diretorio_fastas, "*.fasta"))

    if not arquivos_fasta:
        print(f"Nenhum arquivo .fasta encontrado em {diretorio_fastas}")
        return

    print(f"Analisando {len(arquivos_fasta)} arquivos FASTA...\n")
    print(f"{'PDB ID':<8} | {'Total Cadeias':<14} | {'Achou MHC?':<12} | {'Achou Peptídeo?':<15}")
    print("=" * 55)

    proteinas_perfeitas = 0
    for caminho in arquivos_fasta:
        pdb_id = os.path.basename(caminho).replace(".fasta", "").upper()
        total_cadeias = 0
        achou_mhc = False
        achou_peptideo = False

        with open(caminho, encoding="utf-8") as handle:
            for linha in handle:
                if linha.startswith(">"):
                    total_cadeias += 1
                    linha_lower = linha.lower()
                    if "mhc" in linha_lower or "histocompatibility" in linha_lower:
                        achou_mhc = True
                    if "peptide" in linha_lower:
                        achou_peptideo = True

        status_mhc = "✅ Sim" if achou_mhc else "❌ Não"
        status_pep = "✅ Sim" if achou_peptideo else "❌ Não"
        if achou_mhc and achou_peptideo:
            proteinas_perfeitas += 1
        print(f"{pdb_id:<8} | {total_cadeias:<14} | {status_mhc:<12} | {status_pep:<15}")

    print("=" * 55)
    taxa_sucesso = proteinas_perfeitas / len(arquivos_fasta) * 100
    print(f"Resultado Final: {taxa_sucesso:.1f}% das proteínas têm as marcações perfeitas no texto.")


def inspecionar_npz(caminho_arquivo: str | Path = "rcsb_processed_targets/structures/1a1m.npz") -> None:
    caminho_arquivo = _resolve(caminho_arquivo)
    try:
        dados = np.load(caminho_arquivo)
        print(f"\n{'='*50}")
        print(f"🔬 RAIO-X DO ARQUIVO: {caminho_arquivo}")
        print(f"{'='*50}")
        chaves = dados.files
        print(f"Total de tensores encontrados: {len(chaves)}\n")
        for chave in chaves:
            matriz = dados[chave]
            print(f" 📦 Chave: {chave.ljust(15)} | 📐 Dimensão: {str(matriz.shape).ljust(15)} | 🧮 Tipo: {matriz.dtype}")
        print(f"{'='*50}\n")
    except FileNotFoundError:
        print(f"❌ Erro: Arquivo {caminho_arquivo} não encontrado.")


def gerar_txt_do_npz(
    caminho_npz: str | Path,
    caminho_txt: str | Path,
) -> None:
    caminho_npz = _resolve(caminho_npz)
    caminho_txt = _resolve(caminho_txt)

    print(f"Lendo o arquivo binário: {caminho_npz}")
    dados = np.load(caminho_npz, allow_pickle=True)

    caminho_txt.parent.mkdir(parents=True, exist_ok=True)
    with caminho_txt.open("w", encoding="utf-8") as handle:
        handle.write(f"=== ESTRUTURA DO ARQUIVO NPZ: {caminho_npz} ===\n\n")
        for chave in dados.files:
            matriz = dados[chave]
            handle.write(f"-> NOME DO TENSOR: {chave}\n")
            handle.write(f"   Dimensões (Shape): {matriz.shape}\n")
            handle.write(f"   Tipo de dado: {matriz.dtype}\n")
            amostra = matriz.flatten()[:5]
            handle.write(f"   Amostra do conteúdo: {amostra}...\n")
            handle.write("-" * 50 + "\n")

    print(f"Relatório estrutural salvo em: {caminho_txt}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ferramentas de inspeção para FASTA e NPZ.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fasta_api = subparsers.add_parser("fasta-api", help="Audita FASTA direto da API do PDB.")
    fasta_api.add_argument("--dir", default="rcsb_processed_targets/structures")
    fasta_api.add_argument("--limit", type=int, default=20)

    fasta_headers = subparsers.add_parser("fasta-headers", help="Audita cabeçalhos FASTA locais.")
    fasta_headers.add_argument("--dir", default="rcsb_processed_targets/fasta")

    npz_parser = subparsers.add_parser("npz", help="Mostra o raio-x de um arquivo NPZ.")
    npz_parser.add_argument("path", nargs="?", default="rcsb_processed_targets/structures/1a1m.npz")

    npz_report = subparsers.add_parser("npz-report", help="Gera um relatório texto a partir de um NPZ.")
    npz_report.add_argument("npz_path")
    npz_report.add_argument("txt_path")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "fasta-api":
        auditar_fastas_via_api(args.dir, args.limit)
    elif args.command == "fasta-headers":
        auditar_cabecalhos_fasta(args.dir)
    elif args.command == "npz":
        inspecionar_npz(args.path)
    elif args.command == "npz-report":
        gerar_txt_do_npz(args.npz_path, args.txt_path)


if __name__ == "__main__":
    main()
