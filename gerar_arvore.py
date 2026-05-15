import os

root_dir = "/home/gpu/nempa-boltz"
output_file = "mapa_limpo.txt"

# Ignoramos completamente as pastas de dados brutos e ambientes virtuais
ignore_dirs = {".git", "__pycache__", "wandb", ".ipynb_checkpoints", 
               "rcsb_processed_targets", "rcsb_processed_msa", "mhc_data", 
               "venv", ".venv", "cif_files"}

with open(output_file, "w", encoding="utf-8") as out:
    out.write("=== ARQUITETURA DO CÓDIGO NEMPA BOLTZ ===\n\n")
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        level = root.replace(root_dir, '').count(os.sep)
        indent = ' ' * 4 * level
        out.write(f"{indent}{os.path.basename(root)}/\n")
        
        subindent = ' ' * 4 * (level + 1)
        # Lista apenas arquivos relevantes de código/configuração, sem imprimir o conteúdo deles
        for f in sorted(files):
            if f.endswith(('.py', '.yaml', '.yml', '.json', '.sh', '.md')):
                out.write(f"{subindent}{f}\n")

print("Mapa limpo gerado com sucesso!")