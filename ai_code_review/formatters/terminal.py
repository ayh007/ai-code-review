"""终端彩色输出格式化器。

使用 Rich 库生成美观的终端输出。
"""

from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box


# 严重程度 → 颜色和图标映射
SEVERITY_STYLES = {
    "critical": {"color": "red", "icon": "🔴", "label": "CRITICAL"},
    "warning": {"color": "yellow", "icon": "🟡", "label": "WARNING"},
    "suggestion": {"color": "green", "icon": "🟢", "label": "SUGGESTION"},
}


def format_findings(
    findings: list[dict],
    diff_stats: Optional[dict] = None,
    model: str = "deepseek-chat",
    color: bool = True,
) -> str:
    """将 findings 格式化为富文本终端输出。

    Args:
        findings: 审查发现列表
        diff_stats: diff 统计信息
        model: 使用的模型名称
        color: 是否使用彩色输出

    Returns:
        格式化后的字符串（含 Rich markup）
    """
    console = Console(no_color=not color, force_terminal=True, width=100)

    with console.capture() as capture:
        # ── 头部面板 ──
        header_lines = []
        header_lines.append(f"Model: {model}")
        if diff_stats:
            header_lines.append(
                f"Files: {diff_stats['files_changed']}  "
                f"+{diff_stats['insertions']}  "
                f"-{diff_stats['deletions']}"
            )
        header = Panel(
            "\n".join(header_lines),
            title="[bold]🔍 AI Code Review[/bold]",
            border_style="cyan",
            box=box.ROUNDED,
        )
        console.print(header)

        if not findings:
            console.print(
                Panel(
                    "[green]✅ 未发现问题，代码看起来不错！[/green]",
                    border_style="green",
                    box=box.ROUNDED,
                )
            )
            console.print()
            return capture.get()

        # ── 按严重程度排序 ──
        severity_order = {"critical": 0, "warning": 1, "suggestion": 2}
        sorted_findings = sorted(
            findings, key=lambda f: severity_order.get(f.get("severity", "suggestion"), 99)
        )

        # ── 逐条输出 ──
        for i, finding in enumerate(sorted_findings):
            severity = finding.get("severity", "suggestion")
            style = SEVERITY_STYLES.get(severity, SEVERITY_STYLES["suggestion"])
            icon = style["icon"]
            sev_color = style["color"]

            # 标题行
            line_info = f"(line {finding['line']})" if finding.get("line") else ""
            title = Text(f"{icon} [{sev_color}]{finding.get('title', '未命名')}[/{sev_color}] {line_info}")
            console.print(title)

            # 描述
            if finding.get("description"):
                console.print(f"   {finding['description']}")

            # 建议
            if finding.get("suggestion"):
                console.print(f"   [bold cyan]→ Suggestion:[/bold cyan] {finding['suggestion']}")

            console.print()  # 空行

        # ── 底部汇总 ──
        critical_count = sum(1 for f in findings if f.get("severity") == "critical")
        warning_count = sum(1 for f in findings if f.get("severity") == "warning")
        suggestion_count = sum(1 for f in findings if f.get("severity") == "suggestion")

        summary_parts = []
        if critical_count:
            summary_parts.append(f"[red]{critical_count} critical[/red]")
        if warning_count:
            summary_parts.append(f"[yellow]{warning_count} warnings[/yellow]")
        if suggestion_count:
            summary_parts.append(f"[green]{suggestion_count} suggestions[/green]")

        summary = " · ".join(summary_parts) if summary_parts else "no issues"
        console.print(
            Panel(
                f"Summary: {summary}",
                border_style="dim cyan",
                box=box.ROUNDED,
            )
        )

    return capture.get()
