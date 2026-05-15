"""Tests for my_plugins — verify custom plugin files are valid."""

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestMyPluginsSyntax:
    """Verify all custom plugin files have valid syntax."""

    PLUGIN_FILES = [
        "my_plugins/__init__.py",
        "my_plugins/help.py",
        "my_plugins/cookie_mgr.py",
    ]

    @pytest.mark.parametrize("rel_path", PLUGIN_FILES)
    def test_syntax_valid(self, rel_path):
        full_path = PROJECT_ROOT / rel_path
        assert full_path.exists(), f"File not found: {rel_path}"
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(full_path)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"Syntax error in {rel_path}:\n{result.stderr}"


class TestBotSyntax:
    """Verify bot.py has valid syntax."""

    def test_bot_syntax_valid(self):
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(PROJECT_ROOT / "bot.py")],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"Syntax error in bot.py:\n{result.stderr}"


class TestHelpText:
    """Verify help.py content."""

    def test_help_contains_all_commands(self):
        content = (PROJECT_ROOT / "my_plugins" / "help.py").read_text(encoding="utf-8")
        required = ["添加订阅", "查询订阅", "删除订阅", "添加cookie", "查看cookie", "关联cookie", "删除cookie", "群管理", "help"]
        for cmd in required:
            assert cmd in content, f"Help text missing command: {cmd}"

    def test_help_mentions_cookie_privacy(self):
        content = (PROJECT_ROOT / "my_plugins" / "help.py").read_text(encoding="utf-8")
        assert "Cookie" in content


class TestCookieMgr:
    """Verify cookie_mgr.py content."""

    def test_catches_broad_exception(self):
        content = (PROJECT_ROOT / "my_plugins" / "cookie_mgr.py").read_text(encoding="utf-8")
        assert "except Exception" in content

    def test_shows_association_count(self):
        content = (PROJECT_ROOT / "my_plugins" / "cookie_mgr.py").read_text(encoding="utf-8")
        assert "关联" in content
        assert "get_cookie_target" in content
