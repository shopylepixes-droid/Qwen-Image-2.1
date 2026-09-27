#!/usr/bin/env bash
# Запуск ComfyUI (порт 8188). Если установка ещё не делалась, сначала сам запустит comfy/setup.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKDIR="${WORKDIR:-/workspace}"
COMFY_DIR="${COMFY_DIR:-$WORKDIR/ComfyUI}"
COMFY_VENV="${COMFY_VENV:-$WORKDIR/comfy-venv}"
export HF_HOME="${HF_HOME:-$WORKDIR/hf_cache}"

if [ ! -x "$COMFY_VENV/bin/python" ] || [ ! -f "$COMFY_DIR/models/diffusion_models/qwen_image_2.1_bf16.safetensors" ]; then
  bash "$SCRIPT_DIR/setup.sh"
fi

printf '\n\033[1;32mComfyUI запускается. Когда появится строка «To see the GUI go to», откройте в RunPod: Connect → HTTP Service [Port 8188]\033[0m\n\n'
cd "$COMFY_DIR"
exec "$COMFY_VENV/bin/python" main.py --listen 0.0.0.0 --port 8188 --output-directory "$WORKDIR/outputs/comfy" "$@"
