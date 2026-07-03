"""JSON 格式化器。

生成结构化 JSON 输出，适用于 CI/CD 集成和程序化处理。
"""

import json
from datetime import datetime, timezone
from typing import Optional


def format_findings(
    findings: list[dict],
    diff_stats: Optional[dict] = None,
    model: str = "deepseek-chat",
) -> str:
    """将 findings 格式化为 JSON 字符串。

    Args:
        findings: 审查发现列表
        diff_stats: diff 统计信息
        model: 使用的模型名称

    Returns:
        格式化的 JSON 字符串
    """
    # 统计
    critical_count = sum(1 for f in findings if f.get("severity") == "critical")
    warning_count = sum(1 for f in findings if f.get("severity") == "warning")
    suggestion_count = sum(1 for f in findings if f.get("severity") == "suggestion")

    report = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "model": model,
            "dimensions_reviewed": list(
                set(f.get("category", "unknown") for f in findings)
            )
            if findings
            else [],
        },
        "stats": {
            "total": len(findings),
            "critical": critical_count,
            "warning": warning_count,
            "suggestion": suggestion_count,
        },
        "diff_stats": diff_stats or {},
        "findings": findings,
    }

    return json.dumps(report, ensure_ascii=False, indent=2)
