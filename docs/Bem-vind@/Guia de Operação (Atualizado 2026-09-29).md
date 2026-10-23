# Guia de Opera��o ? CMCAD (vers�o atualizada, 2026-09-29)

Este documento **complementa** (n�o substitui) os arquivos j� existentes nesta pasta
(`Pimeiro Acesso.md` e `Guia de Opera��o e Boas Pr�ticas.md`). Aqueles dois parecem
ter sido escritos para um layout de servidor diferente do atual (prov�velmente por
Ikaro, em um acesso anterior) ? eles citam `/opt/projeto_cmcad/` e um comando
`usar_gpu` que **n�o existem** neste servidor. N�o foram apagados/sobrescritos;
use este arquivo como a refer�ncia v�lida at� decidirmos consolidar tudo.

## 1. Onde as coisas realmente est�o

- Reposit�rio de trabalho: `/home/gpu/nempa-boltz` (fork do Boltz-1/2 com LoRA).
- Dados RCSB (estruturas + MSA) ficam em `/home/gpu/rcsb_processed_targets` e
  `/home/gpu/rcsb_processed_msa`, linkados dentro do repo via symlink.
- Checkpoint de f�brica (modelo base): `nempa-boltz/boltz_checkpoints/boltz1.ckpt`.
- N�o h� mutex/fila autom�tica de GPU. Coordena��o � manual: combine no time e use
  `nvidia-smi` / `watch -n 2 nvidia-smi` para checar uso antes de rodar algo pesado.
- Ambientes Python: conda, ex. `/home/gpu/miniconda3/envs/boltz_env`. `conda` n�o
  est� no PATH do shell padr�o ? ative com o caminho completo ou `source` do conda.
- Organiza��o de sess�es longas (treino/predict): ver `docs/guia_sobrevivencia_tmux.md`.


## 2. Divis�o temporal dos dados MHC

Para a continuidade do protocolo, em 05/10/2026 foi escolhida a regra de corte
indicada na mensagem do PI no Telegram:

- Treino: liberacao antes de 30/09/2021.
- Validacao: de 30/09/2021 ate antes de 01/01/2023.
- Teste: a partir de 01/01/2023.

Aplicados aos 1.452 IDs unicos de `mhc_data/TCR3d_data.csv`, esses limites produzem
**1.082 treino / 128 validacao / 242 teste**. As listas atuais
`scripts/train/assets/validation_ids.txt` e `scripts/train/assets/test_ids.txt`
correspondem exatamente a essas duas coortes.

### Historico dos cortes e relacao com a run kz8g6i5j

Ha duas regras temporais registradas, e elas diferem somente para `8gqv` e
`8gqw`, ambos liberados em 11/01/2023:

- A recomendacao resumida na mensagem do PI no Telegram usa teste a partir de
  01/01/2023. No CSV, isso resulta em 1.082 treino / 128 validacao / 242 teste.
- O notebook `get_subsamples/get_subsample.ipynb` usa teste a partir de
  13/01/2023. No CSV, isso resulta em 1.082 treino / 130 validacao / 240 teste.

A combinacao 1.082 / 128 / 240 mistura os dois cortes e nao e uma particao valida.
Em 01/10/2026 foi discutido o corte do notebook; em 05/10/2026 foi escolhida
para continuidade a regra de 01/01, por corresponder a recomendacao do PI e as
listas usadas como referencia na ultima run. `mhc_data/test_templated.txt` contem
somente os 240 IDs do corte de 13/01; nao e a lista completa de teste de 242 IDs
do protocolo escolhido.

A run `kz8g6i5j` terminou em 29/09/2026, antes dessa reconciliacao. A configuracao
registrada usou `scripts/train/assets/validation_ids.txt`, com 128 IDs, e o
manifest original. Como `8gqv` e `8gqw` existem fisicamente no dataset e nao
estavam nessa lista, ambos eram elegiveis para treino; nao ha evidencia nos logs
de que tenham sido amostrados. Portanto, a run nao implementou integralmente o
corte de 13/01; sob o corte de 01/01, esses dois IDs tambem deveriam estar
isolados como teste. Os 240 IDs do teste de 13/01 nao tinham NPZ em
`dataset_limpo`, mas isso nao resolve a classificacao desses dois casos de borda.

Estado fisico atual de `mhc_data/dataset_limpo/structures`:

| Categoria temporal | NPZ presentes |
|---|---:|
| Treino | 1.058 |
| Validacao | 119 |
| Teste (a partir de 01/01/2023) | 2 |
| Total | 1.179 |

Os 240 IDs de `mhc_data/test_templated.txt` (corte de 13/01) nao possuem NPZ em
`dataset_limpo`; os outros dois IDs do teste escolhido, `8gqv` e `8gqw`, possuem.
O manifest original tem 1.251 registros, incluindo 72 sem NPZ. O sidecar
`manifest.physical.json` tem 1.179 registros e preserva metadados, mas inclui
`8gqv` e `8gqw`; portanto, nao pode ser usado sozinho para treinar sob o corte de
01/01. Em 05/10/2026 foi criado o manifesto temporal lateral
`manifest.train_val_before_test_2023-01-01.json`, com 1.177 registros e sem
`8gqv`/`8gqw`. `manifest.json` e `manifest.physical.json` foram mantidos intactos.

`SubsetFilter` nao e necessario quando o dataset fisico e o manifest usado contem
somente registros elegiveis para treino/validacao. O Boltz usa
`data.datasets[].manifest_path` quando configurado; sem essa opcao, carrega
`target_dir/manifest.json`. Para uma proxima run sob o corte Jan01, configurar
`manifest_path` como `./mhc_data/dataset_limpo/manifest.train_val_before_test_2023-01-01.json`
e usar os 128 IDs de `scripts/train/assets/validation_ids.txt`. O sidecar
`manifest.physical.json` de 1.179 registros nao basta para esse corte. O
`scripts/train/configs/full.yaml` agora aponta para o manifesto temporal; a
configuracao foi validada, mas nenhuma nova run foi iniciada.
O split separa validacao do treino; ele nao cria um conjunto de teste para predict.

### Run kz8g6i5j e isolamento

A run `kz8g6i5j` terminou 20 epocas em 29/09/2026. Seu checkpoint final e
`mhc_finetune_clean/nempa-boltz/kz8g6i5j/checkpoints/last.ckpt`. A lista de
validacao registrada no WandB corresponde exatamente a coorte Jan01 de 128 IDs.
Porem, a configuracao nao definia `manifest_path`: o dataloader leu o manifesto
original, que inclui `8gqv` e `8gqw`. Como esses NPZs nao estavam na validacao,
eram elegiveis para treino; nao ha evidencia nos logs de que tenham sido amostrados.
Portanto, a run usou a lista de validacao Jan01, mas nao garantiu isolamento completo
do teste Jan01 de 242 IDs. Os 240 IDs do subconjunto Jan13 nao tinham NPZ; os outros
dois IDs do teste escolhido tinham e precisavam ser excluidos do manifesto de treino.
O sidecar fisico foi criado depois da run e nao foi usado retroativamente. As 72
referencias sem NPZ do manifesto original nao representam estruturas treinadas.

## 3. Checkpoints

- Modelo base: `boltz_checkpoints/boltz1.ckpt`.
- Fine-tuning completo de 20 epocas: `mhc_finetune_clean/nempa-boltz/kz8g6i5j/checkpoints/last.ckpt`.
- Run anterior parcial: `mhc_finetune/nempa-boltz/k0cr7qy9/` (ate epoch 3).
- Smoke test LoRA: `mhc_finetune/checkpoints/last-v1.ckpt` (nao e o fine-tuning completo).
- Novas runs LoRA devem usar o output separado configurado em `full_lora.yaml`.

## 4. Acesso ao CMCAD - linha do tempo

- Acesso perdido em julho/2026.
- Acesso recuperado na segunda-feira, 21/09/2026.

## 5. Predicao comparativa: FASTAs e checkpoints

O script legado `scripts/predict/download_rcsb_fastas_legacy.py` baixou 239 arquivos
para `/home/gpu/test_yamls`;
baixados em `/home/gpu/test_yamls` sao arquivos brutos do RCSB, nao FASTAs no schema
do Boltz. Seus headers, por exemplo `>7Q98_3|Chains C, F, I, L, O|...`, causam
`Invalid entity type: Chains`. O endpoint FASTA do RCSB retorna 404 para `8JHV`, embora
seu CIF esteja disponivel.

Para preparar inputs Boltz, use `scripts/predict/prepare_boltz_fastas.py`. Ele baixa os CIFs
para `/home/gpu/test_yamls_cif`, alinha cadeias longas com a cadeia MHC A do CIF
1A1M, seleciona o peptideo pela sequencia do CSV quando disponivel e valida uma
interface de pelo menos 10 contatos atomicos a 4 A. Quando o CSV nao informa um
peptideo, usa a cadeia curta com maior interface e marca esse fallback no relatorio.
Cada FASTA gerado contem apenas duas cadeias, MHC e peptideo, com headers aceitos pelo
Boltz. O `selection_report.tsv` lista as cadeias selecionadas e falhas que precisam
de curadoria; nao inclua entradas com falha no predict.

Execute com Python que tenha Gemmi e Biopython. Neste servidor, `python3` tem ambos;
o `.venv` do Boltz nao tem Gemmi. Para testar dois IDs sem substituir os resultados
do lote:

```bash
cd /home/gpu/nempa-boltz
python3 scripts/predict/prepare_boltz_fastas.py \
  --pdb-ids 7Q98 8JHV \
  --output /tmp/test_yamls_boltz_smoke \
  --cif-cache /tmp/test_yamls_cif_smoke
```

Para preparar a lista completa, os defaults leem `mhc_data/test_templated.txt`,
gravando em `/home/gpu/test_yamls_boltz` e `/home/gpu/test_yamls_cif`:

```bash
cd /home/gpu/nempa-boltz
python3 scripts/predict/prepare_boltz_fastas.py
```

Revise `/home/gpu/test_yamls_boltz/selection_report.tsv` antes do predict. O lote
esperado tem 240 IDs; quantidade menor significa que ha casos para revisar. Use os
mesmos FASTAs aprovados e parametros para comparar os dois checkpoints:

```bash
INPUT=/home/gpu/test_yamls_boltz

.venv/bin/boltz predict "$INPUT" \
  --checkpoint /home/gpu/nempa-boltz/boltz_checkpoints/boltz1.ckpt \
  --use_msa_server \
  --out_dir /home/gpu/nempa-boltz/predictions_base \
  --accelerator gpu --devices 1

.venv/bin/boltz predict "$INPUT" \
  --checkpoint /home/gpu/nempa-boltz/mhc_finetune_clean/nempa-boltz/kz8g6i5j/checkpoints/last.ckpt \
  --use_msa_server \
  --out_dir /home/gpu/nempa-boltz/predictions_treinado \
  --accelerator gpu --devices 1
```

Antes do lote, validar um arquivo convertido com `boltz predict` e confirmar que as
cadeias correspondem ao MHC e peptideo usados no benchmark. A flag `--checkpoint` e
suportada pela CLI; o bloqueio atual e o formato/curadoria dos inputs, nao o caminho
dos checkpoints.
