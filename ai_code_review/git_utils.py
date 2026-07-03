"""Git 操作工具模块。

通过 subprocess 调用 git 命令，提供 diff 获取和文件操作功能。
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional


class GitError(Exception):
    """Git 操作异常。"""

    pass


def _run_git(args: list[str], cwd: Optional[Path] = None) -> str:
    """执行 git 命令并返回 stdout。

    Args:
        args: git 命令参数列表 (不含 'git')
        cwd: 工作目录，默认当前目录

    Returns:
        命令的 stdout 输出

    Raises:
        GitError: git 命令失败或不在 git 仓库中
    """
    cmd = ["git"] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=cwd,
            # Windows 下避免控制台弹窗
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            check=False,
        )
    except FileNotFoundError:
        raise GitError(
            "未找到 git 命令。请确认 git 已安装并在 PATH 中。"
        )

    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "not a git repository" in stderr.lower():
            raise GitError("当前目录不在 Git 仓库中。请在 Git 项目内运行此命令。")
        raise GitError(f"git 命令失败: {' '.join(cmd)}\n{stderr}")

    return result.stdout


def is_git_repo(cwd: Optional[Path] = None) -> bool:
    """检查当前目录是否在 Git 仓库中。"""
    try:
        _run_git(["rev-parse", "--git-dir"], cwd=cwd)
        return True
    except GitError:
        return False


def get_unstaged_diff(cwd: Optional[Path] = None) -> str:
    """获取工作区未暂存的改动 (git diff)。"""
    return _run_git(["diff"], cwd=cwd)


def get_staged_diff(cwd: Optional[Path] = None) -> str:
    """获取已暂存但未提交的改动 (git diff --cached)。"""
    return _run_git(["diff", "--cached"], cwd=cwd)


def get_all_uncommitted_diff(cwd: Optional[Path] = None) -> str:
    """获取所有未提交的改动 (暂存 + 未暂存)。"""
    staged = get_staged_diff(cwd)
    unstaged = get_unstaged_diff(cwd)
    if staged and unstaged:
        return staged + "\n" + unstaged
    return staged or unstaged


def get_commit_diff(commit: str, cwd: Optional[Path] = None) -> str:
    """获取指定 commit 的 diff。

    Args:
        commit: commit 引用，如 HEAD~1, abc1234
    """
    return _run_git(["diff", f"{commit}..HEAD"], cwd=cwd)


def get_file_content(filepath: str, cwd: Optional[Path] = None) -> str:
    """读取文件内容（不限于 git 跟踪的文件）。

    Args:
        filepath: 文件路径（相对或绝对）
    """
    target = Path(cwd or Path.cwd()) / filepath
    if not target.exists():
        raise GitError(f"文件不存在: {filepath}")
    if not target.is_file():
        raise GitError(f"路径不是文件: {filepath}")
    return target.read_text(encoding="utf-8", errors="replace")


def get_tracked_files(cwd: Optional[Path] = None) -> list[str]:
    """获取 git 跟踪的文件列表。"""
    output = _run_git(["ls-files"], cwd=cwd)
    return [f for f in output.strip().split("\n") if f]


def get_diff_for_files(filepaths: list[str], staged: bool = False, cwd: Optional[Path] = None) -> str:
    """获取指定文件的 diff。

    Args:
        filepaths: 文件路径列表
        staged: True 获取暂存区 diff，False 获取工作区 diff
    """
    args = ["diff"]
    if staged:
        args.append("--cached")
    args.append("--")
    args.extend(filepaths)
    return _run_git(args, cwd=cwd)


def get_diff_stats(diff: str) -> dict:
    """解析 diff 统计信息。

    Returns:
        dict with keys: files_changed, insertions, deletions
    """
    if not diff.strip():
        return {"files_changed": 0, "insertions": 0, "deletions": 0}

    files = set()
    insertions = 0
    deletions = 0

    for line in diff.split("\n"):
        if line.startswith("diff --git"):
            # 提取文件名
            parts = line.split(" ")
            if len(parts) >= 4:
                # 格式: diff --git a/path b/path
                files.add(parts[3].replace("b/", "", 1))
        elif line.startswith("+") and not line.startswith("+++"):
            insertions += 1
        elif line.startswith("-") and not line.startswith("---"):
            deletions += 1

    return {
        "files_changed": len(files),
        "insertions": insertions,
        "deletions": deletions,
    }


def get_changed_files(cwd: Optional[Path] = None) -> list[str]:
    """获取工作区有改动的文件列表。"""
    output = _run_git(["diff", "--name-only"], cwd=cwd)
    staged_output = _run_git(["diff", "--name-only", "--cached"], cwd=cwd)
    files = set()
    if output.strip():
        files.update(output.strip().split("\n"))
    if staged_output.strip():
        files.update(staged_output.strip().split("\n"))
    return sorted(files)
