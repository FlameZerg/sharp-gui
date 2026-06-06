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
    if fmt not in ("spz", "ply"):
        fmt = "spz"

    ply_filename = f"{model_id}.ply"
    ply_path = os.path.join(paths.output_folder, ply_filename)

    if not os.path.exists(ply_path):
        return None, {"error": "Model not found"}, 404

    print(f"📦 Exporting {model_id} as {fmt.upper()}...")

    ply_size = os.path.getsize(ply_path)

    if fmt == "spz":
        spz_path = os.path.join(paths.output_folder, f"{model_id}.spz")
        if not os.path.exists(spz_path):
            spz_path = ply_to_spz(ply_path, spz_path)

        with open(spz_path, "rb") as f:
            model_bytes = f.read()

        model_size = len(model_bytes)
        model_data = base64.b64encode(model_bytes).decode("utf-8")
        scene_format = "Spz"
        print(
            f"   PLY: {ply_size / 1024 / 1024:.1f}MB → SPZ: {model_size / 1024 / 1024:.1f}MB "
            f"({100 - model_size * 100 // ply_size}% smaller)"
        )
    else:
        splat_data = ply_to_splat(ply_path)
        model_size = len(splat_data)
        model_data = base64.b64encode(splat_data).decode("utf-8")
        scene_format = "Splat"
        print(
            f"   PLY: {ply_size / 1024 / 1024:.1f}MB → Splat: {model_size / 1024 / 1024:.1f}MB "
            f"({100 - model_size * 100 // ply_size}% smaller)"
        )

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

    three_js_path = _pick_existing_path(three_js_candidates)
    orbit_controls_path = _pick_existing_path(orbit_controls_candidates)
    spark_js_path = _pick_existing_path(spark_js_candidates)

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

    three_data_url = f"data:text/javascript;base64,{three_js_b64}"
    orbit_controls_data_url = f"data:text/javascript;base64,{orbit_controls_b64}"
    spark_data_url = f"data:text/javascript;base64,{spark_js_b64}"

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
