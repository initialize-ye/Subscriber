"""Tests for bot.py — verify configuration and initialization."""

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BOT_FILE = PROJECT_ROOT / "bot.py"


class TestBotConfig:
    """Verify bot.py configuration and structure."""

    @pytest.fixture
    def source(self):
        return BOT_FILE.read_text(encoding="utf-8")

    def test_imports_dotenv(self, source):
        assert "from dotenv import load_dotenv" in source

    def test_imports_nonebot(self, source):
        assert "import nonebot" in source

    def test_imports_onebot_adapter(self, source):
        assert "OneBotV11Adapter" in source

    def test_loads_dotenv_before_init(self, source):
        """load_dotenv() must be called before nonebot.init()."""
        dotenv_pos = source.find("load_dotenv()")
        init_pos = source.find("nonebot.init()")
        assert dotenv_pos < init_pos, "load_dotenv() must come before nonebot.init()"

    def test_registers_onebot_adapter(self, source):
        assert "register_adapter(OneBotV11Adapter)" in source

    def test_loads_apscheduler_first(self, source):
        """apscheduler must load before bison (bison depends on it)."""
        aps_pos = source.find("nonebot_plugin_apscheduler")
        bison_pos = source.find("nonebot_bison")
        assert aps_pos < bison_pos, "apscheduler must load before bison"

    def test_loads_bison_before_my_plugins(self, source):
        """bison must load before my_plugins (they import from bison)."""
        bison_pos = source.find("nonebot_bison")
        plugins_pos = source.find('nonebot.load_plugins("my_plugins")')
        assert bison_pos < plugins_pos, "bison must load before my_plugins"

    def test_has_main_function(self, source):
        assert "def main() -> None:" in source

    def test_has_if_name_main(self, source):
        assert 'if __name__ == "__main__":' in source

    def test_calls_nonebot_run(self, source):
        assert "nonebot.run()" in source


class TestEnvExample:
    """Verify .env.example has all required keys."""

    @pytest.fixture
    def env_content(self):
        return (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")

    def test_has_host(self, env_content):
        assert "HOST=" in env_content

    def test_has_port(self, env_content):
        assert "PORT=" in env_content

    def test_has_access_token(self, env_content):
        assert "ONEBOT_ACCESS_TOKEN=" in env_content

    def test_has_superusers(self, env_content):
        assert "SUPERUSERS=" in env_content

    def test_has_db_dir(self, env_content):
        assert "BISON_DB_DIR=" in env_content

    def test_has_use_browser(self, env_content):
        assert "BISON_USE_BROWSER=" in env_content

    def test_has_browser_ua(self, env_content):
        assert "BISON_BROWSER_UA=" in env_content


class TestGitignore:
    """Verify .gitignore protects sensitive files."""

    @pytest.fixture
    def gitignore(self):
        return (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")

    def test_ignores_env(self, gitignore):
        assert ".env" in gitignore

    def test_ignores_venv(self, gitignore):
        assert ".venv" in gitignore or "venv" in gitignore

    def test_ignores_data(self, gitignore):
        assert "data" in gitignore or "data/" in gitignore

    def test_ignores_pycache(self, gitignore):
        assert "__pycache__" in gitignore
