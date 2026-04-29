def optimize_prompt(intent, examples):
    tmpl = (
        "你是一个友好的代码助理。根据用户意图，生成可运行的 Python 示例。\n"
        "用户意图：{intent}\n\n示例：\n{examples}\n\n请仅返回代码，不要解释。"
    )
    sanitized_intent = str(intent).strip()
    sanitized_examples = [str(item).strip() for item in examples if str(item).strip()][:5]
    ex_text = "\n".join(sanitized_examples) if sanitized_examples else "无"
    prompt = tmpl.format(intent=sanitized_intent, examples=ex_text)
    prompt = "\n".join(line.rstrip() for line in prompt.splitlines() if line.strip())
    return prompt
