"""Веб-интерфейс Qwen-Image-2.1: создание картинок по тексту и по референсам (до 10), 1K/2K, прозрачный фон.

Запуск на RunPod:  bash start.sh
Параметры:        python app.py --help
"""

import argparse
import math
import os
import random
import time
from pathlib import Path

# Меньше фрагментации видеопамяти: без этого 2K с 10 референсами на 48 ГБ падает с нехваткой памяти.
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

import gradio as gr  # noqa: E402
import torch  # noqa: E402
from diffusers import QwenImage21Pipeline  # noqa: E402
from PIL import Image, ImageOps  # noqa: E402

MODEL_ID = os.environ.get("MODEL_ID", "Qwen/Qwen-Image-2.1")
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/workspace/outputs"))
MAX_SEED = 2**31 - 1
MAX_REFERENCES = 10

# Веса в bf16: трансформер 13.3 ГБ, текстовый энкодер 16.3 ГБ, VAE 1.3 ГБ, плюс до ~28 ГБ на сам расчёт
# (2K с 10 референсами). Поэтому целиком на видеокарте модель держим только на картах от 70 ГБ,
# на 40–70 ГБ текстовый энкодер живёт в ОЗУ, а на меньших картах по очереди подгружаются все части.
FULL_GPU_MIN_VRAM_GB = 70
TEXT_OFFLOAD_MIN_VRAM_GB = 40

# Рекомендуемые размеры из карточки модели: 2K — её родное разрешение, 1K — те же пропорции около
# 1 мегапикселя, в 4–5 раз быстрее. Стороны кратны 32, как требует модель.
ASPECTS = ["1:1", "4:3", "3:4", "3:2", "2:3", "16:9", "9:16"]
SIZES = {
    "1K": {
        "1:1": (1024, 1024), "4:3": (1152, 864), "3:4": (864, 1152), "3:2": (1216, 832),
        "2:3": (832, 1216), "16:9": (1344, 768), "9:16": (768, 1344),
    },
    "2K": {
        "1:1": (2048, 2048), "4:3": (2400, 1792), "3:4": (1792, 2400), "3:2": (2528, 1696),
        "2:3": (1696, 2528), "16:9": (2752, 1536), "9:16": (1536, 2752),
    },
}
RESOLUTION_SIDE = {"1K": 1024, "2K": 2048}
RESOLUTION_LABELS = {"1K (~1 Мп, быстро)": "1K", "2K (~4 Мп, родное для модели, в ~5 раз дольше)": "2K"}
FOLLOW_LAST, FOLLOW_FIRST = "Как у последней картинки", "Как у первой картинки"

# Каждый референс модель читает в разрешении результата. Чтобы 10 референсов при 2K влезли в 48 ГБ,
# их суммарная площадь ограничена десятью картинками 1024×1024: при 2K один-два референса идут
# в полном 2K, а больше — уменьшаются.
MAX_REFERENCE_PIXELS = 10 * 1024 * 1024

# Формулировка из карточки модели: только с ней модель рисует настоящий прозрачный фон (альфа-канал).
RGBA_PREFIX = "This is an RGBA image with transparency."
RGBA_SUFFIX = "The image has alpha channel and the background is transparent."

EXAMPLES = [
    ["A capybara wearing a wizard hat, oil painting", False],
    ["A cozy coffee shop storefront at night, neon sign that says \"QWEN CAFE\", rain on the street, photo", False],
    ["A cute cartoon fox sticker", True],
    ["Minimalist poster with the text \"Hello, RunPod!\" in bold letters, pastel colors", False],
]

pipe: QwenImage21Pipeline | None = None


def keep_text_encoder_in_ram(text_encoder: torch.nn.Module):
    """Текстовый энкодер лежит в закреплённой (pinned) ОЗУ и заходит на видеокарту только на время чтения запроса.

    Веса не меняются, поэтому обратно их не копируем: после чтения параметры просто снова указывают на копию в ОЗУ,
    а видеопамять освобождается. Загрузка на видеокарту из закреплённой памяти занимает около секунды.
    """
    params = dict(text_encoder.named_parameters())
    buffers = dict(text_encoder.named_buffers())
    in_ram = {name: t.data.pin_memory() for name, t in {**params, **buffers}.items()}

    def point_to(device):
        for name, param in params.items():
            param.data = in_ram[name].to(device, non_blocking=True)
        for name, buf in buffers.items():
            module_name, _, attr = name.rpartition(".")
            text_encoder.get_submodule(module_name)._buffers[attr] = in_ram[name].to(device, non_blocking=True)

    def back_to_ram(*_):
        point_to("cpu")
        torch.cuda.empty_cache()

    point_to("cpu")
    text_encoder.register_forward_pre_hook(lambda *_: point_to("cuda"))
    text_encoder.register_forward_hook(back_to_ram)
    return back_to_ram


release_text_encoder = None


def load_pipeline(offload: str) -> QwenImage21Pipeline:
    global release_text_encoder
    print(f"Загружаю модель {MODEL_ID} (1–3 минуты)...", flush=True)
    pipeline = QwenImage21Pipeline.from_pretrained(MODEL_ID, dtype=torch.bfloat16)
    vram_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
    if offload == "auto":
        if vram_gb >= FULL_GPU_MIN_VRAM_GB:
            offload = "off"
        elif vram_gb >= TEXT_OFFLOAD_MIN_VRAM_GB:
            offload = "text"
        else:
            offload = "on"
    if offload == "on":
        pipeline.enable_model_cpu_offload()
        print(f"Видеопамяти {vram_gb:.0f} ГБ: части модели по очереди подгружаются из ОЗУ.", flush=True)
    elif offload == "text":
        pipeline.transformer.to("cuda")
        pipeline.vae.to("cuda")
        release_text_encoder = keep_text_encoder_in_ram(pipeline.text_encoder)
        print(f"Видеопамяти {vram_gb:.0f} ГБ: текстовый энкодер в ОЗУ, остальное на видеокарте.", flush=True)
    else:
        pipeline.to("cuda")
        print(f"Видеопамяти {vram_gb:.0f} ГБ: модель целиком на видеокарте.", flush=True)
    return pipeline


def with_transparency(prompt: str) -> str:
    if RGBA_PREFIX.lower() in prompt.lower():
        return prompt
    if prompt[-1] not in ".!?":
        prompt += "."
    return f"{RGBA_PREFIX} {prompt} {RGBA_SUFFIX}"


def size_like(image: Image.Image, side: int) -> tuple[int, int]:
    """Размер с пропорциями картинки и площадью side×side, стороны кратны 32."""
    ratio = image.width / image.height
    width = math.sqrt(side * side * ratio)
    return round(width / 32) * 32, round(width / ratio / 32) * 32


@torch.no_grad()
def decode(latents: torch.Tensor, width: int, height: int) -> Image.Image:
    """Декодирует латенты в картинку, как в конце QwenImage21Pipeline, но уже после выхода из пайплайна.

    К этому моменту освобождён кэш референсов (до ~20 ГБ), и 2K помещается в видеопамять целиком. Декодирование
    по частям (vae.enable_tiling) тоже экономит память, но оставляет на 2K заметные швы через каждые 192 пикселя.
    """
    vae = pipe.vae
    latents = pipe._unpack_latents(latents, height, width, pipe.vae_scale_factor).to(vae.dtype)
    mean = torch.tensor(vae.config.latents_mean).view(1, -1, 1, 1, 1).to(latents)
    std = torch.tensor(vae.config.latents_std).view(1, -1, 1, 1, 1).to(latents)
    image = vae.decode(latents * std + mean, return_dict=False)[0][:, :, 0]
    return pipe.image_processor.postprocess(image, output_type="pil")[0]


def run_pipeline(prompt, images, width, height, transparent, seed, randomize_seed, steps, negative_prompt, cfg,
                 progress):
    if not prompt or not prompt.strip():
        raise gr.Error("Напишите запрос (промпт).")
    prompt = with_transparency(prompt.strip()) if transparent else prompt.strip()
    if randomize_seed:
        seed = random.randint(0, MAX_SEED)
    seed, steps = int(seed), int(steps)

    def on_step(_pipe, step, _timestep, callback_kwargs):
        progress((step + 1) / steps, desc=f"Шаг {step + 1} из {steps}")
        return callback_kwargs

    extra = {}
    if cfg > 1:
        # Guidance включается только вместе с negative_prompt; пробел — «пустой» негативный промпт.
        extra = {"true_cfg_scale": cfg, "negative_prompt": negative_prompt.strip() or " "}
    if images:
        # Модель читает каждый референс как квадрат этой стороны по площади (см. MAX_REFERENCE_PIXELS).
        side = min(math.sqrt(width * height), math.sqrt(MAX_REFERENCE_PIXELS / len(images)))
        extra.update(image=images, output_resolution=int(side) // 32 * 32)

    progress(0, desc="Подготовка...")
    try:
        latents = pipe(
            prompt=prompt,
            width=width,
            height=height,
            num_inference_steps=steps,
            generator=torch.Generator("cpu").manual_seed(seed),
            callback_on_step_end=on_step,
            output_type="latent",
            **extra,
        ).images
        result = decode(latents, width, height)
    except torch.OutOfMemoryError:
        result = None
    if result is None:
        # Уже вне except: трассировка ошибки освобождена, и вместе с ней тензоры, которые она держала.
        if release_text_encoder:
            release_text_encoder()
        torch.cuda.empty_cache()
        raise gr.Error("Не хватило видеопамяти. Выберите 1K, выключите CFG или загрузите меньше картинок.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result.save(OUTPUT_DIR / f"{time.strftime('%Y%m%d-%H%M%S')}_seed{seed}.png")
    return result, seed


def text_to_image(prompt, resolution, aspect, transparent, seed, randomize_seed, steps, negative_prompt, cfg,
                  progress=gr.Progress()):
    width, height = SIZES[RESOLUTION_LABELS[resolution]][aspect]
    return run_pipeline(
        prompt, None, width, height, transparent, seed, randomize_seed, steps, negative_prompt, cfg, progress
    )


def load_references(gallery) -> list[Image.Image]:
    # Галерея отдаёт пары (путь к файлу, подпись) в порядке загрузки.
    paths = [item[0] if isinstance(item, (list, tuple)) else item for item in gallery or []]
    if not paths:
        raise gr.Error("Загрузите хотя бы одну картинку.")
    if len(paths) > MAX_REFERENCES:
        raise gr.Error(f"Можно не больше {MAX_REFERENCES} картинок, сейчас {len(paths)}.")
    # exif_transpose поворачивает фото с телефона как надо; режим (и прозрачность PNG) сохраняется.
    return [ImageOps.exif_transpose(Image.open(path)) for path in paths]


def edit_image(prompt, gallery, resolution, aspect, transparent, seed, randomize_seed, steps, negative_prompt, cfg,
               progress=gr.Progress()):
    images = load_references(gallery)
    resolution = RESOLUTION_LABELS[resolution]
    if aspect in (FOLLOW_LAST, FOLLOW_FIRST):
        width, height = size_like(images[-1] if aspect == FOLLOW_LAST else images[0], RESOLUTION_SIDE[resolution])
    else:
        width, height = SIZES[resolution][aspect]
    return run_pipeline(
        prompt, images, width, height, transparent, seed, randomize_seed, steps, negative_prompt, cfg, progress
    )


def output_settings(aspects):
    with gr.Row():
        resolution = gr.Radio(label="Разрешение", choices=list(RESOLUTION_LABELS), value=next(iter(RESOLUTION_LABELS)))
        aspect = gr.Dropdown(label="Пропорции", choices=aspects, value=aspects[0])
    transparent = gr.Checkbox(
        label="Прозрачный фон (PNG с альфа-каналом)",
        info="Добавляет к запросу формулировку, при которой модель рисует прозрачный фон",
    )
    return resolution, aspect, transparent


def advanced_settings():
    with gr.Accordion("Дополнительные настройки", open=False):
        with gr.Row():
            seed = gr.Number(label="Seed (зерно)", value=0, precision=0, minimum=0, maximum=MAX_SEED)
            randomize_seed = gr.Checkbox(label="Случайный seed", value=True)
        steps = gr.Slider(
            label="Шаги (больше — детальнее, но дольше; рекомендуется 40)",
            minimum=10, maximum=60, step=1, value=40,
        )
        cfg = gr.Slider(
            label="CFG (1 = выключено, рекомендуется; >1 — строже следует запросу, но в 2 раза дольше)",
            minimum=1.0, maximum=8.0, step=0.5, value=1.0,
        )
        negative_prompt = gr.Textbox(
            label="Негативный промпт (что НЕ рисовать; работает только при CFG > 1)",
            placeholder="blurry, low quality, watermark",
        )
    return seed, randomize_seed, steps, negative_prompt, cfg


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="Qwen-Image-2.1") as demo:
        gr.Markdown(
            "# Qwen-Image-2.1\n"
            "Запросы можно писать **по-русски**, но в тонких деталях английский (или китайский) надёжнее. "
            "Текст, который должен появиться на картинке, берите в кавычки — кириллицу модель тоже пишет. "
            "Картинки сохраняются в `/workspace/outputs`."
        )

        with gr.Tab("Создать по тексту"):
            with gr.Row():
                with gr.Column():
                    t2i_prompt = gr.Textbox(label="Запрос (промпт)", lines=4, placeholder=EXAMPLES[0][0])
                    t2i_output_settings = output_settings(ASPECTS)
                    t2i_button = gr.Button("Создать", variant="primary")
                    t2i_advanced = advanced_settings()
                    gr.Examples(examples=EXAMPLES, inputs=[t2i_prompt, t2i_output_settings[2]], label="Примеры")
                with gr.Column():
                    t2i_output = gr.Image(label="Результат", type="pil", format="png")
                    t2i_seed_used = gr.Number(label="Использованный seed", interactive=False)

        with gr.Tab("Редактировать / по референсам"):
            with gr.Row():
                with gr.Column():
                    edit_prompt = gr.Textbox(
                        label="Что сделать",
                        lines=4,
                        placeholder="Move it to a snowy mountain top",
                    )
                    gr.Markdown(
                        f"Загрузите от 1 до {MAX_REFERENCES} картинок. Модель читает их **в порядке загрузки**, "
                        "в запросе на них можно ссылаться по номеру: *Put the person from image 1 into the scene "
                        "from image 2* (или `<image1>`, `<image2>`…). Одна картинка — это её редактирование.\n\n"
                        "Вырезать объект с фото: включите «Прозрачный фон» и опишите сам объект, например "
                        "*The cat from image 1, exactly the same, isolated*."
                    )
                    edit_gallery = gr.Gallery(
                        label=f"Картинки-референсы (до {MAX_REFERENCES})",
                        type="filepath",
                        file_types=["image"],
                        interactive=True,
                        columns=5,
                        height="auto",
                    )
                    edit_output_settings = output_settings([FOLLOW_LAST, FOLLOW_FIRST, *ASPECTS])
                    edit_button = gr.Button("Создать", variant="primary")
                    edit_advanced = advanced_settings()
                with gr.Column():
                    edit_output = gr.Image(label="Результат", type="pil", format="png")
                    edit_seed_used = gr.Number(label="Использованный seed", interactive=False)

        # Общий concurrency_id: видеокарта обрабатывает один запрос за раз, остальные ждут в очереди.
        t2i_button.click(
            text_to_image,
            inputs=[t2i_prompt, *t2i_output_settings, *t2i_advanced],
            outputs=[t2i_output, t2i_seed_used],
            concurrency_id="gpu",
            concurrency_limit=1,
        )
        edit_button.click(
            edit_image,
            inputs=[edit_prompt, edit_gallery, *edit_output_settings, *edit_advanced],
            outputs=[edit_output, edit_seed_used],
            concurrency_id="gpu",
            concurrency_limit=1,
        )
    return demo


def main():
    parser = argparse.ArgumentParser(description="Веб-интерфейс Qwen-Image-2.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 7860)))
    parser.add_argument(
        "--share", action="store_true",
        help="создать временную публичную ссылку *.gradio.live (если порт 7860 не открыт в RunPod)",
    )
    parser.add_argument(
        "--offload", choices=["auto", "off", "text", "on"], default=os.environ.get("OFFLOAD", "auto"),
        help="где держать части модели: auto — по объёму видеопамяти; off — всё на видеокарте; "
             "text — текстовый энкодер в ОЗУ; on — все части по очереди подгружаются из ОЗУ",
    )
    args = parser.parse_args()

    global pipe
    pipe = load_pipeline(args.offload)

    password = os.environ.get("APP_PASSWORD")
    auth = (lambda _user, entered: entered == password) if password else None

    print(f"\nГотово! Откройте в RunPod: Connect → HTTP Service [Port {args.port}]\n", flush=True)
    build_ui().queue().launch(server_name="0.0.0.0", server_port=args.port, share=args.share, auth=auth)


if __name__ == "__main__":
    main()
