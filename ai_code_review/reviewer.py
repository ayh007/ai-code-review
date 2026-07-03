"""核心审查编排模块。

协调 diff 获取 → 分块 → LLM 调用 → 结果聚合的完整流程。
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from .config import Config
from .git_utils import get_diff_stats
from .llm_client import DeepSeekClient, LLMError
from .prompts import get_dimension_prompts, build_review_messages


class Reviewer:
    """代码审查编排器。

    负责:
    1. 管理 LLM 客户端（延迟初始化）
    2. 按维度分发审查请求
    3. 聚合和排序结果
    """

    def __init__(self, config: Config):
        self.config = config
        self._client = None
        self.review_cfg = config.review

    @property
    def client(self) -> DeepSeekClient:
        """延迟初始化 LLM 客户端，仅在需要 API 调用时创建。"""
        if self._client is None:
            llm_cfg = self.config.llm
            self._client = DeepSeekClient(
                api_key=llm_cfg.get("api_key", ""),
                model=llm_cfg.get("model", "deepseek-chat"),
                base_url=llm_cfg.get("base_url", "https://api.deepseek.com"),
            )
        return self._client

    def review(
        self,
        diff: str,
        dimensions: Optional[list[str]] = None,
        language: str = "auto",
        max_tokens: int = 4096,
        parallel: bool = True,
    ) -> list[dict]:
        """对一段 diff 执行多维度审查。

        Args:
            diff: 代码 diff 文本
            dimensions: 审查维度列表，默认使用配置中的所有维度
            language: 目标编程语言
            max_tokens: LLM 最大返回 token
            parallel: 是否并发执行多维度审查

        Returns:
            聚合的 findings 列表，按严重程度排序
        """
        if not diff or not diff.strip():
            return []

        # 检查 diff 大小限制
        max_diff_size = self.review_cfg.get("max_diff_size", 50_000)
        if len(diff) > max_diff_size:
            diff = self._truncate_diff(diff, max_diff_size)

        # 确定审查维度
        if dimensions is None:
            dimensions = self.review_cfg.get(
                "dimensions", ["bugs", "security", "performance", "style"]
            )

        dim_prompts = get_dimension_prompts(dimensions)

        if not parallel or len(dim_prompts) == 1:
            # 串行执行
            all_findings = []
            for dim in dim_prompts:
                try:
                    findings = self._review_dimension(dim, diff, language, max_tokens)
                    all_findings.extend(findings)
                except LLMError as e:
                    # 单个维度失败不阻塞其他维度
                    all_findings.append({
                        "severity": "suggestion",
                        "category": "error",
                        "title": f"审查维度 '{dim['name']}' 出错",
                        "description": str(e),
                        "suggestion": "请检查 API 配置或稍后重试。",
                        "line": None,
                    })
        else:
            # 并发执行
            all_findings = self._review_parallel(
                dim_prompts, diff, language, max_tokens
            )

        # 去重（相同标题和行号的视为重复）
        all_findings = self._deduplicate(all_findings)

        # 按严重程度排序
        severity_order = {"critical": 0, "warning": 1, "suggestion": 2}
        all_findings.sort(
            key=lambda f: (severity_order.get(f.get("severity", "suggestion"), 99),)
        )

        return all_findings

    def _review_dimension(
        self, dim: dict, diff: str, language: str, max_tokens: int
    ) -> list[dict]:
        """对单个维度执行审查。"""
        messages = build_review_messages(dim, diff, language)
        findings = self.client.review(messages, max_tokens=max_tokens)
        # 确保 category 设置为当前维度
        for f in findings:
            f["category"] = dim["key"]
        return findings

    def _review_parallel(
        self,
        dim_prompts: list[dict],
        diff: str,
        language: str,
        max_tokens: int,
    ) -> list[dict]:
        """并发执行多个维度的审查。"""
        all_findings = []

        with ThreadPoolExecutor(max_workers=len(dim_prompts)) as executor:
            future_to_dim = {
                executor.submit(
                    self._review_dimension, dim, diff, language, max_tokens
                ): dim
                for dim in dim_prompts
            }

            for future in as_completed(future_to_dim):
                dim = future_to_dim[future]
                try:
                    findings = future.result()
                    all_findings.extend(findings)
                except Exception as e:
                    all_findings.append({
                        "severity": "suggestion",
                        "category": "error",
                        "title": f"审查维度 '{dim['name']}' 出错",
                        "description": str(e),
                        "suggestion": "请检查 API 配置或稍后重试。",
                        "line": None,
                    })

        return all_findings

    def _truncate_diff(self, diff: str, max_size: int) -> str:
        """截断过大的 diff，尽量在文件边界处截断。"""
        if len(diff) <= max_size:
            return diff

        # 在文件边界（diff --git）处分割
        files = diff.split("\ndiff --git ")
        if len(files) <= 1:
            # 没有文件边界标记，直接硬截断
            return (
                diff[:max_size]
                + f"\n\n... (省略剩余 {len(diff) - max_size} bytes，"
                f"总计 {len(diff)} bytes 超过 {max_size} bytes 限制)"
            )

        result = files[0]  # 第一个可能不含 diff --git 前缀

        for file_diff in files[1:]:
            chunk = "\ndiff --git " + file_diff
            if len(result) + len(chunk) > max_size:
                result += (
                    f"\n\n... (省略剩余 {len(files) - files.index(file_diff) - 1} 个文件的 diff，"
                    f"总计 {len(diff)} bytes 超过 {max_size} bytes 限制)"
                )
                break
            result += chunk

        return result

    def _deduplicate(self, findings: list[dict]) -> list[dict]:
        """去除重复的 findings。"""
        seen = set()
        unique = []
        for f in findings:
            key = (f.get("title", ""), f.get("line"))
            if key not in seen:
                seen.add(key)
                unique.append(f)
        return unique
