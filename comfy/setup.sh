#!/usr/bin/env bash
# Установка ComfyUI с моделью Qwen-Image-2.1 в полном качестве (bf16) на под RunPod.
# Запускать один раз:  bash comfy/setup.sh
# Повторный запуск безопасен: уже установленное и скачанное пропускается.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKDIR="${WORKDIR:-/workspace}"
COMFY_DIR="${COMFY_DIR:-$WORKDIR/ComfyUI}"
COMFY_VENV="${COMFY_VENV:-$WORKDIR/comfy-venv}"
# В этой версии ComfyUI уже есть блоки Qwen-Image-2.1. Зафиксирована, чтобы установка не сломалась от обновлений.
COMFY_VERSION="${COMFY_VERSION:-v0.37.4}"
# Помощник для запросов (prompt enhancer, ~20 ГБ). WITH_PE=0 — не скачивать.
WITH_PE="${WITH_PE:-1}"
REPO="Comfy-Org/Qwen-Image-2.1"
export HF_HOME="${HF_HOME:-$WORKDIR/hf_cache}"
export HF_XET_HIGH_PERFORMANCE=1

say()  { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
fail() { printf '\n\033[1;31mОШИБКА: %s\033[0m\n' "$*" >&2; exit 1; }

say "Проверяю сервер"

command -v nvidia-smi >/dev/null 2>&1 \
  || fail "Видеокарта не найдена. Создайте под с GPU (см. README.md, шаг 2)."
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader

command -v git >/dev/null 2>&1 || fail "Не найден git. Используйте шаблон «Runpod Pytorch» (см. README.md)."

python3 - <<'PYEOF' || fail "Нужен Python 3.10+ и PyTorch 2.6+ с CUDA. Выберите шаблон «Runpod Pytorch» версии 2.6 или новее (см. README.md)."
import sys
assert sys.version_info >= (3, 10), f"Python {sys.version.split()[0]} слишком старый"
import torch
major, minor = (int(x) for x in torch.__version__.split("+")[0].split(".")[:2])
assert (major, minor) >= (2, 6), f"PyTorch {torch.__version__} слишком старый"
assert torch.cuda.is_available(), "PyTorch не видит видеокарту"
print(f"Python {sys.version.split()[0]}, PyTorch {torch.__version__}, CUDA {torch.version.cuda}")
PYEOF

mkdir -p "$WORKDIR" "$HF_HOME"
need_gb=$(( WITH_PE == 1 ? 60 : 40 ))
free_gb=$(df -Pk "$WORKDIR" | awk 'NR==2 {print int($4 / 1024 / 1024)}')
echo "Свободно в $WORKDIR: ${free_gb} ГБ"
if [ "$free_gb" -lt "$need_gb" ] && [ ! -f "$COMFY_DIR/models/diffusion_models/qwen_image_2.1_bf16.safetensors" ]; then
  fail "Мало места в $WORKDIR (${free_gb} ГБ), нужно минимум ${need_gb} ГБ свободно. Увеличьте Container Disk (см. README.md, раздел про ComfyUI)."
fi

say "Скачиваю ComfyUI $COMFY_VERSION в $COMFY_DIR"
if [ ! -f "$COMFY_DIR/main.py" ]; then
  git clone --depth 1 --branch "$COMFY_VERSION" https://github.com/comfyanonymous/ComfyUI.git "$COMFY_DIR"
fi

say "Создаю окружение Python в $COMFY_VENV"
# --system-site-packages: берём готовый PyTorch из шаблона, не скачивая его заново.
if [ ! -x "$COMFY_VENV/bin/python" ]; then
  if ! python3 -m venv --system-site-packages "$COMFY_VENV" 2>/dev/null; then
    rm -rf "$COMFY_VENV"
    python3 -m venv --system-site-packages --without-pip "$COMFY_VENV"
  fi
fi
PY="$COMFY_VENV/bin/python"

say "Устанавливаю библиотеки ComfyUI (2–5 минут)"
# Не даём pip заменить PyTorch из шаблона: закрепляем уже установленные версии.
CONSTRAINTS="$COMFY_VENV/torch-constraints.txt"
"$PY" - > "$CONSTRAINTS" <<'PYEOF'
import importlib.metadata as md
for pkg in ("torch", "torchvision", "torchaudio"):
    try:
        print(f"{pkg}=={md.version(pkg).split('+')[0]}")
    except md.PackageNotFoundError:
        pass
PYEOF
"$PY" -m pip install --disable-pip-version-check -r "$COMFY_DIR/requirements.txt" -c "$CONSTRAINTS"

say "Скачиваю Qwen-Image-2.1 в полном качестве bf16 (~32 ГБ$( [ "$WITH_PE" = 1 ] && echo ' + помощник для запросов ~20 ГБ'), обычно 5–20 минут)"
WITH_PE="$WITH_PE" REPO="$REPO" MODELS="$COMFY_DIR/models" "$PY" - <<'PYEOF'
import os
from huggingface_hub import hf_hub_download

files = [
    "diffusion_models/qwen_image_2.1_bf16.safetensors",
    "text_encoders/qwen3vl_8b_bf16.safetensors",
    "vae/qwen_image_2.1_vae_bf16.safetensors",
]
if os.environ["WITH_PE"] == "1":
    # Помощник выпущен только в int8: он пишет текст запроса, на качество картинки это не влияет.
    files += [
        "text_encoders/qwen3.5_9b_qwen_image_2.1_pe_t2i.int8_convrot.safetensors",
        "text_encoders/qwen3.5_9b_qwen_image_2.1_pe_i2i.int8_convrot.safetensors",
    ]
for name in files:
    path = hf_hub_download(os.environ["REPO"], name, local_dir=os.environ["MODELS"])
    print(f"  {name}: {os.path.getsize(path) / 1e9:.1f} ГБ")
PYEOF

say "Готовлю схемы (workflows) для Qwen-Image-2.1"
"$PY" "$SCRIPT_DIR/workflows.py" "$COMFY_DIR"

say "Готово! Теперь запустите:  bash $SCRIPT_DIR/start.sh"
