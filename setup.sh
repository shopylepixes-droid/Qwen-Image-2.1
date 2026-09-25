#!/usr/bin/env bash
# Установка Qwen-Image-2.1 на под RunPod.
# Запускать один раз:  bash setup.sh
# Повторный запуск безопасен: уже установленное и скачанное пропускается.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKDIR="${WORKDIR:-/workspace}"
VENV="${VENV:-$WORKDIR/qwen-venv}"
MODEL_ID="${MODEL_ID:-Qwen/Qwen-Image-2.1}"
export HF_HOME="${HF_HOME:-$WORKDIR/hf_cache}"
export HF_XET_HIGH_PERFORMANCE=1

say()  { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
fail() { printf '\n\033[1;31mОШИБКА: %s\033[0m\n' "$*" >&2; exit 1; }

say "Проверяю сервер"

command -v nvidia-smi >/dev/null 2>&1 \
  || fail "Видеокарта не найдена. Создайте под с GPU (см. README.md, шаг 2)."
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader

command -v git >/dev/null 2>&1 || fail "Не найден git. Используйте шаблон «Runpod Pytorch» (см. README.md)."

python3 - <<'EOF' || fail "Нужен Python 3.10+ и PyTorch 2.6+ с CUDA. Выберите шаблон «Runpod Pytorch» версии 2.6 или новее (см. README.md)."
import sys
assert sys.version_info >= (3, 10), f"Python {sys.version.split()[0]} слишком старый"
import torch
major, minor = (int(x) for x in torch.__version__.split("+")[0].split(".")[:2])
assert (major, minor) >= (2, 6), f"PyTorch {torch.__version__} слишком старый"
assert torch.cuda.is_available(), "PyTorch не видит видеокарту"
print(f"Python {sys.version.split()[0]}, PyTorch {torch.__version__}, CUDA {torch.version.cuda}")
EOF

mkdir -p "$WORKDIR" "$HF_HOME"
free_gb=$(df -Pk "$WORKDIR" | awk 'NR==2 {print int($4 / 1024 / 1024)}')
echo "Свободно в $WORKDIR: ${free_gb} ГБ"
if [ "$free_gb" -lt 45 ] && [ ! -d "$HF_HOME/hub/models--${MODEL_ID//\//--}" ]; then
  fail "Мало места в $WORKDIR (${free_gb} ГБ). Модель весит ~33 ГБ, нужно минимум 45 ГБ свободно. Увеличьте Volume Disk (см. README.md)."
fi

say "Создаю окружение Python в $VENV"
# --system-site-packages: берём готовый PyTorch из шаблона, не скачивая его заново.
# Окружение лежит в /workspace, поэтому переживает остановку пода.
if [ ! -x "$VENV/bin/python" ]; then
  if ! python3 -m venv --system-site-packages "$VENV" 2>/dev/null; then
    rm -rf "$VENV"
    python3 -m venv --system-site-packages --without-pip "$VENV"
  fi
fi
PY="$VENV/bin/python"

say "Устанавливаю библиотеки (2–5 минут)"
"$PY" -m pip install --disable-pip-version-check -r "$SCRIPT_DIR/requirements.txt"

say "Скачиваю модель $MODEL_ID (~33 ГБ, обычно 5–15 минут)"
MODEL_ID="$MODEL_ID" "$PY" - <<'EOF'
import os
from diffusers import QwenImage21Pipeline

path = QwenImage21Pipeline.download(os.environ["MODEL_ID"])
print(f"Модель сохранена в {path}")
EOF

say "Готово! Теперь запустите:  bash $SCRIPT_DIR/start.sh"
