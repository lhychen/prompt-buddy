import json
import os
import sys
import urllib.error
import urllib.request
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
MAX_API_KEY_LENGTH = 300
MAX_MODEL_NAME_LENGTH = 100
DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"


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


def normalize_base_url(base_url):
    cleaned = str(base_url or "").strip()
    if not cleaned:
        return DEFAULT_BASE_URL
    return cleaned.rstrip("/")


def call_model_via_api(prompt, settings):
    api_key = str(settings.get("apiKey", "")).strip()
    if not api_key:
        raise ValueError("已启用 API 接入，但 API 密钥为空")
    if len(api_key) > MAX_API_KEY_LENGTH:
        raise ValueError(f"API 密钥长度不能超过 {MAX_API_KEY_LENGTH} 个字符")

    model = str(settings.get("model", DEFAULT_MODEL)).strip() or DEFAULT_MODEL
    if len(model) > MAX_MODEL_NAME_LENGTH:
        raise ValueError(f"模型名称长度不能超过 {MAX_MODEL_NAME_LENGTH} 个字符")

    base_url = normalize_base_url(settings.get("baseUrl"))
    endpoint = f"{base_url}/chat/completions"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是一个代码助理，只返回可运行代码。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    payload_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=payload_bytes,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            error_body = exc.read().decode("utf-8")
            parsed = json.loads(error_body)
            detail = parsed.get("error", {}).get("message", "")
        except (json.JSONDecodeError, UnicodeDecodeError):
            detail = ""
        message = detail or f"模型接口请求失败（HTTP {exc.code}）"
        raise RuntimeError(message) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("模型接口连接失败，请检查 Base URL 或网络") from exc

    try:
        parsed_body = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError("模型接口返回了无法解析的内容") from exc

    content = (
        parsed_body.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    output = str(content).strip()
    if not output:
        raise RuntimeError("模型返回为空")
    return output, model


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

    settings = data.get("settings", {})
    if settings is None:
        settings = {}
    if not isinstance(settings, dict):
        return jsonify({"error": "settings 必须是对象"}), 400

    examples = [item.strip() for item in examples_raw if item.strip()]
    used_default_examples = False
    if not examples:
        examples = load_default_examples()[:MAX_EXAMPLES]
        used_default_examples = True

    prompt = optimize_prompt(intent, examples)
    api_enabled = bool(settings.get("apiEnabled"))
    engine = "mock"
    model_name = "mock"
    if api_enabled:
        try:
            model_output, model_name = call_model_via_api(prompt, settings)
            engine = "api"
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 502
    else:
        model_output = build_mock_output(intent)

    score, issues = verify_output(model_output)
    return jsonify({
        "prompt": prompt,
        "output": model_output,
        "score": score,
        "issues": issues,
        "meta": {
            "engine": engine,
            "model": model_name,
            "used_default_examples": used_default_examples,
            "examples_count": len(examples),
        },
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
