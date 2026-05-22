import json
import os
import shutil
from pathlib import Path

# Configuração de Caminhos (Baseado no seu mapa_repositorio_definitivo.txt)
SOURCE_DIR = Path("rcsb_processed_targets")
MSA_SOURCE = Path("rcsb_processed_msa")
TARGET_DIR = Path("mhc_data/dataset_limpo")
MANIFEST_PATH = SOURCE_DIR / "manifest.json"

# Arquivos de template que o Ernest mencionou (precisam estar no mhc_data)
TEMPLATE_FILES = ["train_templated.json", "val_templated.json"]

def process_batch():
    # 1. Criar pastas de saída
    (TARGET_DIR / "msa").mkdir(parents=True, exist_ok=True)
    (TARGET_DIR / "structures").mkdir(parents=True, exist_ok=True)

    # 2. Carregar manifestos
    with open(MANIFEST_PATH) as f:
        master_manifest = {s['id']: s for s in json.load(f)}
    
    # Unificar listas de treino e val do template
    target_samples = []
    for t_file in TEMPLATE_FILES:
        with open(t_file) as f:
            target_samples.extend(json.load(f))

    new_manifest = []
    
    # 3. Loop de Processamento
    for sample in target_samples:
        pdb_id = sample['pdb_id'].lower()
        if pdb_id not in master_manifest:
            continue
            
        data = master_manifest[pdb_id]
        peptide_target = sample['peptide_chain'] + '1'
        protein_targets = [c + '1' for c in sample['protein_chains']]
        
        valid_chain_ids = []
        
        # Filtrar Cadeias
        for chain in data['chains']:
            is_target = chain['chain_name'] == peptide_target or chain['chain_name'] in protein_targets
            
            if is_target:
                chain['valid'] = True
                valid_chain_ids.append(chain['chain_id'])
                # Copiar MSA correspondente
                if chain['msa_id'] != -1:
                    msa_file = f"{chain['msa_id']}.npz"
                    if (MSA_SOURCE / msa_file).exists():
                        shutil.copy(MSA_SOURCE / msa_file, TARGET_DIR / "msa" / msa_file)
            else:
                chain['valid'] = False

        # Filtrar Interfaces (Manter apenas o contato Peptídeo-MHC)
        for interface in data['interfaces']:
            if interface['chain_1'] in valid_chain_ids and interface['chain_2'] in valid_chain_ids:
                interface['valid'] = True
            else:
                interface['valid'] = False
        
        # Copiar arquivo de estrutura .npz
        struct_file = f"{pdb_id}.npz"
        if (SOURCE_DIR / "structures" / struct_file).exists():
            shutil.copy(SOURCE_DIR / "structures" / struct_file, TARGET_DIR / "structures" / struct_file)
            
        new_manifest.append(data)

    # 4. Salvar novo manifesto final
    with open(TARGET_DIR / "manifest.json", "w") as f:
        json.dump(new_manifest, f, indent=4)
    
    print(f"✅ Processamento concluído. Dataset limpo em: {TARGET_DIR}")

if __name__ == "__main__":
    process_batch()
