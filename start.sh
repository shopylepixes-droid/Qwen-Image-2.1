#!/usr/bin/env bash
# Запуск веб-интерфейса Qwen-Image-2.1.
# Если установка ещё не делалась, сначала сам запустит setup.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKDIR="${WORKDIR:-/workspace}"
VENV="${VENV:-$WORKDIR/qwen-venv}"
export HF_HOME="${HF_HOME:-$WORKDIR/hf_cache}"
export OUTPUT_DIR="${OUTPUT_DIR:-$WORKDIR/outputs}"

if [ ! -x "$VENV/bin/python" ] || ! "$VENV/bin/python" -c "import diffusers, gradio" 2>/dev/null; then
  bash "$SCRIPT_DIR/setup.sh"
fi

exec "$VENV/bin/python" "$SCRIPT_DIR/app.py" "$@"
