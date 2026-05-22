import json

notebook = {
    "cells": [],
    "metadata": {},
    "nbformat": 4,
    "nbformat_minor": 5
}

def add_markdown(text):
    notebook["cells"].append({
        "cell_type": "markdown",
        "metadata": {},
        "source": [line + "\\n" for line in text.split("\\n")]
    })

def add_code(text):
    notebook["cells"].append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [line + "\\n" for line in text.split("\\n")]
    })

# Introducao
add_markdown("""# 🧬 EDA: NEMPA-Boltz (Complexos MHC-Peptídeo)
Esta análise exploratória foi desenhada para investigar os dados presentes na pasta `mhc_data/` e arquivos personalizados do repositório `nempa-boltz` (branch `rafael`).
Focaremos na base de manifestos (`mhc_manifest_filtered.json`), cruzando com a base de dados clínica (`TCR3d_data.csv`) e os splits de treino/validação.""")

# Imports
add_code("""import pandas as pd
import numpy as np
import json
import os
import matplotlib.pyplot as plt
import seaborn as sns

# Configurações de estilo
sns.set_theme(style="whitegrid")
plt.rcParams['figure.figsize'] = (10, 6)""")

# Carregamento CSV
add_markdown("""## 1. Análise da Base Clínica: `TCR3d_data.csv`
Nesta etapa, analisamos a base clínica contendo informações de MHC e os peptídeos.""")

add_code("""csv_path = 'mhc_data/TCR3d_data.csv'
df_clinico = pd.read_csv(csv_path)

# Tratamento básico: transformar ID para minúsculo e remover nulos
df_clinico['PDB ID'] = df_clinico['PDB ID'].str.lower().dropna()

display(df_clinico.head())
print(f"Total de registros na base clínica: {len(df_clinico)}")""")

# EDA CSV
add_code("""fig, axes = plt.subplots(1, 2, figsize=(16, 5))

# Distribuição de Espécies
sns.countplot(data=df_clinico, y='Species', order=df_clinico['Species'].value_counts().index, ax=axes[0], palette="viridis")
axes[0].set_title('Distribuição de Espécies (TCR3d)')

# Comprimento dos Peptídeos
df_clinico['Peptide_Length'] = df_clinico['Peptide*'].astype(str).apply(lambda x: len(x) if x != 'nan' else 0)
sns.histplot(df_clinico[df_clinico['Peptide_Length'] > 0]['Peptide_Length'], bins=20, ax=axes[1], color="salmon", discrete=True)
axes[1].set_title('Distribuição do Tamanho dos Peptídeos')
axes[1].set_xlabel('Tamanho (Número de Aminoácidos)')

plt.tight_layout()
plt.show()""")

# Carregamento do Manifesto
add_markdown("""## 2. Análise Estrutural: `mhc_manifest_filtered.json`
O manifesto é a nossa fonte primária da verdade (proveniente do Boltz/RCSB). Vamos entender os metadados de estrutura.""")

add_code("""manifest_path = 'mhc_data/mhc_manifest_filtered.json'

with open(manifest_path, 'r') as f:
    manifest_data = json.load(f)
    
print(f"Total de complexos no manifesto filtrado: {len(manifest_data)}")""")

add_code("""# Extrair dados de 'structure' para um DataFrame
structures_list = []
for item in manifest_data:
    pdb_id = item.get('id')
    struct = item.get('structure', {})
    structures_list.append({
        'pdb_id': pdb_id,
        'resolution': struct.get('resolution'),
        'method': struct.get('method'),
        'released': pd.to_datetime(struct.get('released')),
        'num_chains': struct.get('num_chains')
    })
    
df_struct = pd.DataFrame(structures_list)
display(df_struct.head())""")

# EDA Metadados Estruturais
add_code("""fig, axes = plt.subplots(1, 2, figsize=(16, 5))

# Distribuição de Resolução (excluindo 0.0 que geralmente é NMR ou computational)
sns.histplot(df_struct[df_struct['resolution'] > 0]['resolution'], bins=30, ax=axes[0], kde=True, color='purple')
axes[0].set_title('Distribuição da Resolução (Å) - (Apenas Difração)')

# Método Experimental
sns.countplot(data=df_struct, y='method', order=df_struct['method'].value_counts().index, ax=axes[1], palette='magma')
axes[1].set_title('Método Experimental de Determinação')

plt.tight_layout()
plt.show()""")

# Analise das Cadeias e Validacao Biologica
add_markdown("""## 3. Análise das Cadeias e Critérios Biológicos
Segundo o arquivo `NEMPA_Boltz_Documentacao_Dados.md` e scripts de descarte (`analise_descartes.py`), os critérios são:
- MHC deve ter no mínimo **200** resíduos.
- Peptídeo deve ter no máximo **25** resíduos.
- Marcados com `valid: true` no manifesto.""")

add_code("""# Nivelando a lista de cadeias
chains_list = []
for item in manifest_data:
    pdb_id = item.get('id')
    for chain in item.get('chains', []):
        chains_list.append({
            'pdb_id': pdb_id,
            'chain_name': chain.get('chain_name'),
            'mol_type': chain.get('mol_type'),
            'num_residues': chain.get('num_residues'),
            'valid': chain.get('valid')
        })

df_chains = pd.DataFrame(chains_list)

print(f"Total de cadeias no dataset: {len(df_chains)}")
print(f"Total de cadeias válidas: {df_chains['valid'].sum()}")
display(df_chains.head())""")

add_code("""# Distinguir visualmente as cadeias baseadas no número de resíduos e validade
df_valid_chains = df_chains[df_chains['valid'] == True]

plt.figure(figsize=(10, 6))
sns.histplot(data=df_valid_chains, x='num_residues', bins=50, color="teal", kde=False)
plt.axvline(x=25, color='red', linestyle='--', label='Max Peptídeo (25)')
plt.axvline(x=200, color='blue', linestyle='--', label='Min MHC (200)')
plt.title('Tamanho das Cadeias Válidas (Resíduos)')
plt.xlabel('Número de Resíduos')
plt.ylabel('Contagem')
plt.legend()
plt.yscale('log') # Log scale para vizualizar melhor a separação entre pep e mhc
plt.show()""")

# Splits de Treino/Validacao
add_markdown("""## 4. Auditoria de Splits de Treino e Validação
Como o script `auditar_dados.py` faz o cruzamento de dados, vamos analisar as partições em `mhc_split.txt`, `mhc_train.txt` e `val_templated.txt`.""")

add_code("""# Carregando Splits
def load_list(filepath):
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return set([line.strip().lower() for line in f.readlines() if line.strip()])
    return set()

mhc_split = load_list('mhc_data/mhc_split.txt')
mhc_train = load_list('mhc_data/mhc_train.txt')
mhc_val = load_list('validation_ids.txt')

print(f"Total de alvos previstos (mhc_split): {len(mhc_split)}")
print(f"Alocados para treino: {len(mhc_train)}")
print(f"Alocados para validação: {len(mhc_val)}")

# Cruzando dados CSV com Manifesto
ids_csv = set(df_clinico['PDB ID'].dropna())
ids_manifest = set(df_struct['pdb_id'])

print(f"\\nAuditoria Simples:")
print(f"Estão no CSV mas NÃO no Manifesto Filtrado: {len(ids_csv - ids_manifest)}")
print(f"Estão no Manifesto Filtrado mas NÃO no CSV: {len(ids_manifest - ids_csv)}")
print(f"Interseção (Prontos): {len(ids_csv.intersection(ids_manifest))}")""")

with open('EDA_NEMPA_Boltz.ipynb', 'w') as f:
    json.dump(notebook, f, indent=2)

print("Notebook salvo com sucesso.")