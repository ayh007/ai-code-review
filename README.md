# 🔍 AI Code Review (ACR)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek-orange)](https://platform.deepseek.com/)

**AI 驱动的代码审查 CLI 工具** — 一键检测 Bug、安全漏洞、性能瓶颈和代码风格问题。

对 Git 工作区的代码改动进行多维度深度审查，由 DeepSeek 大模型提供智能分析。

---

## ✨ 功能特性

- 🐛 **Bug 检测** — 空指针、边界条件、逻辑错误、异常处理
- 🔒 **安全审查** — SQL 注入、XSS、敏感信息泄露、不安全加密
- ⚡ **性能分析** — 算法复杂度、内存浪费、N+1 查询
- 🎨 **代码风格** — 命名规范、代码重复、最佳实践
- 📊 **三种输出格式** — 终端彩色 / Markdown 报告 / JSON（CI 友好）
- ⚙️ **灵活配置** — 配置文件 + 环境变量 + 命令行参数
- 🔄 **Git 原生集成** — 审查未提交改动、指定 commit、单文件

---

## 📦 安装

### 前提条件

- Python 3.10+
- Git
- DeepSeek API Key（[获取地址](https://platform.deepseek.com/api_keys)）

### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/yourname/ai-code-review.git
cd ai-code-review

# 2. 安装依赖
pip install -e .

# 3. 设置 API Key
export DEEPSEEK_API_KEY=sk-your-api-key-here

# 4. 验证安装
acr --version
```

**Windows 用户**：使用 `set` 代替 `export`：
```cmd
set DEEPSEEK_API_KEY=sk-your-api-key-here
```

---

## 🚀 快速开始

```bash
# 审查所有未提交的改动
acr review

# 审查暂存的改动（git add 后的）
acr review --staged

# 审查上一次 commit
acr review --commit HEAD~1

# 审查指定文件
acr review src/main.py

# 只做安全审查
acr review --dimensions security

# 输出 Markdown 报告并保存
acr review --output markdown --save review-report.md

# 输出 JSON（用于 CI 管道）
acr review --output json
```

---

## 🎨 输出展示

```
╭──────────────────────────────────────────────────────────╮
│ 🔍 AI Code Review                                        │
│ Model: deepseek-chat · Files: 3 · +15 -8                 │
╰──────────────────────────────────────────────────────────╯

🔴 Potential null pointer dereference (line 42)
   The variable `user` may be None when accessing `.name`.
   → Suggestion: Add `if user is None: return` guard.

🟡 Inefficient nested loop (line 78)
   O(n²) complexity in a hot path — consider using a set.
   → Suggestion: `valid_ids = {x.id for x in items}`

🟢 Unclear variable name (line 15)
   `df` is ambiguous. Consider `dataframe` or `records_df`.
   → Suggestion: Rename to `user_dataframe` for clarity.

────────────────────────────────────────────────────────────
Summary: 1 critical · 1 warning · 1 suggestion
```

---

## ⚙️ 配置

### 配置文件

在项目根目录创建 `.acr.yml`：

```bash
acr config --init  # 自动生成配置文件
```

```yaml
llm:
  api_key: ${DEEPSEEK_API_KEY}   # 从环境变量读取
  base_url: https://api.deepseek.com
  model: deepseek-chat

review:
  dimensions: [bugs, security, performance, style]
  exclude_patterns:
    - "*.lock"
    - "package-lock.json"
  max_file_size: 100000
  max_diff_size: 50000

output:
  format: terminal    # terminal | markdown | json
  color: true
```

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥（必填） | — |
| `DEEPSEEK_BASE_URL` | API 地址 | `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | 模型名称 | `deepseek-chat` |

### 优先级

```
命令行参数 > 环境变量 > 配置文件 > 默认值
```

---

## 🧪 运行测试

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

---

## 📁 项目结构

```
ai-code-review/
├── ai_code_review/
│   ├── cli.py              # CLI 入口 (click)
│   ├── reviewer.py         # 审查编排核心
│   ├── git_utils.py        # Git 操作封装
│   ├── llm_client.py       # DeepSeek API 客户端
│   ├── prompts.py          # 审查提示词模板
│   ├── config.py           # 配置管理
│   └── formatters/
│       ├── terminal.py     # Rich 终端输出
│       ├── markdown.py     # Markdown 报告
│       └── json_fmt.py     # JSON 输出
├── tests/
│   ├── test_git_utils.py
│   ├── test_llm_client.py
│   └── test_reviewer.py
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## 🔧 技术栈

| 组件 | 技术 |
|------|------|
| CLI 框架 | [Click](https://click.palletsprojects.com/) |
| 终端渲染 | [Rich](https://rich.readthedocs.io/) |
| LLM API | DeepSeek (OpenAI 兼容) |
| 配置解析 | PyYAML |
| 测试框架 | Pytest |

---

## 📄 License

MIT © Your Name

---

## 🙏 致谢

- [DeepSeek](https://platform.deepseek.com/) — 高性能、高性价比的 LLM API
- [Rich](https://github.com/Textualize/rich) — 让终端输出更美
