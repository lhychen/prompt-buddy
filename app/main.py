import json
import os
import sys
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from prompt_optimizer import optimize_prompt
from verifier import verify_output

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
MAX_EXAMPLES = 5


def load_default_examples():
    if not EXAMPLES_FILE.exists():
        return []
    try:
        with EXAMPLES_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    examples = []
    for item in data:
        if not isinstance(item, dict):
            continue
        for example in item.get("examples", []):
            if isinstance(example, str) and example.strip():
                examples.append(example.strip())
    return examples


def build_mock_output(intent):
    return f"# 模拟代码 for intent: {intent}\nprint('hello world')\n"


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

    data = request.get_json(silent=True) or {}
    intent = str(data.get("intent", "")).strip()
    if not intent:
        return jsonify({"error": "intent 不能为空"}), 400
    if len(intent) > MAX_INTENT_LENGTH:
        return jsonify({"error": f"intent 长度不能超过 {MAX_INTENT_LENGTH} 个字符"}), 400

    examples_raw = data.get("examples", [])
    if examples_raw is None:
        examples_raw = []
    if not isinstance(examples_raw, list):
        return jsonify({"error": "examples 必须是字符串数组"}), 400
    if len(examples_raw) > MAX_EXAMPLES:
        return jsonify({"error": f"examples 最多允许 {MAX_EXAMPLES} 条"}), 400
    if any(not isinstance(item, str) for item in examples_raw):
        return jsonify({"error": "examples 必须是字符串数组"}), 400

    examples = [item.strip() for item in examples_raw if item.strip()]
    used_default_examples = False
    if not examples:
        examples = load_default_examples()[:MAX_EXAMPLES]
        used_default_examples = True

    prompt = optimize_prompt(intent, examples)
    model_output = build_mock_output(intent)
    score, issues = verify_output(model_output)
    return jsonify({
        "prompt": prompt,
        "output": model_output,
        "score": score,
        "issues": issues,
        "meta": {
            "engine": "mock",
            "used_default_examples": used_default_examples,
            "examples_count": len(examples),
        },
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
