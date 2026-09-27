"""Готовит схемы ComfyUI для Qwen-Image-2.1 и кладёт их в ComfyUI/user/default/workflows.

Берёт официальные шаблоны Comfy и меняет в них: модель и текстовую часть на bf16 (полное качество),
40 шагов, размер 2K. Прозрачность картинок-образцов сохраняется (обычный LoadImage её отбрасывает).
Плюс две схемы для персонажей с нашими проверенными запросами.

Запуск:  python comfy/workflows.py /workspace/ComfyUI
"""
import copy
import importlib.metadata
import json
import sys
import urllib.request
from pathlib import Path

# Свежие официальные шаблоны уже с помощником для запросов; коммит зафиксирован, чтобы правки ниже не разъехались.
TEMPLATE_URL = ("https://raw.githubusercontent.com/Comfy-Org/workflow_templates/"
                "9b912856b25a8564632b20857aa6353fbf78eb5a/templates/{}.json")
BF16 = {
    "qwen_image_2.1_int8_convrot.safetensors": "qwen_image_2.1_bf16.safetensors",
    "qwen3vl_8b_int8_convrot.safetensors": "qwen3vl_8b_bf16.safetensors",
}
STEPS = 40
SIDE = 2048  # картинки-образцы приводятся к ~2048×2048 по площади, результат того же размера (2K)
RGBA = ("This is an RGBA format image with transparency. {} The image has an alpha channel and a transparent "
        "background.")
NEW_POSE = ("Draw the character from image 1 in a completely new pose: [опишите позу по-английски]. Change the pose "
            "and body position, but keep the same face, hair, outfit, colors and soft watercolor illustration style. "
            "Give the character a clearly different facial expression than in image 1: [весёлое или праздничное "
            "выражение]. Full body, a single isolated character, no other objects.")
RED_CIRCLE = ("Fix only the area inside the red circle: [что исправить]. Remove the red circle. Keep everything else in "
              "image 1 exactly the same: the same character, pose, face, expression, colors, soft watercolor "
              "illustration style and composition.")
NOT_WIDGETS = {"IMAGE", "MASK", "LATENT", "CONDITIONING", "MODEL", "CLIP", "VAE"}


def load_template(name):
    """Шаблон с GitHub, а без интернета — из пакета comfyui-workflow-templates (там он без помощника)."""
    try:
        with urllib.request.urlopen(TEMPLATE_URL.format(name), timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except OSError as err:
        print(f"  Не скачался шаблон {name} ({err}), беру встроенный в ComfyUI")
    for dist in importlib.metadata.distributions():
        if not (dist.metadata["Name"] or "").lower().replace("_", "-").startswith("comfyui-workflow-templates"):
            continue
        for file in dist.files or []:
            if file.name == f"{name}.json":
                return json.loads(file.locate().read_text(encoding="utf-8"))
    raise SystemExit(f"Не нашёлся шаблон {name}")


def to_bf16(workflow):
    text = json.dumps(workflow, ensure_ascii=False)
    for old, new in BF16.items():
        text = text.replace(old, new)
    return json.loads(text)


def main_node(workflow):
    """Узел-подграф с настройками (промпт, шаги, модели) и описание его входов."""
    subgraphs = {sg["id"]: sg for sg in workflow["definitions"]["subgraphs"]}
    for node in workflow["nodes"]:
        if node["type"] in subgraphs:
            return node, subgraphs[node["type"]]
    raise SystemExit("В шаблоне не нашёлся подграф Qwen-Image-2.1: формат шаблона изменился")


def set_widgets(workflow, **values):
    node, subgraph = main_node(workflow)
    names = [i["name"] for i in subgraph["inputs"] if i["type"] not in NOT_WIDGETS]
    widgets = node["widgets_values"]
    if len(names) != len(widgets) or widgets[names.index("unet_name")] != BF16[next(iter(BF16))]:
        raise SystemExit("Не совпали настройки шаблона: формат шаблона изменился, обновите comfy/workflows.py")
    for name, value in values.items():
        if name in names:
            widgets[names.index(name)] = value
        elif name != "switch_1":  # переключателя помощника нет только во встроенных шаблонах
            raise SystemExit(f"В шаблоне нет настройки {name}: формат шаблона изменился")


def keep_alpha(workflow, load_id):
    """Вставляет JoinImageWithAlpha после LoadImage, чтобы модель видела прозрачность образца."""
    nodes = {n["id"]: n for n in workflow["nodes"]}
    load = nodes[load_id]
    main, _ = main_node(workflow)
    link = next(l for l in workflow["links"] if l[1] == load_id and l[3] == main["id"])
    join_id = workflow["last_node_id"] + 1
    img_link, mask_link = workflow["last_link_id"] + 1, workflow["last_link_id"] + 2
    workflow["last_node_id"], workflow["last_link_id"] = join_id, mask_link

    link[1], link[2] = join_id, 0  # подграф теперь получает картинку с альфой
    load["outputs"][0]["links"] = [l for l in load["outputs"][0]["links"] if l != link[0]] + [img_link]
    load["outputs"][1]["links"] = [mask_link]
    workflow["links"] += [[img_link, load_id, 0, join_id, 0, "IMAGE"], [mask_link, load_id, 1, join_id, 1, "MASK"]]
    workflow["nodes"].append({
        "id": join_id, "type": "JoinImageWithAlpha",
        "pos": [load["pos"][0] + 20, load["pos"][1] - 110], "size": [270, 46], "flags": {}, "order": 1, "mode": 0,
        "inputs": [{"name": "image", "type": "IMAGE", "link": img_link},
                   {"name": "alpha", "type": "MASK", "link": mask_link}],
        "outputs": [{"name": "IMAGE", "type": "IMAGE", "links": [link[0]]}],
        "properties": {"Node name for S&R": "JoinImageWithAlpha"}, "widgets_values": [],
    })


def drop_node(workflow, node_id):
    """Убирает узел и все его связи (второй пример-образец из официального шаблона)."""
    gone = {l[0] for l in workflow["links"] if node_id in (l[1], l[3])}
    workflow["links"] = [l for l in workflow["links"] if l[0] not in gone]
    workflow["nodes"] = [n for n in workflow["nodes"] if n["id"] != node_id]
    for node in workflow["nodes"]:
        for inp in node.get("inputs", []):
            if inp.get("link") in gone:
                inp["link"] = None
        for out in node.get("outputs", []):
            out["links"] = [l for l in out.get("links") or [] if l not in gone]


def edit_workflow(prompt=None, use_pe=None, single=False):
    """Редактирование по картинкам: bf16, 2K, 40 шагов, прозрачность образцов сохраняется.

    single=True оставляет одну картинку-образец вместо двух из официального примера.
    """
    workflow = to_bf16(load_template("image_qwen_image_2_1_image_edit"))
    values = {"resolution": SIDE, "steps": STEPS}
    if prompt is not None:
        values["prompt"] = prompt
    if use_pe is not None:
        values["switch_1"] = use_pe
    set_widgets(workflow, **values)
    loads = sorted(n["id"] for n in workflow["nodes"] if n["type"] == "LoadImage")
    if single:
        for extra in loads[1:]:
            drop_node(workflow, extra)
        loads = loads[:1]
    for load_id in loads:
        keep_alpha(workflow, load_id)
    return workflow


def use_example_image(workflow):
    """Вместо картинок из примеров Comfy (их нет на сервере) — example.png, который есть в любом ComfyUI."""
    for node in workflow["nodes"]:
        if node["type"] == "LoadImage":
            node["widgets_values"][0] = "example.png"


def build():
    t2i = to_bf16(load_template("image_qwen_image_2_1_t2i"))
    set_widgets(t2i, steps=STEPS)
    for node in t2i["nodes"]:
        if node["type"] == "ResolutionSelector":
            node["widgets_values"][1:3] = [4.0, 32]  # 4 мегапикселя = 2K, стороны кратны 32

    background = to_bf16(load_template("image_qwen_image_2_1_background_removal"))
    set_widgets(background, resolution=SIDE, steps=STEPS)

    edit = edit_workflow()

    # Для персонажей помощник выключен: он описывает героя своими словами («a blue lizard») и ломает сходство.
    pose = edit_workflow(RGBA.format(NEW_POSE), use_pe=False, single=True)
    fix = copy.deepcopy(pose)
    set_widgets(fix, prompt=RGBA.format(RED_CIRCLE))

    for workflow in (background, edit, pose, fix):
        use_example_image(workflow)
    return {
        "Qwen 2.1 — картинка по тексту (2K)": t2i,
        "Qwen 2.1 — редактирование (2K)": edit,
        "Qwen 2.1 — удалить фон (2K)": background,
        "Персонаж — новая поза (прозрачный фон)": pose,
        "Персонаж — правка по красному кругу": fix,
    }


if __name__ == "__main__":
    out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "/workspace/ComfyUI") / "user" / "default" / "workflows"
    out_dir.mkdir(parents=True, exist_ok=True)
    for title, workflow in build().items():
        (out_dir / f"{title}.json").write_text(json.dumps(workflow, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  {title}")
