#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="${NEMPA_DIR:-$HOME/nempa-boltz}"
DRIVE1="gdrive1:nempa-boltz"
DRIVE2="gdrive2:nempa-boltz"
LOG_DIR="$HOME/rclone_logs/nempa"
STATE="$LOG_DIR/state.txt"
mkdir -p "$LOG_DIR"

ts()         { date +%H:%M:%S; }
log()        { echo "[$(ts)] $*" | tee -a "${ACTIVE_LOG:-$LOG_DIR/main.log}"; }
done_check() { grep -qxF "OK:$1" "$STATE" 2>/dev/null; }
done_mark()  { echo "OK:$1" >> "$STATE"; }

send() {
  local SRC="$1" DST="$2"
  log "→ $(basename $SRC) ⟶ $DST"
  rclone copy "$SRC" "$DST" \
    --drive-chunk-size 128M \
    --drive-upload-cutoff 128M \
    --transfers 8 \
    --checkers 16 \
    --retries 10 \
    --low-level-retries 30 \
    --timeout 600s \
    --drive-stop-on-upload-limit \
    --stats 60s --stats-one-line \
    --log-level INFO \
    --log-file "${ACTIVE_LOG:-$LOG_DIR/main.log}" 2>&1 \
  && { done_mark "$SRC→$DST"; log "✓ $(basename $SRC)"; } \
  || log "✗ $(basename $SRC) — execute: bash upload.sh resume"
}

upload_full() {
  local DRIVE="$1" LOG="$2"
  ACTIVE_LOG="$LOG"
  log "=== CÓPIA COMPLETA → $DRIVE ==="
  local SRC="$SOURCE_DIR"
  local DST="$DRIVE"
  done_check "$SRC→$DST" && { log "↩ Já enviado para $DRIVE"; return; }
  send "$SRC" "$DST"
}

case "${1:-help}" in
  upload)
    log "=== INÍCIO: cópia completa (550GB) nas 2 contas em paralelo ==="
    # Drive 2 em background — limite 750GB/dia é independente por conta
    ( upload_full "$DRIVE2" "$LOG_DIR/drive2.log" ) &
    PID=$!
    log "Drive 2 rodando em background (PID: $PID)"
    # Drive 1 no foreground
    upload_full "$DRIVE1" "$LOG_DIR/drive1.log"
    log "Drive 1 concluído. Aguardando Drive 2..."
    wait "$PID" 2>/dev/null && log "✓ Drive 2 concluído" || log "Drive 2 encerrou com erro"
    log "=== FIM — execute: bash upload.sh verify ==="
    ;;
  resume)
    log "Retomando uploads incompletos..."
    ( upload_full "$DRIVE2" "$LOG_DIR/drive2.log" ) &
    PID=$!
    upload_full "$DRIVE1" "$LOG_DIR/drive1.log"
    wait "$PID" 2>/dev/null || true
    log "Resume concluído."
    ;;
  verify)
    echo "=== Verificando Drive 1 ==="
    rclone check "$SOURCE_DIR" "$DRIVE1" --checkers 16 --one-way -v \
      2>&1 | tee "$LOG_DIR/verify_drive1.log"
    echo "=== Verificando Drive 2 ==="
    rclone check "$SOURCE_DIR" "$DRIVE2" --checkers 16 --one-way -v \
      2>&1 | tee "$LOG_DIR/verify_drive2.log"
    ;;
  estimate)
    echo "=== Tamanho total a ser copiado para CADA conta ==="
    du -sh "$SOURCE_DIR"
    echo ""
    echo "Breakdown:"
    du -sh "$SOURCE_DIR"/* 2>/dev/null | sort -h
    ;;
  status)
    echo "=== Itens concluídos ==="
    cat "$STATE" 2>/dev/null || echo "nenhum ainda"
    echo ""
    echo "--- Drive 1 — últimas 20 linhas ---"
    tail -20 "$LOG_DIR/drive1.log" 2>/dev/null || echo "sem log"
    echo ""
    echo "--- Drive 2 — últimas 20 linhas ---"
    tail -20 "$LOG_DIR/drive2.log" 2>/dev/null || echo "sem log"
    ;;
  *)
    echo "Uso: NEMPA_DIR=~/nempa-boltz bash upload.sh [upload|resume|verify|estimate|status]"
    ;;
esac
