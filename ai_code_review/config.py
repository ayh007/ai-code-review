"""配置加载模块。

支持三层配置，优先级从高到低:
1. 命令行参数
2. 环境变量
3. 配置文件 (.acr.yml 或 ~/.acr/config.yml)
"""

import os
import re
from pathlib import Path
from typing import Any, Optional

import yaml


# 默认配置值
DEFAULTS = {
    "llm": {
        "api_key": None,
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
    },
    "review": {
        "dimensions": ["bugs", "security", "performance", "style"],
        "exclude_patterns": [
            "*.lock",
            "poetry.lock",
            "package-lock.json",
            "*.pyc",
        ],
        "max_file_size": 100_000,
        "max_diff_size": 50_000,
    },
    "output": {
        "format": "terminal",
        "color": True,
    },
}


def _resolve_env_vars(value: Any) -> Any:
    """递归解析字符串中的 ${VAR} 环境变量引用。"""
    if isinstance(value, str):
        pattern = re.compile(r"\$\{(\w+)\}")
        return pattern.sub(
            lambda m: os.environ.get(m.group(1), m.group(0)), value
        )
    elif isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_resolve_env_vars(v) for v in value]
    return value


def _deep_merge(base: dict, override: dict) -> dict:
    """深度合并两个字典，override 覆盖 base。"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _find_config_file() -> Optional[Path]:
    """查找配置文件，项目级优先于用户级。"""
    # 项目级配置
    project_config = Path.cwd() / ".acr.yml"
    if project_config.exists():
        return project_config

    # 用户级配置
    user_config = Path.home() / ".acr" / "config.yml"
    if user_config.exists():
        return user_config

    return None


class Config:
    """审查工具配置。

    加载顺序: 默认值 → 配置文件 → 环境变量 → 命令行参数
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        cli_overrides: Optional[dict] = None,
    ):
        # 从默认值开始
        self._data = DEFAULTS.copy()

        # 加载配置文件
        if config_path:
            cfg_file = Path(config_path)
        else:
            cfg_file = _find_config_file()

        if cfg_file and cfg_file.exists():
            with open(cfg_file, "r", encoding="utf-8") as f:
                file_config = yaml.safe_load(f) or {}
            file_config = _resolve_env_vars(file_config)
            self._data = _deep_merge(self._data, file_config)

        # 环境变量覆盖
        self._apply_env_overrides()

        # 命令行参数覆盖
        if cli_overrides:
            self._apply_cli_overrides(cli_overrides)

    def _apply_env_overrides(self) -> None:
        """用环境变量覆盖配置。"""
        env_map = {
            "DEEPSEEK_API_KEY": ("llm", "api_key"),
            "DEEPSEEK_BASE_URL": ("llm", "base_url"),
            "DEEPSEEK_MODEL": ("llm", "model"),
        }
        for env_var, (section, key) in env_map.items():
            value = os.environ.get(env_var)
            if value:
                self._data[section][key] = value

    def _apply_cli_overrides(self, overrides: dict) -> None:
        """用命令行参数覆盖配置。"""
        for key, value in overrides.items():
            if value is None:
                continue
            # 扁平 key "llm.model" → 嵌套
            if "." in key:
                section, subkey = key.split(".", 1)
                if section in self._data:
                    if "." in subkey:
                        # 二级嵌套: "llm.model.name" — 暂不处理
                        pass
                    else:
                        self._data[section][subkey] = value
            elif key == "dimensions" and value:
                self._data["review"]["dimensions"] = (
                    value.split(",") if isinstance(value, str) else value
                )
            elif key == "format" and value:
                self._data["output"]["format"] = value
            elif key == "no_color" and value:
                self._data["output"]["color"] = False

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """获取配置值。"""
        return self._data.get(section, {}).get(key, default)

    @property
    def llm(self) -> dict:
        return self._data.get("llm", {})

    @property
    def review(self) -> dict:
        return self._data.get("review", {})

    @property
    def output(self) -> dict:
        return self._data.get("output", {})

    def to_dict(self) -> dict:
        return self._data.copy()

    def display(self) -> str:
        """返回配置的 YAML 显示字符串。"""
        return yaml.dump(self._data, allow_unicode=True, default_flow_style=False)
