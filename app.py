"""Веб-интерфейс Qwen-Image-2.1: создание картинок по тексту и редактирование картинок.

Запуск на RunPod:  bash start.sh
Параметры:        python app.py --help
"""

import argparse
import os
import random
import time
from pathlib import Path

import gradio as gr
import torch
from diffusers import QwenImage21Pipeline

MODEL_ID = os.environ.get("MODEL_ID", "Qwen/Qwen-Image-2.1")
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/workspace/outputs"))
MAX_SEED = 2**31 - 1
# Вся модель в bf16 занимает ~33 ГБ видеопамяти. На картах меньше этого части модели
# по очереди подгружаются из оперативной памяти: медленнее, но помещается даже в 24 ГБ.
FULL_GPU_MIN_VRAM_GB = 40

# Около 1 мегапикселя; стороны кратны 32, как требует модель.
SIZES = {
    "1:1 — 1024×1024": (1024, 1024),
    "3:4 — 864×1152": (864, 1152),
    "4:3 — 1152×864": (1152, 864),
    "2:3 — 832×1216": (832, 1216),
    "3:2 — 1216×832": (1216, 832),
    "9:16 — 768×1344": (768, 1344),
    "16:9 — 1344×768": (1344, 768),
    "1:1 — 2048×2048 (в 4+ раза медленнее)": (2048, 2048),
}

EXAMPLES = [
    "A capybara wearing a wizard hat, oil painting",
    "A cozy coffee shop storefront at night, neon sign that says \"QWEN CAFE\", rain on the street, photo",
    "A cute cartoon fox sticker, transparent background",
    "Minimalist poster with the text \"Hello, RunPod!\" in bold letters, pastel colors",
]

pipe: QwenImage21Pipeline | None = None


def load_pipeline(offload: str) -> QwenImage21Pipeline:
    print(f"Загружаю модель {MODEL_ID} (1–3 минуты)...", flush=True)
    pipeline = QwenImage21Pipeline.from_pretrained(MODEL_ID, dtype=torch.bfloat16)
    vram_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
    if offload == "auto":
        offload = "on" if vram_gb < FULL_GPU_MIN_VRAM_GB else "off"
    if offload == "on":
        pipeline.enable_model_cpu_offload()
        print(f"Видеопамяти {vram_gb:.0f} ГБ: включена подгрузка частей модели из ОЗУ.", flush=True)
    else:
        pipeline.to("cuda")
        print(f"Видеопамяти {vram_gb:.0f} ГБ: модель целиком на видеокарте.", flush=True)
    return pipeline


def run_pipeline(prompt, image, seed, randomize_seed, steps, negative_prompt, cfg, progress, **size):
    if not prompt or not prompt.strip():
        raise gr.Error("Напишите запрос (промпт).")
    if randomize_seed:
        seed = random.randint(0, MAX_SEED)
    seed, steps = int(seed), int(steps)

    def on_step(_pipe, step, _timestep, callback_kwargs):
        progress((step + 1) / steps, desc=f"Шаг {step + 1} из {steps}")
        return callback_kwargs

    guidance = {}
    if cfg > 1:
        # Guidance включается только вместе с negative_prompt; пробел — «пустой» негативный промпт.
        guidance = {"true_cfg_scale": cfg, "negative_prompt": negative_prompt.strip() or " "}

    progress(0, desc="Подготовка...")
    result = pipe(
        prompt=prompt.strip(),
        image=image,
        num_inference_steps=steps,
        generator=torch.Generator("cpu").manual_seed(seed),
        callback_on_step_end=on_step,
        **guidance,
        **size,
    ).images[0]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result.save(OUTPUT_DIR / f"{time.strftime('%Y%m%d-%H%M%S')}_seed{seed}.png")
    return result, seed


def text_to_image(prompt, size_label, seed, randomize_seed, steps, negative_prompt, cfg, progress=gr.Progress()):
    width, height = SIZES[size_label]
    return run_pipeline(
        prompt, None, seed, randomize_seed, steps, negative_prompt, cfg, progress, width=width, height=height
    )


def edit_image(
    prompt, image1, image2, image3, resolution, seed, randomize_seed, steps, negative_prompt, cfg,
    progress=gr.Progress(),
):
    images = [img for img in (image1, image2, image3) if img is not None]
    if not images:
        raise gr.Error("Загрузите хотя бы одну картинку.")
    return run_pipeline(
        prompt, images, seed, randomize_seed, steps, negative_prompt, cfg, progress,
        output_resolution=int(resolution),
    )


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
            "Запросы лучше писать **на английском** (или китайском). Текст, который должен появиться "
            "на картинке, берите в кавычки. Картинки сохраняются в `/workspace/outputs`."
        )

        with gr.Tab("Создать по тексту"):
            with gr.Row():
                with gr.Column():
                    t2i_prompt = gr.Textbox(label="Запрос (промпт)", lines=4, placeholder=EXAMPLES[0])
                    t2i_size = gr.Dropdown(label="Размер", choices=list(SIZES), value=next(iter(SIZES)))
                    t2i_button = gr.Button("Создать", variant="primary")
                    t2i_advanced = advanced_settings()
                    gr.Examples(examples=EXAMPLES, inputs=t2i_prompt, label="Примеры")
                with gr.Column():
                    t2i_output = gr.Image(label="Результат", type="pil", format="png")
                    t2i_seed_used = gr.Number(label="Использованный seed", interactive=False)

        with gr.Tab("Редактировать картинку"):
            with gr.Row():
                with gr.Column():
                    edit_prompt = gr.Textbox(
                        label="Что изменить",
                        lines=4,
                        placeholder="Move it to a snowy mountain top",
                    )
                    gr.Markdown(
                        "Можно загрузить до трёх картинок — модель читает их по порядку "
                        "(например: *Put the flowers from the first image into the second scene*). "
                        "Пропорции результата берутся с **последней** загруженной картинки."
                    )
                    with gr.Row():
                        # image_mode=None сохраняет прозрачность (альфа-канал) загруженных PNG.
                        edit_images = [
                            gr.Image(label=f"Картинка {i}", type="pil", image_mode=None) for i in (1, 2, 3)
                        ]
                    edit_resolution = gr.Slider(
                        label="Разрешение результата (сторона квадрата той же площади)",
                        minimum=512, maximum=2048, step=32, value=1024,
                    )
                    edit_button = gr.Button("Изменить", variant="primary")
                    edit_advanced = advanced_settings()
                with gr.Column():
                    edit_output = gr.Image(label="Результат", type="pil", format="png")
                    edit_seed_used = gr.Number(label="Использованный seed", interactive=False)

        # Общий concurrency_id: видеокарта обрабатывает один запрос за раз, остальные ждут в очереди.
        t2i_button.click(
            text_to_image,
            inputs=[t2i_prompt, t2i_size, *t2i_advanced],
            outputs=[t2i_output, t2i_seed_used],
            concurrency_id="gpu",
            concurrency_limit=1,
        )
        edit_button.click(
            edit_image,
            inputs=[edit_prompt, *edit_images, edit_resolution, *edit_advanced],
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
        "--offload", choices=["auto", "on", "off"], default=os.environ.get("OFFLOAD", "auto"),
        help="подгрузка частей модели из ОЗУ: auto — включить, если видеопамяти меньше 40 ГБ",
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
