import re

# ── Style detection helpers ──

def _detect_tone(text):
    """Detect tone: academic, casual, technical, neutral."""
    features = []

    # Academic indicators
    academic_words = [
        "研究", "分析", "探讨", "结论", "表明", "综上所述", "基于",
        "therefore", "consequently", "furthermore", "nevertheless",
        "本研究", "本文", "显著", "相关性",
    ]
    ac_count = sum(text.count(w) for w in academic_words)
    avg_sent_len = _avg_sentence_length(text)
    passive_patterns = ["被", "所", "得以", "is made", "are considered", "was conducted"]
    passive_count = sum(text.lower().count(p) for p in passive_patterns)

    if ac_count >= 3 or (avg_sent_len > 25 and passive_count >= 2):
        features.append("学术口吻")
    elif ac_count >= 1 and avg_sent_len > 20:
        features.append("正式论述")

    # Casual indicators
    casual_words = [
        "你", "我", "吧", "啦", "哦", "哈", "嘛", "呀",
        "hey", "yeah", "btw", "cool", "awesome",
        "!", "？", "~",
    ]
    casual_count = sum(text.count(w) for w in casual_words)
    if casual_count >= 4 and avg_sent_len < 15:
        features.append("口语化/友好")

    # Technical indicators
    tech_patterns = [
        r"\b(api|sdk|cli|http|json|yml|xml|sql|css|html)\b",
        r"```", r"##\s", r"\|\s+\|", r"npm\s|pip\s|git\s|docker\s",
        r"\b(function|class|def|import|return|const|let|var)\b",
    ]
    tech_count = sum(len(re.findall(p, text, re.IGNORECASE)) for p in tech_patterns)
    if tech_count >= 3:
        features.append("技术风格")

    if not features:
        features.append("中性叙述")

    return features


def _detect_format(text):
    """Detect format: bullet points, paragraphs, Q&A, dialogue."""
    features = []

    lines = text.strip().split("\n")
    bullet_lines = sum(1 for l in lines if re.match(r"^\s*[-*•#]\s|^\s*\d+[.、)\s]", l))
    if bullet_lines >= 2:
        features.append("分点列举")

    if len(lines) >= 4 and bullet_lines < 2:
        features.append("段落叙述")

    if re.search(r"[问Q][：:].*[答A][：:]", text):
        features.append("问答式")

    has_dialogue = len(re.findall(r"[「""].*[」""]", text))
    if has_dialogue >= 2:
        features.append("对话式")

    if not features:
        features.append("段落叙述")

    return features


def _detect_person(text):
    """Detect person perspective."""
    first = len(re.findall(r"\b[我I我们we我的my我们的our]\b", text))
    third = len(re.findall(r"\b[它他她他们it he she they its his her their]\b", text, re.IGNORECASE))
    if first > third * 2:
        return ["第一人称"]
    elif third > first * 2:
        return ["第三人称"]
    return ["通用视角"]


def _detect_language(text):
    """Detect primary language."""
    cn = len(re.findall(r"[\u4e00-\u9fff]", text))
    en = len(re.findall(r"[a-zA-Z]+", text))
    if cn > en * 3:
        return ["中文"]
    elif en > cn * 3:
        return ["English"]
    return ["中英混合"]


def _avg_sentence_length(text):
    sentences = re.split(r"[。！？.!?\n]", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return 0
    return sum(len(s) for s in sentences) / len(sentences)


def analyze_style(style_text):
    """Analyze a style reference text and return detected features."""
    if not style_text or not str(style_text).strip():
        return []
    text = str(style_text).strip()
    features = []
    features.extend(_detect_tone(text))
    features.extend(_detect_format(text))
    features.extend(_detect_person(text))
    features.extend(_detect_language(text))
    return features


# ── Prompt builder ──

def _style_to_role(features):
    """Map style features to a system role description."""
    tone_role = {
        "学术口吻": "你是一位严谨的学术研究者，使用正式、客观的语言",
        "正式论述": "你是一位专业的论述者，使用正式、有条理的语言",
        "口语化/友好": "你是一位友好的助手，使用亲切、易懂的语言",
        "技术风格": "你是一位资深技术专家，使用准确、专业的技术语言",
        "中性叙述": "你是一位中立的助理，使用简洁明了的语言",
    }
    format_role = {
        "分点列举": "请使用分点或编号的形式组织回答",
        "段落叙述": "请使用自然段落的形式组织回答",
        "问答式": "请以问答形式组织回答",
        "对话式": "请以对话的方式展开回答",
    }
    lang_role = {
        "中文": "请用中文回答",
        "English": "Please respond in English",
        "中英混合": "请根据内容需要灵活使用中英文",
    }

    # Pick best matching tone
    tone_match = None
    for key, val in tone_role.items():
        if key in features:
            tone_match = val
            break

    format_match = None
    for key, val in format_role.items():
        if key in features:
            format_match = val
            break

    lang_match = None
    for key, val in lang_role.items():
        if key in features:
            lang_match = val
            break

    parts = [tone_match] if tone_match else ["你是一个友好的助理"]
    if format_match:
        parts.append(format_match)
    if lang_match:
        parts.append(lang_match)

    return "。".join(parts) + "。"


def _build_default_prompt(intent):
    """Build prompt when no style reference is provided."""
    return (
        f"你是一个友好的助理。请根据以下用户意图提供高质量的回应。\n\n"
        f"用户意图：{intent}\n\n"
        f"请直接给出回答，语言清晰、结构合理。"
    )


def _build_styled_prompt(intent, style_text, features):
    """Build prompt incorporating style reference."""
    role = _style_to_role(features)

    # Truncate style text if too long (keep first 800 chars as reference)
    ref = style_text[:800]
    if len(style_text) > 800:
        ref += "\n..."

    return (
        f"{role}\n\n"
        f"以下是一段参考文本，请模仿其语气、格式和结构风格：\n"
        f"```\n{ref}\n```\n\n"
        f"用户意图：{intent}\n\n"
        f"请根据用户意图，使用与参考文本一致的风格进行回应。不要提及你在模仿风格，直接给出内容。"
    )


def optimize_prompt(intent, style_text=None):
    """Generate an optimized prompt based on intent and optional style reference.

    Args:
        intent: User's task intent (required)
        style_text: Optional style reference text for tone/format matching

    Returns:
        (prompt, style_features) tuple
    """
    sanitized_intent = str(intent).strip()

    if not style_text or not str(style_text).strip():
        features = ["默认风格"]
        prompt = _build_default_prompt(sanitized_intent)
    else:
        text = str(style_text).strip()
        features = analyze_style(text)
        prompt = _build_styled_prompt(sanitized_intent, text, features)

    return prompt, features
