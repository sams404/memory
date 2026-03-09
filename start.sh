#!/bin/bash
# Запускает всё одной командой
cd "$(dirname "$0")"
source ~/.pipeline_env 2>/dev/null || true

echo "Starting Pipeline Server..."
export VAULT_PATH="${VAULT_PATH:-$HOME/vault}"
python3 server.py
