def verify_output(output):
    issues = []
    score = 100
    lowered = output.lower()
    if "os.system" in lowered or "subprocess" in lowered:
        issues.append("包含潜在危险的系统/子进程调用")
        score -= 50
    if "eval(" in lowered or "exec(" in lowered:
        issues.append("包含动态执行语句(eval/exec)，存在安全风险")
        score -= 40
    if len(output.strip()) < 10:
        issues.append("输出过短")
        score -= 20
    return max(score, 0), issues
