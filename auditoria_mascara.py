import numpy as np
import os

def auditar_mascaras(pdb_id):
    caminho_velho = f"rcsb_processed_targets/structures/{pdb_id}.npz"
    caminho_novo = f"mhc_data/dataset_limpo/structures/{pdb_id}.npz"
    
    if not os.path.exists(caminho_velho) or not os.path.exists(caminho_novo):
        print(f"Arquivos do PDB {pdb_id} não encontrados para comparação.")
        return

    velho = dict(np.load(caminho_velho))
    novo = dict(np.load(caminho_novo))
    
    mascara_velha = velho['mask']
    mascara_nova = novo['mask']
    
    print(f"\n{'='*50}")
    print(f"📊 RELATÓRIO DE AUDITORIA: PDB {pdb_id.upper()}")
    print(f"{'='*50}")
    
    total_cadeias = len(mascara_velha)
    print(f"Total de cadeias no cristal original: {total_cadeias}\n")
    
    for i in range(total_cadeias):
        status_velho = "ATIVO (True)" if mascara_velha[i] else "INATIVO (False)"
        status_novo = "MANTIDO (True)" if mascara_nova[i] else "DESCARTADO (False)"
        
        # Lógica de cores no terminal para ficar visual
        cor_velho = '\033[92m' if mascara_velha[i] else '\033[91m' # Verde ou Vermelho
        cor_novo = '\033[92m' if mascara_nova[i] else '\033[91m'
        reset = '\033[0m'
        
        mudou = "🔄 ALTERADO" if mascara_velha[i] != mascara_nova[i] else "✅ INTACTO"
        
        print(f"Cadeia {i}:")
        print(f"  Antes:  {cor_velho}{status_velho}{reset}")
        print(f"  Depois: {cor_novo}{status_novo}{reset} -> {mudou}")
        print("-" * 30)

# Altere o ID aqui para testar com outras proteínas
auditar_mascaras("1a1m")