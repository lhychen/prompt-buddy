# Prompt Buddy

Prompt Buddy 是一个轻量级 Prompt 优化工具，输入任务意图和可选的风格参考文本，即可生成匹配目标语气、格式和结构的优化 Prompt。

## 功能概览

- **意图输入**：描述你想要 AI 完成的任务
- **风格参考**（可选）：粘贴示例文本，Prompt Buddy 自动分析其语气、格式、人称、语言等特征，生成风格匹配的 Prompt
- **风格特征检测**：学术口吻、技术风格、口语化、分点列举、段落叙述、问答式、对话式等
- **默认示例库**：5 种预设风格模板（学术/技术文档/产品需求/口语化/问答式）
- **生成历史**：自动保存最近 20 条记录，点击恢复
- **深色/浅色主题**，响应式布局

## 处理流程

```
intent + style_text (可选)
       │
       ▼
   风格分析 (tone / format / person / language)
       │
       ▼
   Prompt 构建 (角色定义 + 风格参考 + 意图注入)
       │
       ▼
   优化后的 Prompt
```

## 接口说明

### `GET /healthz`

```json
{ "status": "ok" }
```

### `GET /api/examples`

返回风格示例列表：

```json
{
  "examples": [
    { "label": "学术风格", "text": "本研究旨在探讨..." },
    { "label": "技术文档", "text": "## 快速开始\n### 环境要求..." }
  ]
}
```

### `POST /generate`

请求体：

```json
{
  "intent": "解释什么是闭包",
  "style_text": "嘿！想不想让你的代码跑得更快？我跟你说...",
  "settings": {}
}
```

字段约束：

| 字段 | 必填 | 最大长度 |
|------|------|----------|
| `intent` | 是 | 500 |
| `style_text` | 否 | 2000 |
| `settings` | 否 | - |

成功响应：

```json
{
  "prompt": "你是一位友好的助手，使用亲切、易懂的语言。请使用自然段落的形式组织回答...\n\n以下是一段参考文本，请模仿其语气、格式和结构风格：\n```\n嘿！想不想让你的代码跑得更快？...\n```\n\n用户意图：解释什么是闭包\n\n请根据用户意图，使用与参考文本一致的风格进行回应...",
  "style_features": ["口语化/友好", "段落叙述", "第一人称", "中文"],
  "meta": {
    "style_provided": true,
    "intent_length": 7,
    "style_length": 42
  }
}
```

无风格参考时使用默认友好助理风格。

## 风格检测规则

| 维度 | 特征 | 示例触发词 |
|------|------|-----------|
| 语气 | 学术口吻 | 研究、表明、综上所述、therefore |
| | 口语化/友好 | 你、我、吧、啦、!、~ |
| | 技术风格 | api、sdk、```、function、import |
| 格式 | 分点列举 | `- `、`1. `、`* `、`## ` |
| | 段落叙述 | 多行连续文本无标记 |
| | 问答式 | Q:/A:、问:/答: |
| 人称 | 第一人称 | 我、我们、I、we |
| | 第三人称 | 它、他、她、they |
| 语言 | 中文/English/混合 | 字符统计 |

## 项目结构

```text
prompt-buddy/
├─ app/
│  ├─ main.py                 # Flask 入口 + 路由
│  ├─ prompt_optimizer.py     # 风格分析 + Prompt 构建
│  └─ templates/
│     └─ example_prompts.json # 预设风格示例
├─ web/
│  └─ index.html              # 单页前端
├─ .github/workflows/
│  ├─ ci.yml                  # CI 测试
│  └─ release.yml             # 自动打包发行
├─ prompt-buddy.spec          # PyInstaller 配置
├─ requirements.txt           # flask, werkzeug
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

双击 exe 自动打开浏览器 → `http://127.0.0.1:5000`

## 打包

```powershell
pyinstaller prompt-buddy.spec
```
