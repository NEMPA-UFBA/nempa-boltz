import numpy as np
import os

def auditar_lote_tabela():
    diretorio_novo = "mhc_data/dataset_limpo/structures"
    diretorio_velho = "rcsb_processed_targets/structures"
    arquivo_saida = "mhc_data/relatorio_auditoria_tabela.txt"
    
    arquivos_limpos = [f for f in os.listdir(diretorio_novo) if f.endswith('.npz')]
    arquivos_limpos.sort() # Organiza em ordem alfabética
    
    print(f"Gerando relatório tabelado para {len(arquivos_limpos)} proteínas...")
    
    with open(arquivo_saida, 'w') as f:
        # Cabeçalho da Tabela
        f.write("=" * 85 + "\n")
        f.write(f"{'PDB ID':<8} | {'Total Cadeias':<15} | {'Índices Mantidos (MHC + Pep)':<30} | {'Status'}\n")
        f.write("=" * 85 + "\n")
        
        for arquivo in arquivos_limpos:
            pdb_id = arquivo.replace('.npz', '').upper()
            caminho_novo = os.path.join(diretorio_novo, arquivo)
            caminho_velho = os.path.join(diretorio_velho, arquivo)
            
            try:
                novo = dict(np.load(caminho_novo))
                mascara_nova = novo['mask']
                
                total_cadeias = len(mascara_nova)
                
                # Acha quais são os índices que ficaram como True
                indices_mantidos = [i for i, valor in enumerate(mascara_nova) if valor]
                
                # Formatação visual
                f.write(f"{pdb_id:<8} | {total_cadeias:<15} | {str(indices_mantidos):<30} | OK\n")
                
            except Exception as e:
                f.write(f"{pdb_id:<8} | {'ERRO':<15} | {'-':<30} | FALHA DE LEITURA\n")
                
        f.write("=" * 85 + "\n")
        f.write(f"Total Auditado: {len(arquivos_limpos)} arquivos.\n")
        
    print(f"✅ Auditoria impecável gerada em: {arquivo_saida}")

auditar_lote_tabela()