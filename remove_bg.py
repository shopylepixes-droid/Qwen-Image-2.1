"""Удаление фона у всех картинок в папке: прозрачные PNG того же размера и zip-архив с ними.

Запуск на RunPod:  /workspace/qwen-venv/bin/python /workspace/Qwen-Image-2.1/remove_bg.py
По умолчанию берёт картинки из /workspace/bg_input и кладёт результат в /workspace/bg_output и bg_output.zip.
Свои папки:       ... remove_bg.py ПАПКА_С_КАРТИНКАМИ ПАПКА_ДЛЯ_РЕЗУЛЬТАТА

Работает отдельная модель BiRefNet_HR (лицензия MIT): она не перерисовывает картинку, как Qwen, а только
делает фон прозрачным, поэтому пиксели и разрешение исходника сохраняются. Около секунды на картинку.
"""

import sys
import time
import zipfile
from pathlib import Path

import torch
from PIL import Image, ImageOps
from torchvision import transforms
from transformers import AutoModelForImageSegmentation

IN_DIR = Path(sys.argv[1] if len(sys.argv) > 1 else "/workspace/bg_input")
OUT_DIR = Path(sys.argv[2] if len(sys.argv) > 2 else "/workspace/bg_output")
EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}

# Версия для высокого разрешения: маска считается на 2048×2048, края на 2K-картинках аккуратнее.
model = AutoModelForImageSegmentation.from_pretrained("ZhengPeng7/BiRefNet_HR", trust_remote_code=True)
model.to("cuda").eval().half()
prepare = transforms.Compose([
    transforms.Resize((2048, 2048)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])

OUT_DIR.mkdir(parents=True, exist_ok=True)
files = sorted(p for p in IN_DIR.rglob("*") if p.suffix.lower() in EXTS)
print(f"Картинок: {len(files)}", flush=True)
done = []
for path in files:
    start = time.time()
    try:
        image = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    except Exception as error:  # noqa: BLE001 — битый файл не должен останавливать всю пачку
        print(f"ПРОПУСК {path.name}: {error}", flush=True)
        continue
    with torch.no_grad():
        mask = model(prepare(image).unsqueeze(0).to("cuda").half())[-1].sigmoid().float().cpu()[0, 0]
    image.putalpha(transforms.functional.to_pil_image(mask).resize(image.size, Image.LANCZOS))
    out = OUT_DIR / path.relative_to(IN_DIR).with_suffix(".png")
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out)
    done.append(out)
    print(f"{path.name} -> {out.name}  {image.width}×{image.height}  {time.time() - start:.1f} с", flush=True)

zip_path = OUT_DIR.with_suffix(".zip")
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
    for out in done:
        archive.write(out, out.relative_to(OUT_DIR))
print(f"Готово: {len(done)} картинок, архив {zip_path}", flush=True)
