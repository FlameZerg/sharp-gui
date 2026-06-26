import base64
import os

from backend import runtime
from backend.services.model_convert import ply_to_splat, ply_to_spz


def _pick_existing_path(candidates):
    for path in candidates:
        if os.path.exists(path):
            return path
    raise FileNotFoundError(f"No available asset found in candidates: {candidates}")


def build_export_html(paths, model_id, fmt):
    """构建独立 HTML 导出内容和元信息。"""
    if fmt not in ("spz", "ply", "splat", "rad"):
        fmt = "spz"

    # 提取 base_id 和传入后缀
    if model_id.endswith((".ply", ".spz", ".splat", ".rad")):
        base_id = os.path.splitext(model_id)[0]
        model_ext = os.path.splitext(model_id)[1].lower()
    else:
        base_id = model_id
        model_ext = None

    ply_path = os.path.join(paths.output_folder, f"{base_id}.ply")
    spz_path = os.path.join(paths.output_folder, f"{base_id}.spz")
    splat_path = os.path.join(paths.output_folder, f"{base_id}.splat")
    rad_path = os.path.join(paths.output_folder, f"{base_id}.rad")

    ply_exists = os.path.exists(ply_path)
    spz_exists = os.path.exists(spz_path)
    splat_exists = os.path.exists(splat_path)
    rad_exists = os.path.exists(rad_path)

    # 预设 ply_size 大小：如果 ply 存在则使用其大小，否则以 spz 大小作为原始模型规格
    ply_size = os.path.getsize(ply_path) if ply_exists else (os.path.getsize(spz_path) if spz_exists else 0)

    # 1. 确定最终使用的文件路径和对应的格式标识
    target_path = None
    scene_format = None
    is_ply_convert_to_splat = False

    if model_ext == ".splat" and splat_exists:
        target_path = splat_path
        scene_format = "Splat"
    elif model_ext == ".rad" and rad_exists:
        target_path = rad_path
        scene_format = "Rad"
    elif model_ext == ".spz" and spz_exists:
        target_path = spz_path
        scene_format = "Spz"
    elif model_ext == ".ply" and ply_exists:
        if fmt == "spz":
            if not spz_exists:
                spz_path = ply_to_spz(ply_path, spz_path)
            target_path = spz_path
            scene_format = "Spz"
        else:
            is_ply_convert_to_splat = True
    else:
        # 如果未指定后缀，根据当前存在的文件和 fmt 参数自动回退
        if fmt == "spz":
            if spz_exists:
                target_path = spz_path
                scene_format = "Spz"
            elif ply_exists:
                spz_path = ply_to_spz(ply_path, spz_path)
                target_path = spz_path
                scene_format = "Spz"
            elif splat_exists:
                target_path = splat_path
                scene_format = "Splat"
            elif rad_exists:
                target_path = rad_path
                scene_format = "Rad"
        else:
            if splat_exists:
                target_path = splat_path
                scene_format = "Splat"
            elif ply_exists:
                is_ply_convert_to_splat = True
            elif spz_exists:
                target_path = spz_path
                scene_format = "Spz"
            elif rad_exists:
                target_path = rad_path
                scene_format = "Rad"

    if not target_path and not is_ply_convert_to_splat:
        return None, {"error": "Model not found"}, 404

    print(f"📦 Exporting {model_id}...")

    # 2. 读取模型数据并进行 Base64 编码
    if is_ply_convert_to_splat:
        splat_data = ply_to_splat(ply_path)
        model_size = len(splat_data)
        model_data = base64.b64encode(splat_data).decode("utf-8")
        scene_format = "Splat"
        if not ply_size:
            ply_size = len(splat_data)
        print(f"   PLY: {ply_size / 1024 / 1024:.1f}MB → Splat: {model_size / 1024 / 1024:.1f}MB")
    else:
        with open(target_path, "rb") as f:
            model_bytes = f.read()
        model_size = len(model_bytes)
        model_data = base64.b64encode(model_bytes).decode("utf-8")
        if not ply_size:
            ply_size = model_size
        print(f"   Model Size: {model_size / 1024 / 1024:.1f}MB, Format: {scene_format}")

    three_js_candidates = [
        os.path.join(runtime.BASE_DIR, "frontend", "node_modules", "three", "build", "three.module.js"),
        os.path.join(runtime.BASE_DIR, "static", "lib", "three.module.js"),
    ]
    orbit_controls_candidates = [
        os.path.join(
            runtime.BASE_DIR,
            "frontend",
            "node_modules",
            "three",
            "examples",
            "jsm",
            "controls",
            "OrbitControls.js",
        ),
    ]
    spark_js_candidates = [
        os.path.join(
            runtime.BASE_DIR,
            "frontend",
            "node_modules",
            "@sparkjsdev",
            "spark",
            "dist",
            "spark.module.js",
        ),
    ]
    pass_js_candidates = [
        os.path.join(
            runtime.BASE_DIR,
            "frontend",
            "node_modules",
            "three",
            "examples",
            "jsm",
            "postprocessing",
            "Pass.js",
        ),
    ]

    three_js_path = _pick_existing_path(three_js_candidates)
    orbit_controls_path = _pick_existing_path(orbit_controls_candidates)
    spark_js_path = _pick_existing_path(spark_js_candidates)
    pass_js_path = _pick_existing_path(pass_js_candidates)

    with open(three_js_path, "r", encoding="utf-8") as f:
        three_module_text = f.read()

    three_core_path = os.path.join(os.path.dirname(three_js_path), "three.core.js")
    three_core_data_url = "data:text/javascript,export%20{};"
    if os.path.exists(three_core_path):
        with open(three_core_path, "rb") as f:
            three_core_b64 = base64.b64encode(f.read()).decode("utf-8")
        three_core_data_url = f"data:text/javascript;base64,{three_core_b64}"
        three_module_text = three_module_text.replace("'./three.core.js'", "'three-core'")
        three_module_text = three_module_text.replace('"./three.core.js"', '"three-core"')

    three_js_b64 = base64.b64encode(three_module_text.encode("utf-8")).decode("utf-8")
    with open(orbit_controls_path, "rb") as f:
        orbit_controls_b64 = base64.b64encode(f.read()).decode("utf-8")
    with open(spark_js_path, "rb") as f:
        spark_js_b64 = base64.b64encode(f.read()).decode("utf-8")
    # 编码 Pass.js 为 Base64 Data URL 以注入单文件 HTML
    with open(pass_js_path, "rb") as f:
        pass_js_b64 = base64.b64encode(f.read()).decode("utf-8")

    three_data_url = f"data:text/javascript;base64,{three_js_b64}"
    orbit_controls_data_url = f"data:text/javascript;base64,{orbit_controls_b64}"
    spark_data_url = f"data:text/javascript;base64,{spark_js_b64}"
    pass_data_url = f"data:text/javascript;base64,{pass_js_b64}"

    template_path = os.path.join(runtime.BASE_DIR, "templates", "share_template.html")
    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    html_content = template.replace("{{MODEL_DATA}}", model_data)
    html_content = html_content.replace("{{MODEL_NAME}}", model_id)
    html_content = html_content.replace("{{SCENE_FORMAT}}", scene_format)
    html_content = html_content.replace("{{THREE_DATA_URL}}", three_data_url)
    html_content = html_content.replace("{{THREE_CORE_DATA_URL}}", three_core_data_url)
    html_content = html_content.replace("{{ORBIT_CONTROLS_DATA_URL}}", orbit_controls_data_url)
    html_content = html_content.replace("{{SPARK_DATA_URL}}", spark_data_url)
    html_content = html_content.replace("{{PASS_DATA_URL}}", pass_data_url)

    html_size = len(html_content.encode("utf-8"))
    print(
        f"   ✅ 导出完成: {ply_size / 1024 / 1024:.1f}MB → {html_size / 1024 / 1024:.1f}MB "
        f"(原始 HTML 约 {100 * ply_size // html_size}% 大小)"
    )

    return {
        "html": html_content,
        "format": fmt,
        "model_size": model_size,
        "html_size": html_size,
    }, None, 200
