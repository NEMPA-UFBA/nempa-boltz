# Documentação Técnica — Estrutura de Dados do Projeto NEMPA-Boltz
> **Repositório:** [NEMPA-UFBA/nempa-boltz](https://github.com/NEMPA-UFBA/nempa-boltz) · Branch: `rafael`  
> **Base upstream:** [jwohlwend/boltz](https://github.com/jwohlwend/boltz) (MIT License)  
> **Dataset fonte:** [boltz1.s3.us-east-2.amazonaws.com/rcsb_processed_targets.tar](https://boltz1.s3.us-east-2.amazonaws.com/rcsb_processed_targets.tar)  
> **Padrão de dados de origem:** [RCSB PDB](https://www.rcsb.org/) / wwPDB / PDBx-mmCIF  

---

## 1. Visão Geral da Arquitetura de Dados

O projeto NEMPA usa o Boltz (versão Boltz-1 e Boltz-2) como framework de predição de interações biomoleculares. O foco específico do projeto é o complexo **MHC–Peptídeo**, utilizado para modelagem de apresentação antigênica. A cadeia de dados segue o fluxo:

```
RCSB PDB (mmCIF/PDBx)
        │
        ▼
rcsb_processed_targets.tar  (AWS S3 · Boltz oficial)
  ├── manifest.json          ← índice de todos os alvos
  └── structures/
        └── {pdb_id}.npz    ← coordenadas + features binárias

rcsb_processed_msa.tar      (AWS S3 · Boltz oficial)
  └── {sha256_sequencia}.npz ← MSA pré-computadas (ColabFold)
        │
        ▼
Pipeline NEMPA (branch rafael)
  ├── auditar_dados.py       ← cruza CSV clínico × manifesto × .npz
  ├── get_subsamples.py      ← filtra e copia alvos MHC-Peptídeo
  ├── limpar_cadeias.py      ← cirurgia nas cadeias e máscara .npz
  └── analise_descartes.py   ← relatório de descarte por critério biológico
        │
        ▼
mhc_data/dataset_limpo/
  ├── manifest.json          ← manifesto filtrado (apenas MHC-Peptídeo válidos)
  ├── structures/
  │     └── {pdb_id}.npz    ← .npz com mask atualizado
  └── msa/
        └── {msa_id}.npz    ← MSAs copiadas apenas para cadeias válidas
```

---

## 2. Padrão de Dados de Origem — RCSB PDB / PDBx-mmCIF

### 2.1 Formato Canônico

Todo dado estrutural no RCSB segue o dicionário **PDBx/mmCIF (macromolecular Crystallographic Information Framework)**, mantido pela wwPDB. Cada entrada PDB é identificada por um código de 4 caracteres alfanuméricos (ex: `1a1m`).

### 2.2 Hierarquia Oficial de Objetos RCSB

| Objeto Core | Identificador | Descrição |
|---|---|---|
| `core_entry` | `pdb_id` (4 chars) | Dados globais da entrada PDB (método, resolução, datas) |
| `core_polymer_entity` | `<pdb_id>_<entity_id>` | Entidade polimérica — proteína, RNA ou DNA |
| `core_nonpolymer_entity` | `<pdb_id>_<entity_id>` | Ligante, íon, cofator |
| `core_polymer_entity_instance` | `<pdb_id>.<asym_id>` | Instância de cadeia específica (= chain) |
| `core_assembly` | `<pdb_id>-<assembly_id>` | Montagem biológica |
| `core_chem_comp` | `chem_comp_id` (3 chars) | Componente químico do CCD |

### 2.3 Tags mmCIF que Alimentam o `manifest.json`

| Campo do manifest.json | Tag mmCIF de Origem |
|---|---|
| `structure.resolution` | `_reflns.d_resolution_high` |
| `structure.method` | `_exptl.method` |
| `structure.deposited` | `_pdbx_database_status.recvd_initial_deposition_date` |
| `structure.released` | `_pdbx_audit_revision_history.revision_date` (1ª revisão) |
| `structure.revised` | `_pdbx_audit_revision_history.revision_date` (última) |
| `chain.chain_name` | `_atom_site.label_asym_id` |
| `chain.mol_type` | `_entity.type` → `polypeptide(L)`, `polyribonucleotide`, `polydeoxyribonucleotide`, `non-polymer` |
| `chain.num_residues` | Contagem de `_atom_site.label_seq_id` únicos por cadeia |

### 2.4 APIs de Acesso Oficial RCSB

- **REST:** `GET https://data.rcsb.org/rest/v1/core/{objeto}/{id}`
- **GraphQL:** `POST https://data.rcsb.org/graphql`
- **Download de arquivos:** `https://files.rcsb.org/download/{PDB_ID}.cif`
- **Sequências:** `https://files.rcsb.org/pub/pdb/derived_data/pdb_seqres.txt.gz`
- **Clusters 40%:** `https://cdn.rcsb.org/resources/sequence/clusters/clusters-by-entity-40.txt`

---

## 3. Estrutura Física do Dataset (`rcsb_processed_targets.tar`)

```
rcsb_processed_targets/
├── manifest.json            ← índice JSON com metadados de todos os alvos
└── structures/
      ├── 1a1m.npz
      ├── 4hhb.npz
      └── ... (~200k entradas)
```

O `manifest.json` é a **única fonte de verdade** sobre quais estruturas estão disponíveis no dataset. Os arquivos `.npz` contêm as coordenadas atômicas e features binárias processadas.

---

## 4. Schema Completo do `manifest.json`

### 4.1 Formato Raiz

O `manifest.json` é um **array JSON** (`list`) — **não** um objeto com chave `records` como no Boltz original.  
Cada elemento do array é um `Record` correspondente a uma entrada PDB.

```json
[
  { /* Record 1 */ },
  { /* Record 2 */ },
  ...
]
```

### 4.2 Objeto `Record` — Campos de Nível Superior

| Campo | Tipo | Obrigatório | Declaração | Exemplo Real (`1a1m`) |
|---|---|---|---|---|
| `id` | `string` | ✅ | PDB ID em letras **minúsculas** (4 chars). Chave primária do registro. Usado para localizar o `.npz` correspondente e para o split treino/validação | `"1a1m"` |
| `structure` | `Object` | ✅ | Metadados globais da estrutura, derivados do cabeçalho mmCIF | ver §4.3 |
| `chains` | `Array[Chain]` | ✅ | Lista de todas as cadeias moleculares presentes na estrutura | ver §4.4 |
| `interfaces` | `Array[Interface]` | ✅ | Lista de interfaces entre pares de cadeias (pode ser `[]`) | ver §4.5 |
| `affinity` | `null \| Object` | ✅ | **Campo NEMPA (extensão):** reservado para dados de afinidade de ligação (Boltz-2). `null` em entradas sem dado de afinidade | `null` |
| `md` | `null \| Object` | ✅ | **Campo NEMPA (extensão):** reservado para dados de dinâmica molecular. `null` em entradas sem simulação MD associada | `null` |

### 4.3 Objeto `structure`

Derivado do cabeçalho PDBx/mmCIF da entrada. Todos os campos podem ser `null` para modelos computacionais sem dados experimentais.

| Campo | Tipo | Declaração | Exemplo Real (`1a1m`) |
|---|---|---|---|
| `resolution` | `float \| null` | Resolução em **Ångströms (Å)**. Derivado de `_reflns.d_resolution_high`. `null` para estruturas NMR ou modelos computacionais. `0.0` indica ultra-alta resolução | `0.0` |
| `method` | `string \| null` | Método experimental de determinação da estrutura. Em **letras minúsculas** no NEMPA (diferente do Boltz original que usa maiúsculas). Valores possíveis: `"x-ray diffraction"`, `"electron microscopy"`, `"solution nmr"`, `"neutron diffraction"`, `"electron crystallography"` | `"x-ray diffraction"` |
| `deposited` | `string \| null` | Data de deposição inicial no PDB. Formato **ISO 8601**: `"YYYY-MM-DD"`. Derivado de `_pdbx_database_status.recvd_initial_deposition_date` | `"1997-12-11"` |
| `released` | `string \| null` | Data de liberação pública da entrada no PDB. Formato `"YYYY-MM-DD"`. Derivado de `_pdbx_audit_revision_history.revision_date` (1ª entrada) | `"1998-04-08"` |
| `revised` | `string \| null` | Data da **última** revisão/atualização da entrada. Formato `"YYYY-MM-DD"`. Indica quão atual são os dados estruturais | `"2023-08-02"` |
| `num_chains` | `int` | Número total de cadeias na estrutura (proteínas + DNA/RNA + ligantes). Corresponde ao número de `label_asym_id` únicos no mmCIF | `3` |
| `num_interfaces` | `int \| null` | Número de interfaces entre cadeias calculadas pelo pipeline Boltz. `null` se não computado | `2` |

### 4.4 Objeto `Chain` (por cadeia)

> ⚠️ **Diferenças NEMPA vs. Boltz Original:** os campos `cluster_id`, `msa_id` são `string` no NEMPA (vs. `int` no Boltz), e o campo `template_id` é exclusivo do NEMPA.

| Campo | Tipo | Declaração | Diferença NEMPA | Exemplo Real (`1a1m`) |
|---|---|---|---|---|
| `chain_id` | `int` | Índice numérico interno da cadeia no contexto da entrada PDB. Começa em `0`. Usado como referência em `interfaces.chain_1` e `interfaces.chain_2`, e como índice no array `mask` do `.npz` | Igual ao Boltz | `0`, `1`, `2` |
| `chain_name` | `string` | Nome da cadeia. No NEMPA, **sufixo numérico `1` é adicionado** ao `label_asym_id` mmCIF original (ex: `A` → `A1`). Isso diferencia instâncias em montagens biológicas | Formato `"X1"` em vez de `"X"` | `"A1"`, `"B1"`, `"C1"` |
| `mol_type` | `int` | **Enum** de tipo molecular: `0` = Proteína (polipeptídeo), `1` = RNA, `2` = DNA, `3` = Ligante / molécula pequena / íon | Igual ao Boltz | `0` (todas proteínas em `1a1m`) |
| `cluster_id` | `string` | ID do cluster de sequência gerado com **40% de similaridade via mmseqs2** sobre `pdb_seqres.txt.gz`. Formato NEMPA: `"<pdb_id_representante>_<índice>"` (ex: `"2yez_0"`). `-1` (como int) indica sem cluster | **`string`** no NEMPA vs. `int` no Boltz | `"2yez_0"`, `"7cjq_1"`, `"1a1m_2"` |
| `msa_id` | `string` | Referência ao arquivo MSA pré-computado em `rcsb_processed_msa/`. Formato NEMPA: `"<pdb_id>_<letra_cadeia>"` (ex: `"1a1m_a"`). `-1` (int) indica sem MSA (ligantes, DNA/RNA sem MSA disponível) | **`string`** no NEMPA vs. `int` no Boltz | `"1a1m_a"`, `"7kgr_b"`, `"1a1m_c"` |
| `template_id` | `string` | **Campo exclusivo NEMPA.** Aponta para o template estrutural usado no treinamento. Mesmo formato de `msa_id`. Permite rastrear qual estrutura serviu de template para cada cadeia | ❌ Não existe no Boltz | `"1a1m_a"`, `"7kgr_b"`, `"1a1m_c"` |
| `num_residues` | `int` | Número de resíduos aminoacídicos (para proteínas) ou bases (para DNA/RNA) ou átomos pesados (para ligantes) na cadeia. **Critério biológico NEMPA:** MHC ≥ 200 resíduos; Peptídeo ≤ 25 resíduos | Igual ao Boltz | `278` (MHC), `99` (β₂m), `9` (peptídeo) |
| `valid` | `bool` | `true` se a cadeia **passou em todos os filtros de qualidade** e deve ser usada no treinamento. `false` marca cadeias descartadas. **No NEMPA, esse campo é manipulado ativamente** pelos scripts de limpeza para selecionar apenas as cadeias MHC e peptídeo alvo | Mesmo semântica, uso mais ativo no NEMPA | `true`, `false`, `true` |

#### Tabela de `mol_type`

| Valor | Tipo Molecular | Critério NEMPA |
|---|---|---|
| `0` | Proteína (polipeptídeo L) | MHC: `num_residues ≥ 200`; Peptídeo: `num_residues ≤ 25` |
| `1` | RNA | Não é alvo do pipeline MHC |
| `2` | DNA | Não é alvo do pipeline MHC |
| `3` | Ligante / molécula pequena / íon | `msa_id = -1` (sem MSA) |

### 4.5 Objeto `Interface`

> ⚠️ **Diferença NEMPA:** o campo `num_contacts` (presente no Boltz original) está **ausente** no NEMPA. O campo `valid` é **exclusivo do NEMPA**.

| Campo | Tipo | Declaração | Diferença NEMPA | Exemplo Real (`1a1m`) |
|---|---|---|---|---|
| `chain_1` | `int` | `chain_id` da primeira cadeia da interface (a de menor índice) | Igual ao Boltz | `0`, `0` |
| `chain_2` | `int` | `chain_id` da segunda cadeia da interface | Igual ao Boltz | `1`, `2` |
| `num_contacts` | `int` | Número de contatos atômicos entre as duas cadeias (calculado pelo pipeline Boltz) | **Ausente no NEMPA** | — |
| `valid` | `bool` | **Campo exclusivo NEMPA.** `true` se ambas as cadeias (`chain_1` e `chain_2`) estão marcadas como `valid: true`. Uma interface é válida somente se **ambas** as cadeias que a compõem são alvos selecionados | ❌ Não existe no Boltz | `false` (chain_1+chain_2=0+1), `true` (0+2) |

---

## 5. Estrutura do Arquivo `.npz` (por entrada PDB)

Cada entrada PDB gera um arquivo `{pdb_id}.npz` (formato NumPy comprimido) com os seguintes arrays:

| Array | Shape | Dtype | Descrição |
|---|---|---|---|
| `coords` | `(N_atoms, 3)` | `float32` | Coordenadas cartesianas (x, y, z) em Ångströms de todos os átomos pesados |
| `mask` | `(N_chains,)` | `bool` | **Máscara de cadeias válidas.** Índice `i` = `True` se `chains[i]['valid'] == true`. Manipulado por `limpar_cadeias.py` |
| `residue_index` | `(N_residues,)` | `int32` | Índice sequencial de cada resíduo na estrutura |
| `chain_index` | `(N_residues,)` | `int32` | `chain_id` de cada resíduo (referência ao campo `chain_id` do manifest) |
| `aatype` | `(N_residues,)` | `int32` | Tipo de aminoácido/base como índice inteiro (0–19 para aminoácidos standard) |
| `atom_mask` | `(N_residues, 37)` | `bool` | Indica quais dos 37 átomos backbone+sidechain estão presentes para cada resíduo |
| `atom_positions` | `(N_residues, 37, 3)` | `float32` | Posições dos 37 átomos por resíduo |
| `b_factors` | `(N_residues, 37)` | `float32` | B-factors (fatores de temperatura) dos átomos, indicam mobilidade atômica |

---

## 6. Pipeline de Processamento NEMPA

### 6.1 Fluxo Completo

```
mhc_data/TCR3d_data.csv          mhc_data/train_templated.json
           │                                    │
           ▼                                    ▼
    auditar_dados.py              get_subsamples.py
    (cruza CSV × manifesto        (filtra por chain_name
     × .npz físico)                peptide_chain + protein_chains)
           │                                    │
           ▼                                    ▼
   Relatório de IDs           mhc_data/dataset_limpo/
   disponíveis                ├── manifest.json (filtrado)
                              ├── structures/{pdb_id}.npz
                              └── msa/{msa_id}.npz
                                          │
                                          ▼
                               limpar_cadeias.py
                               (atualiza valid por
                                critério biológico:
                                MHC ≥200, pep ≤25)
                                          │
                                          ▼
                               analise_descartes.py
                               (gera relatorio_descartes
                                _detalhado.txt)
```

### 6.2 Critérios de Validação de Cadeias (Biológicos)

| Critério | Condição | Script | Diagnóstico de Descarte |
|---|---|---|---|
| MHC Completo | `num_residues ≥ 200` | `limpar_cadeias.py` / `analise_descartes.py` | `"MHC Incompleto"` |
| Peptídeo Presente | `num_residues ≤ 25` | `limpar_cadeias.py` / `analise_descartes.py` | `"Pep. Ausente"` |
| Mínimo 2 cadeias | `len(chains) ≥ 2` | `limpar_cadeias.py` | descarte silencioso |
| No manifesto oficial | `pdb_id ∈ ids_manifesto` | `auditar_dados.py` | `"Não consta no manifesto"` |
| Arquivo físico existe | `.npz` em `structures/` | `auditar_dados.py` | `"sem_arquivo_npz"` |

### 6.3 Algoritmo de Seleção de Cadeias (`get_subsamples.py`)

```python
# Entrada: template JSON com campos:
# { "pdb_id": "1A1M", "peptide_chain": "C", "protein_chains": ["A"] }

peptide_target = sample['peptide_chain'] + '1'   # ex: "C" → "C1"
protein_targets = [c + '1' for c in sample['protein_chains']]  # ["A"] → ["A1"]

for chain in data['chains']:
    is_target = (chain['chain_name'] == peptide_target 
                 or chain['chain_name'] in protein_targets)
    chain['valid'] = is_target
```

---

## 7. Exemplo Real Completo — Entrada `1a1m`

```json
{
  "id": "1a1m",
  "structure": {
    "resolution": 0.0,
    "method": "x-ray diffraction",
    "deposited": "1997-12-11",
    "released": "1998-04-08",
    "revised": "2023-08-02",
    "num_chains": 3,
    "num_interfaces": 2
  },
  "chains": [
    {
      "chain_id": 0,
      "chain_name": "A1",
      "mol_type": 0,
      "cluster_id": "2yez_0",
      "msa_id": "1a1m_a",
      "template_id": "1a1m_a",
      "num_residues": 278,
      "valid": true
    },
    {
      "chain_id": 1,
      "chain_name": "B1",
      "mol_type": 0,
      "cluster_id": "7cjq_1",
      "msa_id": "7kgr_b",
      "template_id": "7kgr_b",
      "num_residues": 99,
      "valid": false
    },
    {
      "chain_id": 2,
      "chain_name": "C1",
      "mol_type": 0,
      "cluster_id": "1a1m_2",
      "msa_id": "1a1m_c",
      "template_id": "1a1m_c",
      "num_residues": 9,
      "valid": true
    }
  ],
  "interfaces": [
    { "chain_1": 0, "chain_2": 1, "valid": false },
    { "chain_1": 0, "chain_2": 2, "valid": true  }
  ],
  "affinity": null,
  "md": null
}
```

**Interpretação biológica:**
- Cadeia `A1` (chain_id=0): **MHC Classe I** (278 resíduos ≥ 200) → `valid: true`
- Cadeia `B1` (chain_id=1): **β₂-microglobulina** (99 resíduos) → `valid: false` (não é alvo primário do pipeline MHC-Peptídeo NEMPA)
- Cadeia `C1` (chain_id=2): **Peptídeo antigênico** (9 resíduos ≤ 25) → `valid: true`
- Interface 0↔1: `valid: false` (cadeia B1 não é válida)
- Interface 0↔2: `valid: true` (**contato MHC–Peptídeo** — interface de interesse biológico)

---

## 8. Arquivos de Referência Cruzada

| Arquivo | Localização | Papel no Pipeline |
|---|---|---|
| `manifest.json` | `rcsb_processed_targets/manifest.json` | Índice master de todos os alvos PDB |
| `manifest.json` (filtrado) | `mhc_data/dataset_limpo/manifest.json` | Subconjunto MHC-Peptídeo validado |
| `mhc_manifest_filtered.json` | `mhc_data/` | Manifesto intermediário (pós-auditoria) |
| `train_templated.json` | `mhc_data/` | Lista de alvos de treino com info de cadeias |
| `val_templated.json` | `mhc_data/` | Lista de alvos de validação |
| `validation_ids.txt` | raiz do repo | IDs PDB reservados para validação |
| `TCR3d_data.csv` | `mhc_data/` | Fonte clínica de IDs PDB de complexos MHC |
| `mhc_split.txt` | `mhc_data/` | Lista de todos os PDB IDs MHC candidatos |

---

## 9. Fontes Oficiais

| Recurso | URL |
|---|---|
| RCSB PDB | https://www.rcsb.org |
| Documentação de APIs RCSB | https://www.rcsb.org/docs/general-help/web-services-overview |
| Download de arquivos RCSB | https://www1.rcsb.org/docs/programmatic-access/file-download-services |
| Dicionário PDBx/mmCIF | https://mmcif.wwpdb.org/ |
| AWS Open Data — Boltz-1 | https://registry.opendata.aws/boltz1/ |
| Repositório Boltz (upstream) | https://github.com/jwohlwend/boltz |
| Documentação de Treino Boltz | https://github.com/jwohlwend/boltz/blob/main/docs/training.md |
| Paper Boltz-1 (bioRxiv) | https://doi.org/10.1101/2024.11.19.624167 |
| Paper Boltz-2 (bioRxiv) | https://doi.org/10.1101/2025.06.14.659707 |
