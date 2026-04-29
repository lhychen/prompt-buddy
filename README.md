# Prompt Buddy

Prompt Buddy 是一个轻量级 AI 提示工程演示项目，提供从输入需求到提示词构建、结果生成与风险校验的完整流程。支持 Mock 模拟和 OpenAI 兼容 API 双模式。

## 功能概览

- Web 页面输入 `intent`、可选 `examples`、输出 `format`
- 后端生成结构化 prompt（支持 System/User 分离）
- 双引擎：Mock 模拟输出 / OpenAI 兼容 API 调用
- **安全预检**：API 模式下自动检测 Prompt 注入风险
- **风险评分**：12 条 JSON 可配置规则检测生成的代码
- 支持 4 种输出格式：Code / JSON / Markdown / 纯文本
- 前端生成历史记录（localStorage，保留最近 20 条）
- 提供默认示例与健康检查接口

## 处理流程

1. 前端提交 `intent`、`examples`、`format`、`settings`
2. 后端校验参数，参数缺省时加载默认示例
3. **Prompt Optimizer** 根据格式/示例数量动态构建 Prompt
4. **API 模式**：先执行 Prompt 注入预检，再调用模型
5. **Mock 模式**：直接生成模拟输出
6. **Verifier** 执行多规则检测并返回分数与问题列表

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
  "examples": ["with open('file.txt') as f: print(len(f.readlines()))"],
  "format": "code",
  "role": null,
  "constraints": [],
  "settings": {
    "apiEnabled": false,
    "apiKey": "",
    "baseUrl": "https://api.openai.com/v1",
    "model": "gpt-4o-mini"
  }
}
```

字段约束：

- `intent`：必填，字符串，最大 500 字符
- `examples`：可选，字符串数组，最多 5 条
- `format`：可选，`code` | `json` | `markdown` | `text`（默认 `code`）
- `role`：可选，自定义系统角色设定
- `constraints`：可选，额外约束列表（字符串数组）
- `settings`：可选对象
  - `apiEnabled`：是否启用 API 模式
  - `apiKey`：API 密钥
  - `baseUrl`：API 地址
  - `model`：模型名称

成功响应示例：

```json
{
  "prompt": "你是一个友好的代码助理。根据用户意图，生成可运行的 Python 示例。\n\n用户意图：读取文件并统计行数\n示例：\nwith open('file.txt') as f: print(len(f.readlines()))\n请参考以上示例的风格和结构进行生成。\n请仅返回可运行的代码，不要解释。",
  "system_prompt": "你是一个友好的代码助理。根据用户意图，生成可运行的 Python 示例。",
  "user_text": "用户意图：读取文件并统计行数\n示例：\nwith open('file.txt') as f: print(len(f.readlines()))",
  "output": "# 模拟代码输出 for intent: 读取文件并统计行数\nprint('hello world')\n",
  "score": 100,
  "issues": [],
  "meta": {
    "engine": "mock",
    "model": "mock",
    "output_format": "code",
    "used_default_examples": false,
    "examples_count": 1
  }
}
```

错误响应示例：

```json
{ "error": "intent 不能为空" }
```

Prompt 注入拦截（API 模式）：

```json
{
  "error": "检测到 Prompt 注入风险",
  "risks": ["尝试覆盖之前的指令"],
  "prompt": "..."
}
```

## 风险评分规则

`app/rules.json` 包含 12 条可配置规则，支持正则匹配和长度检测：

| 规则 | 类型 | 扣分 |
|------|------|------|
| 系统/子进程调用 (`os.system`, `subprocess`) | 正则 | 50 |
| 不安全反序列化 (`pickle`, `yaml.load`, `marshal`) | 正则 | 50 |
| 凭据硬编码 (`api_key=`, `password=`) | 正则 | 45 |
| Shell 命令注入 (`os.popen`, `popen()`) | 正则 | 45 |
| 动态执行 (`eval(`, `exec(`) | 正则 | 40 |
| 动态导入/编译 (`__import__`, `importlib`, `compile`) | 正则 | 35 |
| 网络外联 (`requests`, `urllib`, `socket`) | 正则 | 30 |
| 文件写入 (`open(... 'w')`) | 正则 | 25 |
| 路径遍历 (`../`, `os.chdir`) | 正则 | 20 |
| 底层模块 (`ctypes`, `shutil`, `platform`, `getpass`) | 正则 | 15 |
| 输出过短 (< 10 字符) | 长度 | 20 |
| 输出过长 (> 5000 字符) | 长度 | 10 |

最低分为 0。

## Prompt 注入预检

API 模式下自动检测 `user_text` 中的注入模式：

- 覆盖之前指令 (`ignore previous instructions`)
- 绕过角色限制 (`DAN`, `developer mode`)
- 篡改系统提示词 (`system prompt:`)
- 伪装身份 (`pretend you are`)
- 清除安全约束 (`forget your rules`)
- 提取系统提示词 (`show your system prompt`)
- 重新定义行为 (`from now on you are`)
- 禁用安全指令 (`do not follow`)
- 强制行为覆盖 (`you must always respond`)

## 项目结构

```text
prompt-buddy/
├─ app/
│  ├─ main.py                 # Flask 入口，路由 + API 调用 + 预检
│  ├─ prompt_optimizer.py     # 多格式 Prompt 动态构建
│  ├─ verifier.py             # 安全评分引擎（加载 rules.json）
│  ├─ rules.json              # 可配置风险检测规则（12 条）
│  └─ templates/
│     └─ example_prompts.json # 默认示例数据
├─ web/
│  └─ index.html              # 单页前端（含历史记录/深色主题）
├─ prompt-buddy.spec          # PyInstaller 打包配置
├─ requirements.txt           # 依赖：flask, werkzeug
├─ init_repo.ps1              # Git 初始化 + 推送脚本
└─ README.md
```

## 本地运行

```powershell
Set-Location "C:\Users\chen\prompt-buddy"
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python app\main.py
```

访问地址：`http://127.0.0.1:5000`

## 打包为 EXE

```powershell
pyinstaller prompt-buddy.spec
```

## PowerShell 调用示例

```powershell
# Mock 模式
Invoke-RestMethod -Uri "http://127.0.0.1:5000/generate" `
  -Method Post `
  -ContentType "application/json" `
  -Body (ConvertTo-Json @{
    intent = "写一个读取文本并统计行数的 Python 示例"
    examples = @("with open('file.txt') as f: print(len(f.readlines()))")
    format = "code"
  })

# JSON 格式输出
Invoke-RestMethod -Uri "http://127.0.0.1:5000/generate" `
  -Method Post `
  -ContentType "application/json" `
  -Body (ConvertTo-Json @{
    intent = "列出 5 种常见排序算法的时间复杂度"
    format = "json"
  })
```

## GitHub 推送脚本

```powershell
.\init_repo.ps1 -RemoteUrl "https://github.com/<YOUR_USERNAME>/<YOUR_REPO>.git"
```
