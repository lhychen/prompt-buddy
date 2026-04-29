# Prompt Buddy

Prompt Buddy 是一个轻量级 AI 提示工程演示项目，提供从输入需求到提示词构建、结果生成与规则校验的完整流程。

## 功能概览

- Web 页面输入 `intent` 与可选 `examples`
- 后端生成标准化 prompt
- 返回模拟代码输出（mock engine）
- 对输出进行风险检测并打分
- 提供默认示例与健康检查接口

## 处理流程

1. 前端提交 `intent` 与 `examples`
2. 后端校验参数
3. 参数缺省时加载默认示例
4. Prompt Optimizer 生成 prompt
5. 生成 mock 输出
6. Verifier 执行规则检测并返回分数与问题列表

## 接口说明

### `GET /healthz`

服务健康检查。

响应示例：

```json
{ "status": "ok" }
```

### `GET /api/examples`

返回默认示例列表（来自 `app/templates/example_prompts.json`）。

响应示例：

```json
{
  "examples": [
    "with open('file.txt') as f:\n    print(len(f.readlines()))"
  ]
}
```

### `POST /generate`

请求头：`Content-Type: application/json`

请求体：

```json
{
  "intent": "读取文件并统计行数",
  "examples": ["with open('file.txt') as f: print(len(f.readlines()))"]
}
```

字段约束：

- `intent`：必填，字符串，最大 500 字符
- `examples`：可选，字符串数组，最多 5 条

成功响应示例：

```json
{
  "prompt": "你是一个友好的代码助理。根据用户意图，生成可运行的 Python 示例。\n用户意图：读取文件并统计行数\n示例：\nwith open('file.txt') as f: print(len(f.readlines()))\n请仅返回代码，不要解释。",
  "output": "# 模拟代码 for intent: 读取文件并统计行数\nprint('hello world')\n",
  "score": 100,
  "issues": [],
  "meta": {
    "engine": "mock",
    "used_default_examples": false,
    "examples_count": 1
  }
}
```

错误响应示例：

```json
{ "error": "intent 不能为空" }
```

## 风险评分规则

`app/verifier.py` 当前规则：

- 包含 `os.system` 或 `subprocess`：扣 50 分
- 包含 `eval(` 或 `exec(`：扣 40 分
- 输出长度过短：扣 20 分
- 最低分为 0

## 项目结构

```text
prompt-buddy/
├─ app/
│  ├─ main.py
│  ├─ prompt_optimizer.py
│  ├─ verifier.py
│  └─ templates/
│     └─ example_prompts.json
├─ web/
│  └─ index.html
├─ requirements.txt
├─ .gitignore
├─ init_repo.ps1
└─ README.md
```

## 本地运行（Windows PowerShell）

```powershell
Set-Location "C:\Users\chen\prompt-buddy"
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python app\main.py
```

访问地址：`http://127.0.0.1:5000`

## PowerShell 调用示例

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:5000/generate" `
  -Method Post `
  -ContentType "application/json" `
  -Body (ConvertTo-Json @{
    intent = "写一个读取文本并统计行数的 Python 示例"
    examples = @("with open('file.txt') as f: print(len(f.readlines()))")
  })
```

## GitHub 推送脚本

```powershell
.\init_repo.ps1 -RemoteUrl "https://github.com/<YOUR_USERNAME>/<YOUR_REPO>.git"
```

脚本执行内容：
- 初始化或复用本地仓库
- 提交当前变更
- 设置或更新 `origin`
- 推送到 `main`
