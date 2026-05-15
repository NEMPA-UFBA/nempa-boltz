import numpy as np

def gerar_txt_do_npz(caminho_npz, caminho_txt):
    print(f"Lendo o arquivo binário: {caminho_npz}")
    dados = np.load(caminho_npz, allow_pickle=True)
    
    with open(caminho_txt, 'w') as f:
        f.write(f"=== ESTRUTURA DO ARQUIVO NPZ: {caminho_npz} ===\n\n")
        
        for chave in dados.files:
            matriz = dados[chave]
            
            # Escreve o nome da matriz, as dimensões e o tipo de dado
            f.write(f"-> NOME DO TENSOR: {chave}\n")
            f.write(f"   Dimensões (Shape): {matriz.shape}\n")
            f.write(f"   Tipo de dado: {matriz.dtype}\n")
            
            # Pega apenas os primeiros 5 elementos para amostra (evita arquivos de 1GB)
            amostra = matriz.flatten()[:5]
            f.write(f"   Amostra do conteúdo: {amostra}...\n")
            f.write("-" * 50 + "\n")
            
    print(f"✅ Relatório estrutural salvo em: {caminho_txt}")

# IMPORTANTE: Altere os caminhos abaixo para os arquivos reais que você quer testar
arquivo_alvo_npz = "rcsb_processed_targets/structures/1a1m.npz"
arquivo_saida_txt = "relatorio_estrutura_1A1M.txt"

gerar_txt_do_npz(arquivo_alvo_npz, arquivo_saida_txt)
