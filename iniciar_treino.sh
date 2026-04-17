#!/bin/bash

# Arquivo invisível que vai guardar a memória de qual rodada estamos
ARQUIVO_CONTADOR="mhc_data/.run_counter"

# Se o arquivo não existir (primeira vez), ele cria começando do 1
if [ ! -f "$ARQUIVO_CONTADOR" ]; then
    echo "1" > "$ARQUIVO_CONTADOR"
fi

# Lê o número atual da rodada
RUN_NUM=$(cat "$ARQUIVO_CONTADOR")

# Pega a data de hoje no formato DD/MM/YYYY
HOJE=$(date +%d/%m/%Y)

# Monta o nome dinâmico e exporta para o YAML ler
export RUN_NAME="Run ${RUN_NUM} - Boltz - ${HOJE}"

echo "=================================================="
echo "🚀 INICIANDO TREINAMENTO AUTOMATIZADO NEMPA"
echo "📊 Indexador WandB: $RUN_NAME"
echo "=================================================="

# Dispara o treinamento real
python scripts/train/train.py scripts/train/configs/full.yaml

# Quando o treinamento terminar (ou se você der Ctrl+C), ele soma +1 para a próxima vez
PROXIMO_NUM=$((RUN_NUM + 1))
echo "$PROXIMO_NUM" > "$ARQUIVO_CONTADOR"
