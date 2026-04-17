import numpy as np
import sys

def inspecionar_npz(caminho_arquivo):
    try:
        # Carrega o arquivo binário
        dados = np.load(caminho_arquivo)
        
        print(f"\n{'='*50}")
        print(f"🔬 RAIO-X DO ARQUIVO: {caminho_arquivo}")
        print(f"{'='*50}")
        
        # Lista todas as chaves (as "gavetas" de matrizes)
        chaves = dados.files
        print(f"Total de tensores encontrados: {len(chaves)}\n")
        
        for chave in chaves:
            matriz = dados[chave]
            formato = matriz.shape
            tipo = matriz.dtype
            
            # Formatação elegante para o terminal
            print(f" 📦 Chave: {chave.ljust(15)} | 📐 Dimensão: {str(formato).ljust(15)} | 🧮 Tipo: {tipo}")
            
        print(f"{'='*50}\n")
        
    except FileNotFoundError:
        print(f"❌ Erro: Arquivo {caminho_arquivo} não encontrado.")

# Se você rodar com um arquivo específico no terminal, ele lê. Se não, usa o 1a1m padrão.
arquivo_alvo = sys.argv[1] if len(sys.argv) > 1 else "rcsb_processed_targets/structures/1a1m.npz"
inspecionar_npz(arquivo_alvo)