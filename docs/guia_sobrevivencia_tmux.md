# Guia de Sobrevivencia tmux (Boltz) - v2

Guia pratico para executar predict e training longos com monitoramento, alertas e automacao.

## 1) Conceitos-chave

- Sessao: workspace completo do tmux (conjunto de janelas).
- Janela: aba dentro de uma sessao.
- Painel: divisao da janela.

Regra simples:

1. Use sessoes para separar fluxos grandes.
2. Use janelas para separar responsabilidades.
3. Use paineis apenas quando quiser ver 2 coisas na mesma tela.

## 2) Comandos basicos

### Criar, listar, anexar e desanexar

```bash
tmux new -s predict_boltz
tmux ls
tmux attach -t predict_boltz
# dentro do tmux: Ctrl+b depois d
```

### Renomear sessao

```bash
# dentro do tmux: Ctrl+b depois $

# fora do tmux
tmux rename-session -t nome_antigo nome_novo
tmux rename-session -t 0 treino_boltz
```

### Descobrir sessao/janela/painel atual

```bash
tmux display-message -p '#S'
tmux display-message -p 'S=#S W=#I:#W P=#P'
```

## 3) Flags mais usadas

- -t: target (alvo).
  - Exemplo: tmux attach -t treino_boltz
- -s: nome da sessao (em criacao) ou source em alguns comandos.
  - Exemplo: tmux new -s treino_boltz
- -d: detached.
  - Exemplo: tmux new -d -s predict_boltz
- -n: nome de janela.
  - Exemplo: tmux new -s treino_boltz -n train
- -p: print em alguns comandos.
  - Exemplo: tmux display-message -p '#S'

## 4) Janela x painel (quando usar)

### Janela (recomendado para jobs longos)

- predict: comando principal do Boltz predict.
- progress: contadores de andamento.
- gpu: nvidia-smi.
- gpu_log: gravacao de CSV de uso da GPU.
- alerts: alertas por regra.
- auto_train: automacao para iniciar treino depois do predict.

Atalhos:

- Ctrl+b depois n: proxima janela.
- Ctrl+b depois p: janela anterior.
- Ctrl+b depois w: seletor visual de janelas.
- Ctrl+b depois ,: renomear janela atual.

### Painel (quando quiser consolidar a visualizacao)

```bash
# dividir lateral (lado a lado)
tmux split-window -h

# dividir horizontal (cima/baixo)
tmux split-window -v

# criar painel antes (esquerda/cima)
tmux split-window -h -b
tmux split-window -v -b
```

Atalhos:

- Ctrl+b depois %: divide lateral.
- Ctrl+b depois ": divide horizontal.
- Ctrl+b + setas: navegar entre paineis.
- Ctrl+b depois Space: alternar layouts predefinidos.

Comandos uteis de layout:

```bash
tmux select-layout even-horizontal
tmux select-layout even-vertical
tmux select-layout tiled
```

## 5) Ambientes Conda por janela

Regras praticas:

1. Janela de predict e train: usar boltz_env.
2. Janela de monitoramento puro (watch/nvidia-smi/find): nao precisa.

Exemplo de ativacao:

```bash
conda activate boltz_env
```

## 6) Fluxo recomendado de operacao

### Predict em lote

```bash
conda run -n boltz_env boltz predict /home/gpu/nempa-boltz/get_subsamples/dados_teste_temporal/yaml \
  --use_msa_server \
  --out_dir /home/gpu/nempa-boltz/get_subsamples/boltz_results_teste_temporal \
  --accelerator gpu --devices 1
```

Observacao importante:

- O Boltz cria subpastas por alvo dentro do out_dir. Isso e esperado.

### Monitoramento de progresso

```bash
watch -n 15 '
TOTAL=$(find /home/gpu/nempa-boltz/get_subsamples/dados_teste_temporal/yaml -maxdepth 1 -name "*.yaml" | wc -l)
DONE=$(find /home/gpu/nempa-boltz/get_subsamples/boltz_results_teste_temporal -path "*/predictions/*/*_model_0.cif" 2>/dev/null | wc -l)
PROC=$(find /home/gpu/nempa-boltz/get_subsamples/boltz_results_teste_temporal -path "*/processed/structures/*.npz" 2>/dev/null | wc -l)
echo "TOTAL: $TOTAL"
echo "PROCESSADOS (intermediario): $PROC"
echo "PREDICOES CONCLUIDAS: $DONE"
echo "RESTANTES: $((TOTAL-DONE))"
'
```

### Monitoramento de GPU

```bash
watch -n 2 nvidia-smi
```

## 7) Logging de GPU em CSV

Use em janela dedicada (gpu_log):

```bash
mkdir -p ~/gpu_logs
LOG=~/gpu_logs/gpu_$(date +%F_%H-%M-%S).csv
echo "timestamp,utilization_gpu,memory_used,memory_total,power_w,temperature_c" > "$LOG"
echo "Logando em: $LOG"
while true; do
  nvidia-smi --query-gpu=timestamp,utilization.gpu,memory.used,memory.total,power.draw,temperature.gpu \
    --format=csv,noheader,nounits >> "$LOG"
  sleep 2
done
```

Obter o ultimo arquivo de log:

```bash
ls -1t ~/gpu_logs/gpu_*.csv | head -n 1
```

## 8) Alertas (beep e mensagem)

### Alerta quando sair a primeira predicao

```bash
while true; do
  DONE=$(find /home/gpu/nempa-boltz/get_subsamples/boltz_results_teste_temporal -path "*/predictions/*/*_model_0.cif" 2>/dev/null | wc -l)
  if [ "$DONE" -ge 1 ]; then
    printf '\a'
    echo "Primeira predicao concluida."
    break
  fi
  sleep 10
done
```

### Alerta quando GPU passar de 70%

```bash
while true; do
  U=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits | head -n1)
  if [ "$U" -ge 70 ]; then
    printf '\a'
    echo "GPU >= 70% (atual: $U%)"
    sleep 30
  else
    sleep 2
  fi
done
```

Nota:

- Em SSH/tmux, o beep pode nao tocar no audio local. A mensagem continua confiavel.

## 9) Automacao: iniciar treino depois do predict

Use em janela dedicada (auto_train):

```bash
cd /home/gpu/nempa-boltz

TOTAL=$(find /home/gpu/nempa-boltz/get_subsamples/dados_teste_temporal/yaml -maxdepth 1 -name "*.yaml" | wc -l)
MAX_WAIT_SEC=$((24*3600))
START_TS=$(date +%F_%H-%M-%S)

echo "Aguardando predict concluir: TOTAL=$TOTAL"

while true; do
  DONE=$(find /home/gpu/nempa-boltz/get_subsamples/boltz_results_teste_temporal -path "*/predictions/*/*_model_0.cif" 2>/dev/null | wc -l)
  echo "[$(date '+%F %T')] DONE=$DONE / TOTAL=$TOTAL"

  if [[ "$TOTAL" -gt 0 && "$DONE" -ge "$TOTAL" ]]; then
    printf '\a'
    echo "Predict concluido. Iniciando treino..."
    break
  fi

  if [[ "$SECONDS" -ge "$MAX_WAIT_SEC" ]]; then
    echo "Tempo maximo de espera atingido."
    exit 1
  fi

  sleep 30
done

mkdir -p /home/gpu/nempa-boltz/logs
TRAIN_LOG="/home/gpu/nempa-boltz/logs/train_after_predict_${START_TS}.log"

export RUN_NAME="mhc_temporal_split_v1_$(date +%F_%H-%M)"
/home/gpu/miniconda3/envs/boltz_env/bin/python scripts/train/train.py scripts/train/configs/full.yaml 2>&1 | tee "$TRAIN_LOG"
```

## 10) WandB e nome da run

Em scripts/train/configs/full.yaml, o nome da run usa RUN_NAME (com fallback para Standard Run).

Se rodar treino manualmente e quiser nome customizado:

```bash
export RUN_NAME="mhc_temporal_split_v1_$(date +%F_%H-%M)"
```

Se nao definir RUN_NAME, o nome padrao sera Standard Run.

## 11) Erros comuns e correcoes

- Erro: tmux unknown option -- t.
  - Correto: tmux rename-session -t 0 treino_boltz

- Erro: Path '' does not exist no boltz predict.
  - Causa: variavel ARQ vazia.
  - Correcao: conferir se ha YAMLs no caminho e imprimir ARQ antes de executar.

- Erro: FileNotFound boltz_checkpoints/boltz1.ckpt no treino.
  - Correcao: garantir checkpoint no caminho configurado (ou link simbolico para o checkpoint real).

- Erro: treino com timeout termina com codigo 124.
  - Significado: comando foi encerrado pelo timeout (nao e falha de import/checkpoint).

## 12) Nota GitHub x CMCAD

Arquivos criados/alterados no servidor so vao para GitHub apos commit e push.

```bash
cd /home/gpu/nempa-boltz
git add docs/guia_sobrevivencia_tmux.md
git commit -m "docs: atualiza guia operacional tmux"
git push
```