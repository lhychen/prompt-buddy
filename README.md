# Prompt Buddy

一个面向新手的 AI 提示工程演示项目：输入需求（intent）后，系统会自动优化提示词、生成模拟代码结果，并给出基础安全评分。项目结构简单、可快速运行，适合作为“AI 创作者申请”或作品集 Demo 上传 GitHub。

## 项目目标

解决的核心痛点：
- 新手很难把自然语言需求转成稳定、可复用的提示词
- 缺少“生成结果是否安全/可接受”的最小验证闭环

本项目提供一个最小但完整的流程：
1. 前端收集用户 intent + 示例
2. 后端优化提示词（Prompt Optimizer）
3. 生成代码结果（当前为 Mock，可替换真实模型）
4. 对结果进行规则校验并评分（Verifier）

## 当前能力

- `POST /generate`
  - 输入：`intent`（必填）、`examples`（可选）
  - 输出：`prompt`、`output`、`score`、`issues`
- `GET /api/examples`
  - 返回默认示例（来自 `app/templates/example_prompts.json`）
- `GET /healthz`
  - 健康检查接口，返回 `{"status":"ok"}`
- Web 页面
  - 支持输入需求、加载默认示例、查看 JSON 结果

## 技术栈

- Python 3
- Flask 2.2.5
- 原生 HTML + JavaScript（无前端框架）

## 目录结构

```text
prompt-buddy/
├─ app/
│  ├─ main.py                     # 路由与接口入口
│  ├─ prompt_optimizer.py         # 提示词优化逻辑
│  ├─ verifier.py                 # 输出校验与评分
│  └─ templates/
│     └─ example_prompts.json     # 默认示例库
├─ web/
│  └─ index.html                  # 演示前端
├─ requirements.txt
├─ .gitignore
├─ init_repo.ps1                  # 一键初始化并推送 GitHub
└─ README.md
```

## 快速开始（Windows PowerShell）

1. 进入项目目录
   ```powershell
   Set-Location "C:\Users\chen\prompt-buddy"
   ```
2. 创建并激活虚拟环境
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   ```
3. 安装依赖
   ```powershell
   pip install -r requirements.txt
   ```
4. 启动服务
   ```powershell
   python app\main.py
   ```
5. 打开浏览器
   - `http://127.0.0.1:5000`

## API 使用示例

### 1) 生成接口

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:5000/generate" `
  -Method Post `
  -ContentType "application/json" `
  -Body (ConvertTo-Json @{
    intent = "写一个读取文本并统计行数的 Python 示例"
    examples = @("with open('file.txt') as f: print(len(f.readlines()))")
  })
```

示例响应（节选）：

```json
{
  "prompt": "...优化后的提示词...",
  "output": "# 模拟代码 for intent: ...",
  "score": 100,
  "issues": []
}
```

### 2) 获取默认示例

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/examples" -Method Get
```

### 3) 健康检查

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:5000/healthz" -Method Get
```

## 核心逻辑说明

### Prompt Optimizer（`app/prompt_optimizer.py`）
- 清洗 `intent` 与 `examples`
- 限制示例数量（最多 5 条）
- 拼装统一模板，输出可复用提示词

### Verifier（`app/verifier.py`）
- 检测高风险调用关键词（如 `os.system`、`subprocess`）
- 检测动态执行（`eval` / `exec`）
- 按规则扣分并输出问题列表

### 默认示例回退机制（`app/main.py`）
- 若调用 `/generate` 未提供 `examples`，自动加载 `example_prompts.json` 中示例，提升首用体验

## 安全与限制

- 当前 `output` 为 **Mock 结果**，未接入真实大模型 API
- Verifier 是轻量规则引擎，不是完整安全沙箱
- 不要将 API Key 明文写入代码；建议使用环境变量管理

## 如何替换为真实模型（建议）

在 `app/main.py` 的 `build_mock_output` 位置替换成真实 API 调用逻辑：
- 读取环境变量中的模型密钥
- 将 `prompt` 发送到模型接口
- 把模型返回文本作为 `output`
- 保留 `verify_output` 评分流程

## 上传到 GitHub

执行：

```powershell
.\init_repo.ps1 -RemoteUrl "https://github.com/<YOUR_USERNAME>/<YOUR_REPO>.git"
```

脚本会自动完成：
- `git init`
- `git add -A`
- `git commit`
- 设置/更新 `origin`
- 推送到 `main`

