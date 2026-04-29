import json
import re
from pathlib import Path

_RULES_FILE = Path(__file__).resolve().parent / "rules.json"
_RULES = []


def _load_rules():
    global _RULES
    if _RULES:
        return _RULES
    if not _RULES_FILE.exists():
        return _RULES
    try:
        with _RULES_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return _RULES
    if not isinstance(data, list):
        return _RULES
    for item in data:
        if not isinstance(item, dict):
            continue
        rule = {
            "id": str(item.get("id", "")),
            "pattern": item.get("pattern", ""),
            "description": str(item.get("description", "")),
            "deduction": int(item.get("deduction", 0)),
            "type": str(item.get("type", "pattern")),
            "min_length": int(item.get("min_length", 0)) if item.get("min_length") is not None else None,
            "max_length": int(item.get("max_length", 0)) if item.get("max_length") is not None else None,
        }
        _RULES.append(rule)
    return _RULES


def verify_output(output):
    rules = _load_rules()
    issues = []
    score = 100

    for rule in rules:
        rule_type = rule["type"]
        hit = False

        if rule_type == "length":
            text = output.strip()
            min_len = rule["min_length"]
            max_len = rule["max_length"]
            if min_len is not None and len(text) < min_len:
                hit = True
            elif max_len is not None and len(text) > max_len:
                hit = True
        else:
            pattern = rule["pattern"]
            if pattern:
                try:
                    if re.search(pattern, output):
                        hit = True
                except re.error:
                    continue

        if hit:
            issues.append(rule["description"])
            score -= rule["deduction"]

    return max(score, 0), issues


def reload_rules():
    global _RULES
    _RULES = []
    return _load_rules()
