## 项目经历

### AI Code Review (ACR) — DeepSeek 驱动的智能代码审查 CLI 工具

**2026.07** | 个人项目 | [GitHub](#)

**项目简介**

基于 DeepSeek 大语言模型构建的命令行代码审查工具，集成 Git 工作流，一键对代码改动进行多维度深度分析，覆盖 Bug 检测、安全漏洞扫描、性能瓶颈定位和代码风格审查，支持多种输出格式适配本地开发和 CI/CD 流水线。

**技术栈**

`Python 3.13` `Click` `Rich` `DeepSeek API (OpenAI 兼容)` `Git (subprocess)` `PyYAML` `Pytest` `多线程并发`

**核心职责与成果**

- **设计并实现了多维度审查引擎**，围绕 bugs / security / performance / style 四个方向独立设计 LLM 系统提示词，通过 ThreadPoolExecutor 实现多维度并发审查，单次请求即可输出覆盖全部维度的结构化审查报告
- **封装 LLM 客户端层**，基于 OpenAI SDK 对接 DeepSeek API，实现了自动重试机制、响应解析容错（支持 JSON / Markdown 代码块 / 纯文本多种格式）和优雅降级处理
- **开发 Git 集成模块**，通过 subprocess 调用 Git 命令，支持工作区 diff、暂存区 diff、commit diff、单文件、目录级别的代码提取，并自动解析变更文件数 / 增删行数等统计信息
- **实现三层优先级配置系统**（命令行参数 > 环境变量 > YAML 配置文件），支持 `${VAR}` 环境变量引用解析和深度配置合并，兼顾灵活性和开箱即用体验
- **构建三种输出通道**：Rich 终端彩色面板输出（即时反馈）、Markdown 报告导出（文档归档）、结构化 JSON 输出（CI/CD 集成，退出码联动），覆盖不同使用场景
- **编写 15 个单元测试**（Pytest），覆盖 Git 工具函数、LLM 响应解析、diff 截断去重等核心逻辑，测试全部通过

**项目难点与解决**

| 难点 | 解决方案 |
|------|----------|
| LLM 返回格式不稳定（有时 JSON、有时 Markdown 包裹） | 正则 + JSON 多模式解析，先匹配代码块再兜底纯文本解析 |
| 大 diff 超出 API token 限制 | 按 diff --git 文件边界智能分段截断，保留完整文件上下文 |
| Windows GBK 终端无法渲染 Emoji | 启动时改写 stdout 编码为 UTF-8 with errors=replace |
| 无 API Key 时工具应降级而非崩溃 | Reviewer 延迟初始化 LLM 客户端，仅在实际需调用 API 时检查密钥 |

**项目架构**

```
cli.py (Click 命令层)
  → reviewer.py (审查编排: 分块 → 并发 → 去重 → 排序)
      ├── git_utils.py (Git diff 提取)
      ├── llm_client.py (DeepSeek API 封装)
      ├── prompts.py (4 维度提示词模板)
      └── formatters/
          ├── terminal.py (Rich 彩色面板)
          ├── markdown.py (MD 报告导出)
          └── json_fmt.py (CI JSON 输出)
```

**实际审查效果**（对包含 9 个故意植入缺陷的 Python 示例文件）

```
Summary: 11 critical · 4 warnings · 10 suggestions
成功检出: SQL 注入、命令注入、Pickle 反序列化、硬编码密码、
空指针引用、除零错误、O(n²) 性能瓶颈、未使用变量 等全部问题
```
