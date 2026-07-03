"""CLI 入口模块。

使用 click 框架提供命令行接口。
"""

import sys
import io
from pathlib import Path
from typing import Optional

import click

# Windows 下修复 Unicode 输出问题（如 emoji 在 GBK 终端中报错）
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace"
    )
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding="utf-8", errors="replace"
    )

from .config import Config
from . import git_utils
from .reviewer import Reviewer
from .llm_client import LLMError
from .formatters import terminal as terminal_fmt
from .formatters import markdown as markdown_fmt
from .formatters import json_fmt as json_formatter


# ── 常量 ──

DIMENSION_CHOICES = ["bugs", "security", "performance", "style"]
OUTPUT_CHOICES = ["terminal", "markdown", "json"]

CONTEXT_SETTINGS = dict(
    help_option_names=["-h", "--help"],
    max_content_width=100,
)


def _print_banner():
    """在终端输出打印 ASCII banner。"""
    banner = r"""
    ╔══════════════════════════════════════╗
    ║     🔍  AI Code Review (ACR)        ║
    ║     DeepSeek-powered code reviewer  ║
    ╚══════════════════════════════════════╝
    """
    click.echo(banner)


def _validate_dimensions(ctx, param, value: Optional[str]) -> Optional[list[str]]:
    """验证并解析维度参数。"""
    if value is None:
        return None
    dims = [d.strip() for d in value.split(",")]
    invalid = [d for d in dims if d not in DIMENSION_CHOICES]
    if invalid:
        raise click.BadParameter(
            f"无效的维度: {', '.join(invalid)}。可选: {', '.join(DIMENSION_CHOICES)}"
        )
    return dims


# ── 主命令组 ──


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(version="1.0.0", prog_name="acr")
@click.pass_context
def main(ctx):
    """🔍 AI Code Review — DeepSeek 驱动的代码审查 CLI 工具。

    审查 Git 工作区的改动，发现 Bug、安全隐患、性能问题和代码风格问题。

    \b
    快速开始:
      1. 设置 API Key:  export DEEPSEEK_API_KEY=sk-xxx
      2. 审查未提交改动:  acr review
      3. 审查暂存改动:    acr review --staged
      4. 查看配置:        acr config
    """
    # 确保 ctx.obj 存在
    ctx.ensure_object(dict)


# ── review 子命令 ──


@main.command("review")
@click.argument("target", required=False, default=None)
@click.option(
    "--staged", is_flag=True,
    help="只审查已暂存 (git add) 的改动。",
)
@click.option(
    "--commit", "-c", "commit_ref",
    default=None,
    help="审查指定 commit 的 diff，如 HEAD~1。",
)
@click.option(
    "--dir", "-D", "directory",
    default=None,
    help="审查指定目录下的所有文件。",
)
@click.option(
    "--diff", "-d", "inline_diff",
    default=None,
    help="直接传入 diff 文本进行审查。",
)
@click.option(
    "--dimensions", "-dims",
    default=None,
    callback=_validate_dimensions,
    help=f"审查维度，逗号分隔。可选: {', '.join(DIMENSION_CHOICES)}（默认全部）",
)
@click.option(
    "--output", "-o",
    default=None,
    type=click.Choice(OUTPUT_CHOICES),
    help="输出格式（默认: terminal）。markdown/json 适合 CI 集成。",
)
@click.option(
    "--model", "-m",
    default=None,
    help="DeepSeek 模型名称（默认: deepseek-chat）。",
)
@click.option(
    "--language", "-l",
    default="auto",
    help="目标编程语言，用于辅助审查（默认: auto）。",
)
@click.option(
    "--max-tokens",
    default=4096,
    type=int,
    help="LLM 单次响应最大 token 数（默认: 4096）。",
)
@click.option(
    "--no-color", is_flag=True,
    help="禁用彩色输出。",
)
@click.option(
    "--save", "-s",
    default=None,
    help="将报告保存到指定文件路径。",
)
@click.pass_context
def review_cmd(
    ctx,
    target: Optional[str],
    staged: bool,
    commit_ref: Optional[str],
    directory: Optional[str],
    inline_diff: Optional[str],
    dimensions: Optional[list[str]],
    output: Optional[str],
    model: Optional[str],
    language: str,
    max_tokens: int,
    no_color: bool,
    save: Optional[str],
):
    """审查代码改动。

    TARGET: 可选，指定要审查的文件路径。
    不指定时，审查所有未提交的改动。
    """
    # ── 构建配置 ──
    cli_overrides = {
        "dimensions": dimensions,
        "format": output,
        "no_color": no_color,
    }
    if model:
        cli_overrides["llm.model"] = model

    try:
        config = Config(cli_overrides=cli_overrides)
    except Exception as e:
        click.echo(f"❌ 配置加载失败: {e}", err=True)
        sys.exit(1)

    # ── 确定输出格式 ──
    output_format = output or config.output.get("format", "terminal")

    # ── 获取 diff ──
    try:
        diff = _get_diff(target, staged, commit_ref, directory, inline_diff)
    except git_utils.GitError as e:
        click.echo(f"❌ {e}", err=True)
        sys.exit(1)

    if not diff or not diff.strip():
        click.echo("⚠️  没有发现代码改动。")
        click.echo("  提示: 使用 --staged 审查已暂存的改动，或 --commit HEAD~1 审查上次提交。")
        return

    # ── 统计信息 ──
    diff_stats = git_utils.get_diff_stats(diff)

    # ── 执行审查 ──
    if output_format == "terminal":
        click.echo(f"🔍 正在审查... ({diff_stats['files_changed']} 个文件, "
                   f"+{diff_stats['insertions']} -{diff_stats['deletions']})")
        click.echo(f"   维度: {', '.join(dimensions) if dimensions else '全部'}")
        click.echo(f"   模型: {model or config.llm.get('model', 'deepseek-chat')}")
        click.echo()

    try:
        reviewer = Reviewer(config)
        findings = reviewer.review(
            diff=diff,
            dimensions=dimensions,
            language=language,
            max_tokens=max_tokens,
        )
    except LLMError as e:
        click.echo(f"❌ LLM 调用失败: {e}", err=True)
        sys.exit(1)

    # ── 格式化输出 ──
    model_name = model or config.llm.get("model", "deepseek-chat")

    if output_format == "terminal":
        result = terminal_fmt.format_findings(
            findings,
            diff_stats=diff_stats,
            model=model_name,
            color=not no_color,
        )
        click.echo(result)

    elif output_format == "markdown":
        result = markdown_fmt.format_findings(
            findings,
            diff_stats=diff_stats,
            model=model_name,
        )
        if save:
            markdown_fmt.save_report(findings, save, diff_stats=diff_stats, model=model_name)
            click.echo(f"📄 报告已保存到: {save}")
        else:
            click.echo(result)

    elif output_format == "json":
        result = json_formatter.format_findings(
            findings,
            diff_stats=diff_stats,
            model=model_name,
        )
        if save:
            with open(save, "w", encoding="utf-8") as f:
                f.write(result)
            click.echo(f"📄 报告已保存到: {save}")
        else:
            click.echo(result)

    # ── 退出码：有问题时非零 ──
    critical_count = sum(1 for f in findings if f.get("severity") == "critical")
    if critical_count > 0:
        sys.exit(1)


# ── config 子命令 ──


@main.command("config")
@click.option("--init", is_flag=True, help="在当前目录创建 .acr.yml 配置文件。")
@click.option("--set", "set_value", default=None, help="设置配置项，如: acr config --set llm.model deepseek-chat")
@click.option("--get", "get_key", default=None, help="获取配置项的值")
@click.option("--path", is_flag=True, help="显示当前使用的配置文件路径")
def config_cmd(init: bool, set_value: Optional[str], get_key: Optional[str], path: bool):
    """管理 AI Code Review 配置。"""

    if init:
        _init_config()
        return

    if path:
        _show_config_path()
        return

    if set_value:
        click.echo(f"⚠️  手动编辑配置文件以设置: {set_value}")
        click.echo(f"   配置文件位置: {_find_or_suggest_path()}")
        return

    if get_key:
        try:
            config = Config()
            if "." in get_key:
                section, key = get_key.split(".", 1)
                value = config.get(section, key)
            click.echo(f"{get_key} = {value}")
        except Exception as e:
            click.echo(f"❌ 获取配置失败: {e}", err=True)
        return

    # 默认：显示所有配置
    try:
        config = Config()
        click.echo(config.display())
    except Exception as e:
        click.echo(f"❌ 加载配置失败: {e}", err=True)


# ── 辅助函数 ──


def _get_diff(
    target: Optional[str],
    staged: bool,
    commit_ref: Optional[str],
    directory: Optional[str],
    inline_diff: Optional[str],
) -> str:
    """根据不同参数获取 diff。"""
    if inline_diff:
        return inline_diff

    if target:
        # 指定文件
        if not Path(target).exists():
            raise git_utils.GitError(f"文件不存在: {target}")
        return git_utils.get_file_content(target)

    if commit_ref:
        return git_utils.get_commit_diff(commit_ref)

    if directory:
        files = git_utils.get_changed_files()
        dir_files = [f for f in files if f.startswith(directory)]
        if not dir_files:
            raise git_utils.GitError(f"目录 '{directory}' 中没有发现改动的文件。")
        return git_utils.get_diff_for_files(dir_files, staged=staged)

    if staged:
        return git_utils.get_staged_diff()

    return git_utils.get_all_uncommitted_diff()


def _init_config():
    """创建默认的 .acr.yml 配置文件。"""
    config_path = Path.cwd() / ".acr.yml"
    if config_path.exists():
        click.echo(f"⚠️  配置文件已存在: {config_path}")
        if not click.confirm("是否覆盖？"):
            return

    template = """\
# AI Code Review 配置
# 详见: https://github.com/yourname/ai-code-review

llm:
  api_key: ${DEEPSEEK_API_KEY}
  base_url: https://api.deepseek.com
  model: deepseek-chat

review:
  dimensions:
    - bugs
    - security
    - performance
    - style
  exclude_patterns:
    - "*.lock"
    - "*.pyc"
  max_file_size: 100000
  max_diff_size: 50000

output:
  format: terminal
  color: true
"""
    config_path.write_text(template, encoding="utf-8")
    click.echo(f"✅ 配置文件已创建: {config_path}")
    click.echo("   请编辑此文件并设置你的 API Key。")


def _show_config_path():
    """显示配置文件路径。"""
    click.echo(_find_or_suggest_path())


def _find_or_suggest_path() -> str:
    """查找或建议配置文件路径。"""
    project_config = Path.cwd() / ".acr.yml"
    if project_config.exists():
        return str(project_config)
    user_config = Path.home() / ".acr" / "config.yml"
    if user_config.exists():
        return str(user_config)
    return f"{Path.cwd() / '.acr.yml'} (不存在，使用 acr config --init 创建)"


# ── 入口 ──

if __name__ == "__main__":
    main()
