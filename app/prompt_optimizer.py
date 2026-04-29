def optimize_prompt(intent, examples, role=None, output_format="code", constraints=None):
    """Build a structured prompt with optional role, format, and constraints.

    Args:
        intent: User's intent description (required)
        examples: List of example code strings (max 5 used)
        role: Custom system role; defaults vary by format
        output_format: "code" | "json" | "markdown" | "text"
        constraints: Optional list of extra constraint strings
    """
    sanitized_intent = str(intent).strip()
    sanitized_examples = [str(item).strip() for item in examples if str(item).strip()][:5]
    output_format = output_format if output_format in ("code", "json", "markdown", "text") else "code"
    constraints = constraints if isinstance(constraints, list) else []

    # ── Default role per format ──
    default_roles = {
        "code": "你是一个友好的代码助理。根据用户意图，生成可运行的 Python 示例。",
        "json": "你是一个数据工程师。根据用户意图，输出严格的 JSON 格式数据，不要附带解释。",
        "markdown": "你是一个技术文档专家。根据用户意图，输出格式良好的 Markdown 文档。",
        "text": "你是一个精通技术沟通的助理。根据用户意图，用清晰的中文或英文给出解答。",
    }
    role_text = str(role).strip() if role else default_roles[output_format]

    # ── Format instructions ──
    format_instructions = {
        "code": "请仅返回可运行的代码，不要解释。",
        "json": "请仅返回合法的 JSON，不要包含注释或额外文字。",
        "markdown": "请使用标准的 Markdown 语法返回内容，可包含代码块。",
        "text": "请直接给出答案，不要多余的开场白。",
    }
    format_line = format_instructions.get(output_format, "")

    # ── Examples block ──
    num_examples = len(sanitized_examples)
    if num_examples == 0:
        examples_block = ""
        shot_hint = "请根据你的知识直接生成，无需参考示例。"
    else:
        ex_text = "\n".join(sanitized_examples)
        examples_block = f"示例：\n{ex_text}"
        shot_hint = "请参考以上示例的风格和结构进行生成。" if num_examples <= 2 else "请综合以上多个示例的模式进行生成。"

    # ── Extra constraints ──
    constraints_block = ""
    if constraints:
        constraints_block = "额外约束：\n" + "\n".join(f"- {c}" for c in constraints)

    # ── Assemble ──
    parts = [role_text]
    if examples_block:
        parts.append(examples_block)
    parts.append(shot_hint)
    parts.append(format_line)
    if constraints_block:
        parts.append(constraints_block)

    # ═══ System message (for API consumption) ═══
    system = role_text

    # ═══ User message ═══
    user_parts = [f"用户意图：{sanitized_intent}"]
    if examples_block:
        user_parts.append(examples_block)
    if constraints_block:
        user_parts.append(constraints_block)

    prompt = "\n\n".join(parts)
    user_text = "\n".join(user_parts)

    return prompt, system, user_text, num_examples
