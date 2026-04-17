import pandas as pd
import json
import os

# ==========================================
# CAMINHOS BASEADOS NO SEU MAPA DE REPOSITÓRIO
# ==========================================
csv_path = 'mhc_data/TCR3d_data.csv'
manifest_path = 'rcsb_processed_targets/manifest.json'
structures_dir = 'rcsb_processed_targets/structures/'

print("Iniciando Auditoria de Arquivos Físicos no CMCAD...\n")

try:
    # 1. Carregar os IDs do nosso CSV
    df = pd.read_csv(csv_path)
    # Pegamos os IDs e transformamos em letras minúsculas (pois no Boltz costuma ser minúsculo, ex: '1a1m')
    ids_csv = set(df['PDB ID'].str.lower().dropna())
    print(f"[*] Total de IDs únicas no nosso CSV: {len(ids_csv)}")

    # 2. Carregar o Manifesto Gigante do Boltz
    print(f"[*] Lendo o manifesto gigante ({manifest_path}). Isso pode levar alguns segundos...")
    with open(manifest_path, 'r') as f:
        manifest_data = json.load(f)
    
    # Extrair todos os IDs que o manifesto oficial conhece
    ids_manifesto = set([item.get('id', '').lower() for item in manifest_data])
    print(f"[*] Total de proteínas mapeadas no manifesto oficial do Boltz: {len(ids_manifesto)}")

    # 3. Cruzar os dados e verificar os arquivos .npz
    proteinas_sobreviventes = []
    motivos_descarte = {"nao_no_manifesto": [], "sem_arquivo_npz": []}

    print("\n[*] Cruzando os dados e checando os arquivos físicos .npz...")
    for pdb_id in ids_csv:
        if pdb_id in ids_manifesto:
            # Se tá no manifesto, checa se o arquivo .npz físico realmente existe na pasta
            caminho_npz = os.path.join(structures_dir, f"{pdb_id}.npz")
            if os.path.exists(caminho_npz):
                proteinas_sobreviventes.append(pdb_id)
            else:
                motivos_descarte["sem_arquivo_npz"].append(pdb_id)
        else:
            motivos_descarte["nao_no_manifesto"].append(pdb_id)

    # 4. O Relatório Final
    print("\n================ RELATÓRIO FINAL ================")
    print(f"TOTAL ALMEJADO (CSV): {len(ids_csv)}")
    print(f"TOTAL PRONTO PARA TREINO (Sobreviventes): {len(proteinas_sobreviventes)}")
    print(f"TOTAL DESCARTADO: {len(motivos_descarte['nao_no_manifesto']) + len(motivos_descarte['sem_arquivo_npz'])}")
    
    print("\n--- POR QUE FORAM DESCARTADAS? ---")
    print(f"1. Não existem no manifesto do Boltz: {len(motivos_descarte['nao_no_manifesto'])} proteínas")
    print(f"2. Estão no manifesto, mas o arquivo .npz sumiu/corrompeu: {len(motivos_descarte['sem_arquivo_npz'])} proteínas")
    print("=================================================\n")

except Exception as e:
    print(f"ERRO durante a execução: {e}")
