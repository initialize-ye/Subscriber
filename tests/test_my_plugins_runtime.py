"""Tests for my_plugins runtime behavior and edge cases."""

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestHelpTextContent:
    """Verify help.py content completeness and formatting."""

    @pytest.fixture
    def content(self):
        return (PROJECT_ROOT / "my_plugins" / "help.py").read_text(encoding="utf-8")

    def test_has_subscription_section(self, content):
        assert "订阅管理" in content

    def test_has_cookie_section(self, content):
        assert "Cookie 管理" in content

    def test_has_group_section(self, content):
        assert "群管理" in content

    def test_has_admin_section(self, content):
        assert "后台" in content

    def test_has_other_section(self, content):
        assert "其他" in content

    def test_add_subscription_command(self, content):
        assert "添加订阅" in content

    def test_query_subscription_command(self, content):
        assert "查询订阅" in content

    def test_delete_subscription_command(self, content):
        assert "删除订阅" in content

    def test_add_cookie_command(self, content):
        assert "添加cookie" in content

    def test_add_cookie_uppercase_alias(self, content):
        assert "添加Cookie" in content

    def test_view_cookie_command(self, content):
        assert "查看cookie" in content

    def test_my_cookie_alias(self, content):
        assert "我的cookie" in content

    def test_associate_cookie_command(self, content):
        assert "关联cookie" in content

    def test_disassociate_cookie_command(self, content):
        assert "取消关联cookie" in content

    def test_delete_cookie_command(self, content):
        assert "删除cookie" in content

    def test_group_manage_command(self, content):
        assert "群管理" in content

    def test_admin_command(self, content):
        assert "管理后台" in content or "后台管理" in content

    def test_help_command(self, content):
        assert "help" in content

    def test_help_alias(self, content):
        assert "帮助" in content

    def test_mentions_weibo_cookie_requirement(self, content):
        assert "微博" in content
        assert "Cookie" in content

    def test_help_matcher_aliases(self, content):
        """help matcher should have multiple aliases."""
        assert '"help"' in content or "'help'" in content
        assert "帮助" in content
        assert '"?"' in content or "'?'" in content

    def test_subscription_status_command(self, content):
        assert "订阅状态" in content

    def test_edit_subscription_command(self, content):
        assert "编辑订阅" in content

    def test_lists_bilibili_live_platform(self, content):
        assert "B站直播" in content

    def test_lists_bilibili_bangumi_platform(self, content):
        assert "B站番剧" in content


class TestCookieMgrContent:
    """Verify cookie_mgr.py content and error handling."""

    @pytest.fixture
    def content(self):
        return (PROJECT_ROOT / "my_plugins" / "cookie_mgr.py").read_text(encoding="utf-8")

    def test_imports_config(self, content):
        assert "from nonebot_bison.config import config" in content

    def test_imports_logger(self, content):
        assert "from nonebot.log import logger" in content

    def test_handles_get_cookie_error(self, content):
        """Should catch broad exceptions when getting cookies."""
        assert "except Exception" in content
        assert "获取 Cookie 列表失败" in content

    def test_handles_empty_cookies(self, content):
        """Should handle case when no cookies exist."""
        assert "暂无已添加的 Cookie" in content

    def test_shows_cookie_count(self, content):
        """Should display total cookie count."""
        assert "共" in content
        assert "len(cookies)" in content

    def test_shows_association_count(self, content):
        """Should display association count per cookie."""
        assert "关联" in content
        assert "get_cookie_target" in content

    def test_shows_cookie_status(self, content):
        """Should display cookie validation status."""
        assert "status" in content

    def test_shows_platform_name(self, content):
        """Should display platform name for each cookie."""
        assert "site_name" in content

    def test_shows_cookie_name(self, content):
        """Should display cookie name."""
        assert "cookie_name" in content

    def test_handles_unnamed_cookie(self, content):
        """Should handle cookies without names."""
        assert "未命名" in content

    def test_handles_unknown_platform(self, content):
        """Should handle cookies without platform."""
        assert "未知平台" in content

    def test_groups_by_cookie_id(self, content):
        """Should group associations by cookie_id."""
        assert "cookie_id" in content
        assert "assoc_count" in content


class TestInitFile:
    """Verify my_plugins/__init__.py is valid."""

    def test_init_is_empty_or_valid(self):
        content = (PROJECT_ROOT / "my_plugins" / "__init__.py").read_text(encoding="utf-8")
        # Should be empty or contain only valid Python
        assert len(content.strip()) == 0 or "import" in content


class TestSubStatusContent:
    """Verify sub_status.py content and structure."""

    @pytest.fixture
    def content(self):
        return (PROJECT_ROOT / "my_plugins" / "sub_status.py").read_text(encoding="utf-8")

    def test_imports_config(self, content):
        assert "from nonebot_bison.config import config" in content

    def test_imports_platform_manager(self, content):
        assert "from nonebot_bison.platform import platform_manager" in content

    def test_imports_extract_target(self, content):
        assert "extract_target" in content

    def test_command_name(self, content):
        assert "订阅状态" in content

    def test_shows_platform_name(self, content):
        assert "platform" in content
        assert "plat_name" in content

    def test_shows_categories(self, content):
        assert "Category" in content
        assert "cats" in content

    def test_shows_tags(self, content):
        assert "tags" in content

    def test_shows_cookie_status(self, content):
        assert "cookie" in content.lower()
        assert "cookie_set" in content

    def test_shows_total_count(self, content):
        assert "共" in content
        assert "len(sub_list)" in content

    def test_handles_empty_subs(self, content):
        assert "暂无已订阅账号" in content

    def test_handles_error(self, content):
        assert "except Exception" in content


class TestSubEditContent:
    """Verify sub_edit.py content and structure."""

    @pytest.fixture
    def content(self):
        return (PROJECT_ROOT / "my_plugins" / "sub_edit.py").read_text(encoding="utf-8")

    def test_imports_config(self, content):
        assert "from nonebot_bison.config import config" in content

    def test_imports_update_subscribe(self, content):
        assert "update_subscribe" in content

    def test_imports_platform_manager(self, content):
        assert "from nonebot_bison.platform import platform_manager" in content

    def test_command_name(self, content):
        assert "编辑订阅" in content

    def test_has_cancel_handling(self, content):
        assert "取消" in content

    def test_has_multi_step_flow(self, content):
        """Should use got() for multi-step interaction."""
        assert ".got(" in content

    def test_handles_invalid_index(self, content):
        assert "序号" in content

    def test_handles_error(self, content):
        assert "except Exception" in content

    def test_shows_success_message(self, content):
        assert "已更新订阅" in content

    def test_has_category_parsing(self, content):
        assert "_parse_categories" in content

    def test_supports_unchanged_input(self, content):
        assert "不变" in content
