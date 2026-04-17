import os

root_dir = "/home/gpu/nempa-boltz" # <-- AJUSTE AQUI
output_file = "mapa_repositorio_definitivo.txt"

# Adicionei .md e .sh de volta. O JSON continua de fora para evitar o manifest.
valid_extensions = {".py", ".yaml", ".yml", ".md", ".sh"} 

# Removi a pasta mhc_data daqui para ela aparecer na árvore de pastas
ignore_dirs = {".git", "__pycache__", "wandb", ".ipynb_checkpoints"}

with open(output_file, "w", encoding="utf-8") as out:
    out.write("=== MAPA DO REPOSITÓRIO NEMPA BOLTZ (RESUMO) ===\n\n")
    
    out.write("--- ESTRUTURA DE PASTAS ---\n")
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        level = root.replace(root_dir, '').count(os.sep)
        indent = ' ' * 4 * (level)
        out.write(f"{indent}{os.path.basename(root)}/\n")
        
        subindent = ' ' * 4 * (level + 1)
        # Limita a exibição a 15 arquivos para não poluir
        for f in files[:15]:
            out.write(f"{subindent}{f}\n")
        if len(files) > 15:
            out.write(f"{subindent}... [mais {len(files) - 15} arquivos ocultos nesta pasta]\n")
            
    out.write("\n=========================================\n\n")
    
    out.write("--- CONTEÚDO DOS ARQUIVOS DE CÓDIGO E DOCS ---\n")
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in valid_extensions:
                file_path = os.path.join(root, file)
                out.write(f"\n\n>>> ARQUIVO: {file_path}\n")
                out.write("-" * 40 + "\n")
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        out.write(f.read())
                except Exception as e:
                    out.write(f"[Erro ao ler: {e}]\n")

print("Mapa definitivo gerado!")