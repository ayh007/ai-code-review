"""Git 工具模块测试。"""

import pytest
from pathlib import Path

from ai_code_review import git_utils


class TestGetDiffStats:
    """测试 get_diff_stats 函数。"""

    def test_empty_diff(self):
        """空 diff 应返回全零统计。"""
        stats = git_utils.get_diff_stats("")
        assert stats == {"files_changed": 0, "insertions": 0, "deletions": 0}

    def test_single_file_diff(self):
        """单文件 diff 统计。"""
        diff = """diff --git a/test.py b/test.py
index abc123..def456 100644
--- a/test.py
+++ b/test.py
@@ -1,3 +1,4 @@
-old line
+new line 1
+new line 2
 unchanged
-newly removed"""
        stats = git_utils.get_diff_stats(diff)
        assert stats["files_changed"] == 1
        assert stats["insertions"] == 2
        assert stats["deletions"] == 2

    def test_multi_file_diff(self):
        """多文件 diff 统计。"""
        diff = """diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
+added
diff --git a/b.py b/b.py
--- a/b.py
+++ b/b.py
-removed"""
        stats = git_utils.get_diff_stats(diff)
        assert stats["files_changed"] == 2
        assert stats["insertions"] == 1
        assert stats["deletions"] == 1


class TestIsGitRepo:
    """测试 is_git_repo。"""

    def test_not_git_repo(self, tmp_path):
        """非 git 仓库应返回 False。"""
        assert git_utils.is_git_repo(cwd=tmp_path) is False


class TestGitError:
    """测试 GitError 异常。"""

    def test_file_not_found(self):
        """读取不存在的文件应抛出 GitError。"""
        with pytest.raises(git_utils.GitError, match="文件不存在"):
            git_utils.get_file_content("__nonexistent_file_xyz__.py")
