import os

# Defina a pasta raiz do seu projeto Boltz no CMCAD
root_dir = "/home/gpu/nempa-boltz" # <-- AJUSTE ISSO SE NECESSÁRIO
output_file = "mapa_repositorio_nempa.txt"

# Extensões que queremos ler o conteúdo (Código e Configurações)
valid_extensions = {".py", ".yaml", ".yml", ".sh", ".md"}
# Extensões que queremos ignorar completamente (Dados pesados e arquivos de sistema)
ignore_dirs = {".git", "__pycache__", "wandb", ".ipynb_checkpoints", "mhc_data"}

with open(output_file, "w", encoding="utf-8") as out:
    out.write("=== MAPA DO REPOSITÓRIO NEMPA BOLTZ ===\n\n")
    
    # 1. Primeiro desenhamos a Árvore de Diretórios
    out.write("--- ESTRUTURA DE PASTAS ---\n")
    for root, dirs, files in os.walk(root_dir):
        # Removemos diretórios ignorados para não entrar neles
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        
        level = root.replace(root_dir, '').count(os.sep)
        indent = ' ' * 4 * (level)
        out.write(f"{indent}{os.path.basename(root)}/\n")
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            out.write(f"{subindent}{f}\n")
            
    out.write("\n=========================================\n\n")
    
    # 2. Depois, copiamos o conteúdo dos arquivos de código
    out.write("--- CONTEÚDO DOS ARQUIVOS DE CÓDIGO ---\n")
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in valid_extensions:
                file_path = os.path.join(root, file)
                out.write(f"\n\n>>> ARQUIVO: {file_path}\n")
                out.write("-" * 40 + "\n")
 #               try:
 #                   with open(file_path, "r", encoding="utf-8") as f:
 #                       out.write(f.read())
 #               except Exception as e:
 #                   out.write(f"[Erro ao ler arquivo: {e}]\n")

print(f"Mapa gerado com sucesso em: {output_file}")