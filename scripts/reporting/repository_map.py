from __future__ import annotations

import argparse
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = Path(__file__).resolve().parent / "outputs"

DEFAULT_VALID_EXTENSIONS = {".py", ".yaml", ".yml", ".md", ".sh", ".json"}
DEFAULT_TREE_EXTENSIONS = {".py", ".yaml", ".yml", ".md", ".sh"}


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def write_repository_map(
    output_file: str | Path,
    *,
    root_dir: str | Path = REPO_ROOT,
    valid_extensions: set[str] = DEFAULT_VALID_EXTENSIONS,
    ignore_dirs: set[str] | None = None,
    include_contents: bool = True,
    file_limit_per_dir: int | None = None,
    title: str = "=== MAPA DO REPOSITÓRIO NEMPA BOLTZ ===",
) -> None:
    root_dir = _resolve(root_dir)
    output_file = _resolve(output_file)
    ignore_dirs = ignore_dirs or {".git", "__pycache__", "wandb", ".ipynb_checkpoints"}
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w", encoding="utf-8") as out:
        out.write(f"{title}\n\n")
        out.write("--- ESTRUTURA DE PASTAS ---\n")
        for root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            level = root.replace(str(root_dir), "").count(os.sep)
            indent = " " * 4 * level
            out.write(f"{indent}{os.path.basename(root)}/\n")

            subindent = " " * 4 * (level + 1)
            visible_files = sorted(files)
            if file_limit_per_dir is not None:
                visible_files = visible_files[:file_limit_per_dir]
            for file_name in visible_files:
                out.write(f"{subindent}{file_name}\n")
            if file_limit_per_dir is not None and len(files) > file_limit_per_dir:
                out.write(f"{subindent}... [mais {len(files) - file_limit_per_dir} arquivos ocultos nesta pasta]\n")

        if include_contents:
            out.write("\n=========================================\n\n")
            out.write("--- CONTEÚDO DOS ARQUIVOS DE CÓDIGO E DOCS ---\n")
            for root, dirs, files in os.walk(root_dir):
                dirs[:] = [d for d in dirs if d not in ignore_dirs]
                for file_name in files:
                    ext = os.path.splitext(file_name)[1].lower()
                    if ext in valid_extensions:
                        file_path = os.path.join(root, file_name)
                        out.write(f"\n\n>>> ARQUIVO: {file_path}\n")
                        out.write("-" * 40 + "\n")
                        try:
                            with open(file_path, encoding="utf-8") as handle:
                                out.write(handle.read())
                        except Exception as exc:
                            out.write(f"[Erro ao ler: {exc}]\n")

    print(f"Mapa gerado com sucesso em: {output_file}")


def gerar_mapa_definitivo() -> None:
    write_repository_map(
        REPORTS_DIR / "mapa_repositorio_definitivo.txt",
        ignore_dirs={".git", "__pycache__", "wandb", ".ipynb_checkpoints"},
        valid_extensions=DEFAULT_VALID_EXTENSIONS,
        include_contents=True,
        file_limit_per_dir=15,
        title="=== MAPA DO REPOSITÓRIO NEMPA BOLTZ (RESUMO) ===",
    )


def gerar_mapa_limpo() -> None:
    write_repository_map(
        REPORTS_DIR / "mapa_limpo.txt",
        ignore_dirs={
            ".git",
            "__pycache__",
            "wandb",
            ".ipynb_checkpoints",
            "rcsb_processed_targets",
            "rcsb_processed_msa",
            "mhc_data",
            "venv",
            ".venv",
            "cif_files",
        },
        valid_extensions=DEFAULT_TREE_EXTENSIONS,
        include_contents=False,
        title="=== ARQUITETURA DO CÓDIGO NEMPA BOLTZ ===",
    )


def gerar_mapa_nempa() -> None:
    write_repository_map(
        REPORTS_DIR / "mapa_repositorio_nempa.txt",
        ignore_dirs={".git", "__pycache__", "wandb", ".ipynb_checkpoints", "mhc_data"},
        valid_extensions=DEFAULT_TREE_EXTENSIONS,
        include_contents=False,
        title="=== MAPA DO REPOSITÓRIO NEMPA BOLTZ ===",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gera mapas e árvores do repositório.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("definitive", help="Gera o mapa detalhado do repositório.")
    subparsers.add_parser("clean", help="Gera a versão limpa da árvore do projeto.")
    subparsers.add_parser("nempa", help="Gera o mapa do repositório NemPA.")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "definitive":
        gerar_mapa_definitivo()
    elif args.command == "clean":
        gerar_mapa_limpo()
    elif args.command == "nempa":
        gerar_mapa_nempa()


if __name__ == "__main__":
    main()
