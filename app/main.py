import json
import logging
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from prompt_optimizer import optimize_prompt

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    RUNTIME_BASE_DIR = Path(sys._MEIPASS)
    WEB_DIR = RUNTIME_BASE_DIR / "web"
    EXAMPLES_FILE = RUNTIME_BASE_DIR / "app" / "templates" / "example_prompts.json"
else:
    BASE_DIR = Path(__file__).resolve().parent
    WEB_DIR = BASE_DIR.parent / "web"
    EXAMPLES_FILE = BASE_DIR / "templates" / "example_prompts.json"


app = Flask(__name__, static_folder=str(WEB_DIR))
MAX_INTENT_LENGTH = 500
MAX_STYLE_LENGTH = 2000
MAX_EXAMPLES = 5

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stderr,
)
logger = logging.getLogger("prompt-buddy")


def load_default_examples():
    """Return list of {label, text} style examples."""
    if not EXAMPLES_FILE.exists():
        return []
    try:
        with EXAMPLES_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []
    result = []
    for item in data:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label", "")).strip()
        text = str(item.get("text", "")).strip()
        if text:
            result.append({"label": label or "示例", "text": text})
    return result


@app.route("/")
def index():
    return send_from_directory(str(WEB_DIR), "index.html")


@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"status": "ok"})


@app.route("/api/examples", methods=["GET"])
def examples():
    return jsonify({"examples": load_default_examples()})


@app.route("/generate", methods=["POST"])
def generate():
    if not request.is_json:
        return jsonify({"error": "请求必须为 application/json"}), 400

    t_start = time.time()
    data = request.get_json(silent=True) or {}

    # ── Validate intent ──
    intent = str(data.get("intent", "")).strip()
    if not intent:
        return jsonify({"error": "intent 不能为空"}), 400
    if len(intent) > MAX_INTENT_LENGTH:
        return jsonify({"error": f"intent 长度不能超过 {MAX_INTENT_LENGTH} 个字符"}), 400

    # ── Validate style_text ──
    style_text = str(data.get("style_text") or "").strip() or None
    if style_text and len(style_text) > MAX_STYLE_LENGTH:
        return jsonify({"error": f"风格参考文本长度不能超过 {MAX_STYLE_LENGTH} 个字符"}), 400

    # ── Accept settings (reserved for future use) ──
    settings = data.get("settings", {})
    if settings is None:
        settings = {}
    if not isinstance(settings, dict):
        return jsonify({"error": "settings 必须是对象"}), 400

    # ── Optimize ──
    prompt, style_features = optimize_prompt(intent, style_text)

    logger.info(
        "Request complete total=%.3fs intent_len=%d style_provided=%d features=%s",
        time.time() - t_start, len(intent), int(bool(style_text)), style_features,
    )

    return jsonify({
        "prompt": prompt,
        "style_features": style_features,
        "meta": {
            "style_provided": bool(style_text),
            "intent_length": len(intent),
            "style_length": len(style_text) if style_text else 0,
        },
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"

    def _open_browser():
        webbrowser.open(f"http://127.0.0.1:{port}")

    threading.Timer(1.0, _open_browser).start()

    print(f"\n  Prompt Buddy v3.0 → http://127.0.0.1:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=debug)
