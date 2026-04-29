import json
import logging
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from prompt_optimizer import optimize_prompt
from verifier import verify_output

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stderr,
)
logger = logging.getLogger("prompt-buddy")

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


def build_mock_output(intent, output_format="code"):
    fmt_label = {"code": "代码", "json": "JSON", "markdown": "Markdown", "text": "文本"}.get(output_format, "代码")
    return f"# 模拟{fmt_label}输出 for intent: {intent}\nprint('hello world')\n"


PROMPT_INJECTION_PATTERNS = [
    (r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|messages?)", "尝试覆盖之前的指令"),
    (r"(?i)you\s+are\s+now\s+(a\s+)?(DAN|developer\s+mode|jailbreak)", "尝试绕过角色限制"),
    (r"(?i)system\s*prompt\s*(is|:|=)", "疑似泄露或篡改系统提示词"),
    (r"(?i)pretend\s+you\s+are\s+(not|no\s+longer)", "尝试伪装身份"),
    (r"(?i)forget\s+(all\s+)?(your\s+)?(training|instructions?|rules?)", "尝试清除安全约束"),
    (r"(?i)(output|print|show|display|repeat)\s+(your\s+)?(system|base|initial)\s+(prompt|instructions?|message)", "尝试提取系统提示词"),
    (r"(?i)from\s+now\s+on\s+you\s+(are|will|must)", "尝试重新定义行为"),
    (r"(?i)do\s+not\s+(follow|obey|listen)", "尝试禁用安全指令"),
    (r"(?i)you\s+must\s+(always|never)\s+(respond|answer|reply)", "尝试强制行为覆盖"),
]


def check_prompt_injection(user_text):
    """Return (is_safe, risks) — True means safe, risks is a list of descriptions."""
    risks = []
    for pattern, desc in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, user_text):
            risks.append(desc)
    return len(risks) == 0, risks


def normalize_base_url(base_url):
    cleaned = str(base_url or "").strip()
    if not cleaned:
        return DEFAULT_BASE_URL
    return cleaned.rstrip("/")


def call_model_via_api(system_prompt, user_text, settings):
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
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
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

    t_start = time.time()
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

    role = str(data.get("role") or "").strip() or None
    output_format = str(data.get("format") or "code").strip()
    if output_format not in ("code", "json", "markdown", "text"):
        output_format = "code"
    constraints = data.get("constraints", [])
    if constraints is None:
        constraints = []
    if not isinstance(constraints, list):
        return jsonify({"error": "constraints 必须是字符串数组"}), 400
    if any(not isinstance(item, str) for item in constraints):
        return jsonify({"error": "constraints 必须是字符串数组"}), 400
    constraints = [c.strip() for c in constraints if c.strip()]

    examples = [item.strip() for item in examples_raw if item.strip()]
    used_default_examples = False
    if not examples:
        examples = load_default_examples()[:MAX_EXAMPLES]
        used_default_examples = True

    t0 = time.time()
    prompt, system_prompt, user_text, num_examples = optimize_prompt(
        intent, examples, role=role, output_format=output_format, constraints=constraints
    )
    api_enabled = bool(settings.get("apiEnabled"))
    engine = "mock"
    model_name = "mock"
    if api_enabled:
        safe, risks = check_prompt_injection(user_text)
        if not safe:
            logger.warning("Prompt injection detected risks=%s intent_len=%d", risks, len(intent))
            return jsonify({
                "error": "检测到 Prompt 注入风险",
                "risks": risks,
                "prompt": prompt,
            }), 400
        try:
            model_output, model_name = call_model_via_api(system_prompt, user_text, settings)
            engine = "api"
            logger.info("API call succeeded model=%s latency=%.2fs", model_name, time.time() - t0)
        except ValueError as exc:
            logger.warning("API validation error: %s", exc)
            return jsonify({"error": str(exc)}), 400
        except RuntimeError as exc:
            logger.error("API call failed: %s", exc)
            return jsonify({"error": str(exc)}), 502
    else:
        model_output = build_mock_output(intent, output_format)
        logger.info("Mock generation intent_len=%d format=%s examples=%d", len(intent), output_format, num_examples)

    score, issues = verify_output(model_output)
    if issues:
        logger.info("Verification issues=%d score=%d rules=%s", len(issues), score, issues)
    logger.info("Request complete total=%.3fs engine=%s", time.time() - t_start, engine)
    return jsonify({
        "prompt": prompt,
        "system_prompt": system_prompt,
        "user_text": user_text,
        "output": model_output,
        "score": score,
        "issues": issues,
        "meta": {
            "engine": engine,
            "model": model_name,
            "output_format": output_format,
            "used_default_examples": used_default_examples,
            "examples_count": num_examples,
        },
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
