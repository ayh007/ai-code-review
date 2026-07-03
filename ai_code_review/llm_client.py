"""DeepSeek API 客户端封装。

通过 OpenAI Python SDK 调用 DeepSeek API（兼容格式）。
"""

import json
import re
import time
from typing import Optional

from openai import OpenAI


class LLMError(Exception):
    """LLM 调用异常。"""

    pass


class DeepSeekClient:
    """DeepSeek API 客户端。

    封装代码审查请求的发送和响应解析。
    """

    def __init__(
        self,
        api_key: str,
        model: str = "deepseek-chat",
        base_url: str = "https://api.deepseek.com",
        max_retries: int = 2,
    ):
        if not api_key:
            raise LLMError(
                "未设置 DeepSeek API Key。请通过以下方式之一设置:\n"
                "  1. 环境变量: export DEEPSEEK_API_KEY=sk-xxx\n"
                "  2. 配置文件: .acr.yml 中设置 llm.api_key\n"
                "  3. 命令行: acr config --set llm.api_key sk-xxx"
            )

        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url.rstrip("/"),
        )
        self.model = model
        self.max_retries = max_retries

    def review(
        self,
        messages: list[dict],
        max_tokens: int = 4096,
        temperature: float = 0.1,
    ) -> list[dict]:
        """发送代码审查请求。

        Args:
            messages: 消息列表 [{"role": "system", "content": ...}, ...]
            max_tokens: 最大返回 token 数
            temperature: 生成温度 (低温度 = 更确定性的输出)

        Returns:
            解析后的 findings 列表

        Raises:
            LLMError: API 调用失败或响应解析失败
        """
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )

                content = response.choices[0].message.content
                if content is None:
                    raise LLMError("LLM 返回了空响应")

                return self._parse_response(content)

            except LLMError:
                raise
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    wait = 2 ** attempt
                    time.sleep(wait)
                else:
                    raise LLMError(
                        f"DeepSeek API 调用失败 (已重试 {self.max_retries} 次): {e}"
                    ) from e

        # 理论上不会到这里，但为了类型安全
        raise LLMError(f"DeepSeek API 调用失败: {last_error}")

    def _parse_response(self, content: str) -> list[dict]:
        """从 LLM 响应中提取 JSON findings。

        处理 LLM 可能包裹在 ```json ... ``` 中的情况。
        """
        # 尝试提取 JSON 块
        json_match = re.search(
            r"```(?:json)?\s*\n?(.*?)\n?```", content, re.DOTALL
        )
        if json_match:
            json_str = json_match.group(1)
        else:
            # 尝试直接解析整个内容
            json_str = content

        # 查找第一个 { 到最后一个 }
        start = json_str.find("{")
        end = json_str.rfind("}")
        if start != -1 and end != -1:
            json_str = json_str[start : end + 1]

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise LLMError(
                f"无法解析 LLM 返回的 JSON。响应内容:\n{content[:500]}..."
            ) from e

        findings = data.get("findings", [])
        if not isinstance(findings, list):
            findings = []

        # 为每个 finding 补充默认字段
        for f in findings:
            f.setdefault("line", None)
            f.setdefault("severity", "suggestion")
            f.setdefault("category", "style")
            f.setdefault("title", "未命名问题")
            f.setdefault("description", "")
            f.setdefault("suggestion", "")

        return findings
