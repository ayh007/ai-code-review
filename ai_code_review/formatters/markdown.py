"""Markdown 格式化器。

生成可保存的 Markdown 审查报告。
"""

from datetime import datetime
from typing import Optional


def format_findings(
    findings: list[dict],
    diff_stats: Optional[dict] = None,
    model: str = "deepseek-chat",
) -> str:
    """将 findings 格式化为 Markdown 报告。

    Args:
        findings: 审查发现列表
        diff_stats: diff 统计信息
        model: 使用的模型名称

    Returns:
        Markdown 格式的报告字符串
    """
    lines = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 标题
    lines.append("# 🔍 AI Code Review Report")
    lines.append("")
    lines.append(f"**Generated:** {now}")
    lines.append(f"**Model:** {model}")
    if diff_stats:
        lines.append(
            f"**Files Changed:** {diff_stats['files_changed']}  "
            f"|  **+{diff_stats['insertions']}**  **-{diff_stats['deletions']}**"
        )
    lines.append("")
    lines.append("---")
    lines.append("")

    if not findings:
        lines.append("## ✅ No Issues Found")
        lines.append("")
        lines.append("The code looks good! No problems were detected.")
        return "\n".join(lines)

    # 按严重程度排序
    severity_order = {"critical": 0, "warning": 1, "suggestion": 2}
    sorted_findings = sorted(
        findings, key=lambda f: severity_order.get(f.get("severity", "suggestion"), 99)
    )

    # 统计
    critical_count = sum(1 for f in findings if f.get("severity") == "critical")
    warning_count = sum(1 for f in findings if f.get("severity") == "warning")
    suggestion_count = sum(1 for f in findings if f.get("severity") == "suggestion")

    lines.append("## 📊 Summary")
    lines.append("")
    lines.append(f"| Severity | Count |")
    lines.append(f"|----------|-------|")
    if critical_count:
        lines.append(f"| 🔴 Critical | {critical_count} |")
    if warning_count:
        lines.append(f"| 🟡 Warning | {warning_count} |")
    if suggestion_count:
        lines.append(f"| 🟢 Suggestion | {suggestion_count} |")
    lines.append(f"| **Total** | **{len(findings)}** |")
    lines.append("")

    # 逐条详情
    lines.append("---")
    lines.append("")
    lines.append("## 📋 Findings")
    lines.append("")

    severity_labels = {
        "critical": "🔴 Critical",
        "warning": "🟡 Warning",
        "suggestion": "🟢 Suggestion",
    }

    for i, finding in enumerate(sorted_findings, 1):
        severity = finding.get("severity", "suggestion")
        label = severity_labels.get(severity, "⚪ Unknown")
        line_info = f" (line {finding['line']})" if finding.get("line") else ""

        lines.append(f"### {i}. {label}{line_info}")
        lines.append("")
        lines.append(f"**{finding.get('title', 'Untitled')}**")
        lines.append("")

        if finding.get("description"):
            lines.append(finding["description"])
            lines.append("")

        if finding.get("suggestion"):
            lines.append(f"> 💡 **Suggestion:** {finding['suggestion']}")
            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def save_report(findings: list[dict], filepath: str, **kwargs) -> str:
    """将报告保存到文件。

    Args:
        findings: 审查发现列表
        filepath: 输出文件路径

    Returns:
        保存的文件路径
    """
    content = format_findings(findings, **kwargs)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath
