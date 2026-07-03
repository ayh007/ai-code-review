"""审查提示词模板。

每个审查维度有独立的系统提示词和用户消息模板。
要求 LLM 返回结构化 JSON，便于解析和展示。
"""

# ── 系统提示词：定义审查角色 ──

SYSTEM_PROMPT = """你是一位资深代码审查专家，擅长发现代码中的问题并提供建设性改进建议。
你的审查必须严格、准确、有深度。只报告真实存在的问题，不要凭空猜测。

对于每个发现的问题，按以下 JSON 格式输出（不要输出其他内容）：

```json
{
  "findings": [
    {
      "line": <行号或 null>,
      "severity": "critical|warning|suggestion",
      "category": "bugs|security|performance|style",
      "title": "<简短标题>",
      "description": "<详细描述，说明为什么这是问题>",
      "suggestion": "<具体的改进建议或修复代码>"
    }
  ]
}
```

如果没有发现问题，返回空的 findings 数组。
只输出 JSON，不要输出其他解释文字。"""


# ── 各维度的用户消息模板 ──

BUGS_PROMPT = """请仔细审查以下代码 diff，**专门查找 Bug 和逻辑错误**。

重点关注:
- 空指针 / None 引用
- 数组越界 / 索引错误
- 条件判断逻辑错误（如 = 写成 ==，条件反了）
- 循环 / 递归的终止条件错误
- 异常处理缺失或不正确
- 类型错误 / 类型转换问题
- 并发 / 竞态条件
- 资源泄漏（文件未关闭、连接未释放）
- 边界条件处理（空列表、零值、None）

如果是 Python 代码，还要关注:
- try/except 吞掉异常
- 可变默认参数
- 浅拷贝导致的意外副作用

请审查以下 diff 并返回 JSON:"""


SECURITY_PROMPT = """请仔细审查以下代码 diff，**专门查找安全隐患**。

重点关注:
- SQL 注入（字符串拼接 SQL）
- 命令注入（os.system / subprocess 使用不当）
- 路径遍历 (../ 未过滤)
- XSS（未转义的用户输入输出到 HTML）
- 敏感信息硬编码（密码、token、API key）
- 不安全的加密算法（MD5、SHA1 用于密码）
- 不安全的随机数（random 用于安全场景）
- 权限校验缺失
- 不安全的反序列化（pickle、yaml.load）
- SSRF 风险

请审查以下 diff 并返回 JSON:"""


PERFORMANCE_PROMPT = """请仔细审查以下代码 diff，**专门查找性能问题**。

重点关注:
- 嵌套循环导致 O(n²) 或更高复杂度
- 在循环中进行不必要的重复计算
- N+1 查询问题（循环中查询数据库或 API）
- 内存浪费（大列表一次性加载、未使用生成器）
- 阻塞 I/O 在异步上下文中
- 字符串频繁拼接（应用 join 替代 +）
- 不必要的深拷贝
- 可使用缓存避免重复计算
- pandas / numpy 使用不当（如 iterrows 替代向量化操作）

请审查以下 diff 并返回 JSON:"""


STYLE_PROMPT = """请仔细审查以下代码 diff，**专门查找代码风格和可维护性问题**。

重点关注:
- 变量 / 函数命名不清晰或不规范
- 代码重复（可提取为函数）
- 函数过长（超过 30 行）
- 过深的嵌套（超过 3 层）
- 可以使用语言内置特性简化的写法（如 list comprehension、context manager）
- 缺少必要的注释或 docstring
- 不一致的代码风格
- 魔法数字（未定义为常量的硬编码数值）
- 导入未使用或导入顺序混乱

如果目标语言是 Python，还要关注:
- 是否遵循 PEP 8
- 类型注解缺失
- 可以使用 dataclass / Enum / walrus operator 等特性的场景

请审查以下 diff 并返回 JSON:"""


# ── 维度注册表 ──

DIMENSIONS = {
    "bugs": {
        "name": "Bug 检测",
        "icon": "🐛",
        "prompt": BUGS_PROMPT,
        "description": "逻辑错误、空指针、边界条件、异常处理",
    },
    "security": {
        "name": "安全审查",
        "icon": "🔒",
        "prompt": SECURITY_PROMPT,
        "description": "注入攻击、敏感信息泄露、不安全加密",
    },
    "performance": {
        "name": "性能分析",
        "icon": "⚡",
        "prompt": PERFORMANCE_PROMPT,
        "description": "算法复杂度、内存浪费、I/O 瓶颈",
    },
    "style": {
        "name": "代码风格",
        "icon": "🎨",
        "prompt": STYLE_PROMPT,
        "description": "命名规范、代码重复、可读性、最佳实践",
    },
}


def get_dimension_prompts(dimensions: list[str]) -> list[dict]:
    """获取指定维度的提示词列表。

    Args:
        dimensions: 维度 key 列表，如 ["bugs", "security"]

    Returns:
        [{"key": "bugs", "name": "Bug 检测", "prompt": "..."}, ...]
    """
    result = []
    for key in dimensions:
        if key in DIMENSIONS:
            dim = DIMENSIONS[key]
            result.append({
                "key": key,
                "name": dim["name"],
                "icon": dim["icon"],
                "prompt": dim["prompt"],
            })
    return result


def build_review_messages(dimension: dict, diff: str, language: str = "auto") -> list[dict]:
    """构建发送给 LLM 的完整消息列表。

    Args:
        dimension: get_dimension_prompts 返回的维度字典
        diff: 代码 diff 文本
        language: 目标编程语言

    Returns:
        [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
    """
    lang_hint = f"\n目标语言: {language}\n" if language != "auto" else ""
    user_content = f"{dimension['prompt']}{lang_hint}\n\n```diff\n{diff}\n```"
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
