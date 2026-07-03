"""审查编排模块测试。"""

import pytest

from ai_code_review.config import Config
from ai_code_review.reviewer import Reviewer


class TestReviewerTruncation:
    """测试 diff 截断逻辑。"""

    def test_short_diff_not_truncated(self):
        """短 diff 不应被截断。"""
        config = Config(cli_overrides={"no_color": True})
        reviewer = Reviewer(config)
        diff = "short diff content"
        result = reviewer._truncate_diff(diff, max_size=1000)
        assert result == diff

    def test_long_diff_truncated(self):
        """超长 diff 应被截断。"""
        config = Config(cli_overrides={"no_color": True})
        reviewer = Reviewer(config)
        diff = "x" * 500
        result = reviewer._truncate_diff(diff, max_size=200)
        assert len(result) <= 300  # 截断后 + 提示信息
        assert "省略" in result or "超过" in result

    def test_empty_diff_returns_empty_findings(self):
        """空 diff 应返回空列表。"""
        config = Config(cli_overrides={"no_color": True})
        reviewer = Reviewer(config)
        findings = reviewer.review("")
        assert findings == []
        findings = reviewer.review("   ")
        assert findings == []


class TestDeduplication:
    """测试去重逻辑。"""

    def test_duplicate_findings_removed(self):
        """重复 findings 应被去重。"""
        config = Config(cli_overrides={"no_color": True})
        reviewer = Reviewer(config)
        findings = [
            {"title": "Bug A", "line": 10, "severity": "critical"},
            {"title": "Bug A", "line": 10, "severity": "critical"},  # 完全重复
            {"title": "Bug B", "line": 20, "severity": "warning"},
        ]
        result = reviewer._deduplicate(findings)
        assert len(result) == 2

    def test_same_title_different_line_kept(self):
        """相同标题但不同行号应保留。"""
        config = Config(cli_overrides={"no_color": True})
        reviewer = Reviewer(config)
        findings = [
            {"title": "Same bug", "line": 10, "severity": "critical"},
            {"title": "Same bug", "line": 20, "severity": "critical"},
        ]
        result = reviewer._deduplicate(findings)
        assert len(result) == 2
