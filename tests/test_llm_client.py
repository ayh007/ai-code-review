"""LLM 客户端模块测试。"""

import pytest
import json

from ai_code_review.llm_client import DeepSeekClient, LLMError


class TestParseResponse:
    """测试 _parse_response 方法。"""

    def test_parse_plain_json(self):
        """解析纯 JSON 响应。"""
        client = DeepSeekClient(api_key="sk-test")
        content = json.dumps({
            "findings": [
                {
                    "line": 42,
                    "severity": "critical",
                    "category": "bugs",
                    "title": "Null pointer",
                    "description": "Accessing None",
                    "suggestion": "Add guard",
                }
            ]
        })
        findings = client._parse_response(content)
        assert len(findings) == 1
        assert findings[0]["title"] == "Null pointer"
        assert findings[0]["severity"] == "critical"

    def test_parse_json_in_markdown_block(self):
        """解析包裹在 markdown 代码块中的 JSON。"""
        client = DeepSeekClient(api_key="sk-test")
        content = """Here is my review:

```json
{
  "findings": [
    {
      "line": 10,
      "severity": "warning",
      "category": "performance",
      "title": "Slow loop",
      "description": "Nested loop",
      "suggestion": "Use set"
    }
  ]
}
```

That's all."""
        findings = client._parse_response(content)
        assert len(findings) == 1
        assert findings[0]["title"] == "Slow loop"

    def test_parse_empty_findings(self):
        """解析空 findings。"""
        client = DeepSeekClient(api_key="sk-test")
        content = json.dumps({"findings": []})
        findings = client._parse_response(content)
        assert findings == []

    def test_parse_missing_fields(self):
        """解析缺少字段的 finding 应填充默认值。"""
        client = DeepSeekClient(api_key="sk-test")
        content = json.dumps({
            "findings": [{"title": "Something"}]
        })
        findings = client._parse_response(content)
        assert len(findings) == 1
        assert findings[0]["severity"] == "suggestion"
        assert findings[0]["line"] is None
        assert findings[0]["description"] == ""

    def test_no_api_key_raises_error(self):
        """缺少 API key 应抛出 LLMError。"""
        with pytest.raises(LLMError, match="未设置 DeepSeek API Key"):
            DeepSeekClient(api_key="")
