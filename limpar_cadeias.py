import json
import os
import shutil
import numpy as np

# Caminhos
manifest_path = "mhc_data/mhc_manifest_filtered.json"
npz_source_dir = "rcsb_processed_targets/structures"
target_dir = "mhc_data/dataset_limpo"

# Criar pastas seguras
os.makedirs(f"{target_dir}/structures", exist_ok=True)

with open(manifest_path, 'r') as f:
    data = json.load(f)

new_manifest = []

print("Iniciando a cirurgia nos arquivos...")

for sample in data:
    pdb_id = sample['id']
    chains = sample['chains']
    
    # Se tiver menos de 2 cadeias, ignora (não é MHC-Peptídeo)
    if len(chains) < 2:
        continue

    # Achar as cadeias pelo tamanho (num_residues)
    # Ordenamos as cadeias da maior para a menor
    chains_sorted_by_size = sorted(chains, key=lambda x: x['num_residues'], reverse=True)
    
    mhc_chain = chains_sorted_by_size[0] # A maior de todas
    peptide_chain = chains_sorted_by_size[-1] # A menor de todas
    
    # Validar se os tamanhos fazem sentido biológico (MHC grande, Peptídeo pequeno)
    if mhc_chain['num_residues'] < 200 or peptide_chain['num_residues'] > 25:
        print(f"[{pdb_id}] Tamanhos anormais (Maior: {mhc_chain['num_residues']}, Menor: {peptide_chain['num_residues']}). Pulando...")
        continue

    valid_chain_ids = [mhc_chain['chain_id'], peptide_chain['chain_id']]
    
    # Atualizar o manifesto para essa proteína
    for chain in sample['chains']:
        chain['valid'] = (chain['chain_id'] in valid_chain_ids)
        
    for interface in sample['interfaces']:
        interface['valid'] = (interface['chain_1'] in valid_chain_ids and interface['chain_2'] in valid_chain_ids)

    new_manifest.append(sample)

    # Cirurgia no arquivo .npz físico
    npz_path = f"{npz_source_dir}/{pdb_id}.npz"
    if os.path.exists(npz_path):
        # Carrega o arquivo binário
        npz_data = dict(np.load(npz_path))
        
        # Altera a máscara
        for i in range(len(npz_data['mask'])):
            npz_data['mask'][i] = (i in valid_chain_ids)
            
        # Salva o arquivo limpo na pasta nova
        np.savez(f"{target_dir}/structures/{pdb_id}.npz", **npz_data)

# Salva o novo manifesto
with open(f"{target_dir}/manifest.json", "w") as outfile:
    json.dump(new_manifest, outfile, indent=2)

print(f"Limpeza concluída! Das {len(data)} proteínas, {len(new_manifest)} foram limpas e salvas em {target_dir}")
