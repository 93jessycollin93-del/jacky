#!/usr/bin/env bash
# Sequential Ollama model pulls — one at a time to respect the 980 Pro NVMe
# throttle (heavy concurrent I/O makes it slow down). Smallest first.
set -u
LOG="E:/AI/Jacky/pull_models.log"
MODELS=("nomic-embed-text" "whiterabbitneo" "deepseek-r1:14b" "gpt-oss:20b")

echo "=== Pull run started $(date) ===" | tee -a "$LOG"
for m in "${MODELS[@]}"; do
  echo "" | tee -a "$LOG"
  echo ">>> [$(date +%H:%M:%S)] pulling $m ..." | tee -a "$LOG"
  if ollama pull "$m" >> "$LOG" 2>&1; then
    echo ">>> [$(date +%H:%M:%S)] DONE  $m" | tee -a "$LOG"
  else
    echo ">>> [$(date +%H:%M:%S)] FAILED $m (continuing)" | tee -a "$LOG"
  fi
done
echo "" | tee -a "$LOG"
echo "=== Pull run finished $(date) ===" | tee -a "$LOG"
echo "--- final roster ---" | tee -a "$LOG"
ollama list 2>&1 | tee -a "$LOG"
