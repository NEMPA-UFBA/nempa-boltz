# Registro de alteracoes NEMPA sobre a arvore Boltz

Atualizado em 2026-10-05. Este registro identifica codigo e pastas da arvore
Boltz upstream que receberam alteracoes locais ou especificas do fork NEMPA.
Ele existe para reduzir o risco de sobrescrever essas mudancas durante merges,
atualizacoes ou reorganizacoes futuras.

## Referencia de comparacao

- Branch de trabalho: `boltz-v1`, no commit `1620647` quando este registro foi criado.
- Referencia adotada para esta auditoria: `origin/patrick`, commit `3aea686`.
- `origin/patrick` e uma branch do fork, nao uma copia garantidamente intacta do
  repositorio original `jwohlwend/boltz`. Use-a como referencia da organizacao
  Patrick/NEMPA, nao como prova da procedencia upstream de cada linha.
- Consulte o estado de qualquer arquivo na referencia com
  `git show origin/patrick:caminho/do/arquivo` e compare com
  `git diff origin/patrick -- caminho/do/arquivo`.

O diff de Git nao inclui arquivos untracked. Verifique tambem `git status
--short`; scripts e documentos locais podem ainda nao aparecer no diff.

### Comparacao com o arquivo do Mac em 2026-10-05

Foi comparado o snapshot em
`NEMPA_CMCAD_2026-10-03/reproducibilidade` com os arquivos atuais no CMCAD:

- `scripts/train/train.py`: diverge. O CMCAD tem o carregador LoRA consolidado
  e o caminho `load_confidence_from_trunk` em memoria descritos neste registro.
- `scripts/train/configs/full.yaml`: a unica diferenca observada foi o comentario
  da lista de validacao, corrigido de 129 para 128 IDs. Nenhum valor executavel
  do YAML apareceu no diff.
- `scripts/train/configs/full_lora.yaml`: sem diferencas.
- `src/boltz/model/modules/trunk.py`: sem diferencas.

Esta comparacao cobre somente esses quatro arquivos; nao atesta que o restante
do arquivo do Mac esteja sincronizado com o CMCAD. O snapshot de 03/10 deve ser
preservado; novas copias devem ir para uma pasta de revisao separada, nao
sobrescrever esse registro historico.

## Alteracoes em codigo do modelo ou treinamento

| Arquivo | Procedencia e alteracao | Estado e validacao |
| --- | --- | --- |
| `src/boltz/model/layers/lora.py` | Modulo LoRA adicionado ao fork: envolve camadas lineares, cria adapters e permite marcar somente os adapters como treinaveis. | Presente na branch; teste de gradiente descrito abaixo. |
| `src/boltz/model/model.py` | Integracao da configuracao LoRA na construcao de `Boltz1`. | Presente na branch; nao foi feita uma rodada completa de treino nesta auditoria. |
| `scripts/train/train.py` | O carregador de pesos mapeia `layer.weight`/`layer.bias` para `layer.original_layer.*`, mantem `lora_A`/`lora_B` inicializados e falha diante de pesos ausentes ou inesperados fora dos adapters. A opcao `load_confidence_from_trunk` cria chaves com prefixo `confidence_module.` em memoria e usa o mesmo carregador. Isso substitui o caminho anterior que salvava e apagava um checkpoint temporario ao lado do checkpoint de entrada. | Modificado localmente em relacao a `origin/patrick`; teste sintetico do caminho normal e da copia para `confidence_module` passou. O checkpoint real nao foi carregado por esta validacao. |
| `src/boltz/model/modules/trunk.py` | Durante treino com gradientes habilitados, se `z` chegar sem `requires_grad`, o modulo o destaca e habilita gradiente. Isso permite que activation checkpointing execute o backward quando a representacao vem de camadas congeladas. | Modificado localmente; teste sintetico de Pairformer com activation checkpointing e alvos LoRA do YAML produziu gradientes finitos e nao nulos. |
| `scripts/train/configs/full.yaml` | Configuracao NEMPA para fine-tuning completo, incluindo caminhos, parametros de treino, manifesto temporal Jan01 e lista de validacao local. | Modificado localmente; YAML parseado e o manifesto de 1.177 registros foi aceito por `Manifest.load`. Em 05/10 foi escolhido o corte PI de 01/01 (1082/128/242). A run `kz8g6i5j` nao isolou comprovadamente `8gqv`/`8gqw` do treino; nenhuma nova run foi iniciada. |
| `scripts/train/configs/full_lora.yaml` | Configuracao NEMPA de fine-tuning LoRA, separada da configuracao de treino completo. | Adicionada ao fork; YAML valido. |

As alteracoes em `train.py` sao funcionais, nao apenas organizacionais. Nao as
substitua por uma versao upstream nem as misture com uma atualizacao de codigo
sem revisar este registro e executar os testes de checkpoint.

## Arquivos NEMPA em pastas upstream

Estes utilitarios sao da equipe NEMPA; sua localizacao sob `scripts/` nao os
torna parte do Boltz upstream:

- `scripts/predict/prepare_boltz_fastas.py`: prepara FASTAs Boltz a partir de
  CIFs e gera o relatorio de selecao.
- `scripts/predict/download_rcsb_fastas_legacy.py`: downloader historico de
  FASTAs RCSB brutos; nao usar como entrada de predicao Boltz.
- `scripts/process/filter_manifest_to_existing_structures.py`: cria um
  manifesto lateral para estruturas NPZ existentes, sem sobrescrever a origem.
- `tests/test_train_checkpoint_loading.py`: teste NEMPA do carregador de pesos.

Os avisos de procedencia ficam nos READMEs de `scripts/predict/`,
`scripts/process/` e `tests/`. `scripts/train/README.md` foi atualizado apenas
para apontar para este registro.

## Evidencia de validacao e limites

- `tests/test_train_checkpoint_loading.py`: carrega pesos sinteticos para a
  arvore base e para `confidence_module`, preservando os parametros LoRA.
- `tests/test_trunk_lora_gradients.py`: verifica gradientes finitos e nao nulos
  dos adapters no Pairformer com activation checkpointing.
- Testes locais de `OuterProductMean` e `TriangleAttention` passaram junto com o
  teste de carregamento: 3 testes e 9 subtestes.
- Um Pairformer minimo com activation checkpointing e os cinco alvos LoRA da
  configuracao produziu gradientes finitos e nao nulos. O adapter de `proj_q`
  isolado comecou com gradiente zero, comportamento compativel com a projecao de
  saida zerada na inicializacao.
- Nao foram executados treino, inferencia completa, carregamento do checkpoint
  real de 6,45 GiB nem os testes de regressao que baixam dados externos.

## Politica sugerida para commits

Manter alteracoes de codigo upstream-derived em commits separados das
ferramentas e documentos locais. Para esta area, uma separacao revisavel seria:

1. suporte ao carregamento de pesos em modelos LoRA, junto com seu teste;
2. ajuste do backward do trunk, com teste proprio;
3. configuracoes de treinamento e split, apos decisao metodologica;
4. organizacao e documentacao dos utilitarios NEMPA.

Nenhum commit deve incluir checkpoints, dados, previsoes ou alteracoes de
treinamento sem revisao explicita. Este registro nao significa que as mudancas
foram aprovadas para publicacao upstream.