"""Tests for patch_bison.py — verify patches apply correctly and are idempotent."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PATCH_SCRIPT = PROJECT_ROOT / "patch_bison.py"


class TestPatchBisonRuns:
    """Verify patch_bison.py executes without errors."""

    def test_patch_runs_successfully(self):
        result = subprocess.run(
            [sys.executable, str(PATCH_SCRIPT)],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0, f"patch_bison.py failed:\n{result.stdout}\n{result.stderr}"
        assert "All patches applied!" in result.stdout

    def test_patch_is_idempotent(self):
        """Running twice should produce the same result."""
        r1 = subprocess.run(
            [sys.executable, str(PATCH_SCRIPT)],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        r2 = subprocess.run(
            [sys.executable, str(PATCH_SCRIPT)],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        assert r1.returncode == 0
        assert r2.returncode == 0
        # Compare non-timestamp output lines
        lines1 = [l for l in r1.stdout.splitlines() if "patched" not in l.lower()]
        lines2 = [l for l in r2.stdout.splitlines() if "patched" not in l.lower()]
        assert lines1 == lines2


class TestPatchedFilesSyntax:
    """Verify all patched Python files have valid syntax."""

    PATCHED_FILES = [
        "metrics.py",
        "platform/weibo.py",
        "platform/bilibili/platforms.py",
        "platform/bilibili/scheduler.py",
        "sub_manager/__init__.py",
        "sub_manager/add_cookie.py",
        "sub_manager/del_sub.py",
        "sub_manager/del_cookie.py",
        "sub_manager/del_cookie_target.py",
        "sub_manager/add_cookie_target.py",
        "sub_manager/add_sub.py",
        "sub_manager/query_sub.py",
        "sub_manager/utils.py",
        "config/db_config.py",
        "utils/site.py",
        "utils/context.py",
        "utils/__init__.py",
        "admin_page/jwt.py",
    ]

    @pytest.fixture(autouse=True)
    def _run_patch_first(self):
        subprocess.run(
            [sys.executable, str(PATCH_SCRIPT)],
            capture_output=True, cwd=str(PROJECT_ROOT),
        )

    @pytest.mark.parametrize("rel_path", PATCHED_FILES)
    def test_syntax_valid(self, rel_path, bison_base):
        full_path = os.path.join(bison_base, rel_path)
        assert os.path.isfile(full_path), f"File not found: {rel_path}"
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", full_path],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"Syntax error in {rel_path}:\n{result.stderr}"


class TestCriticalBugFixes:
    """Verify specific critical bug fixes are present in patched files."""

    @pytest.fixture(autouse=True)
    def _run_patch_first(self):
        subprocess.run(
            [sys.executable, str(PATCH_SCRIPT)],
            capture_output=True, cwd=str(PROJECT_ROOT),
        )

    def test_del_sub_has_logger_import(self, bison_base, read_file):
        content = read_file(os.path.join(bison_base, "sub_manager/del_sub.py"))
        assert "from nonebot.log import logger" in content

    def test_del_cookie_has_logger_import(self, bison_base, read_file):
        content = read_file(os.path.join(bison_base, "sub_manager/del_cookie.py"))
        assert "from nonebot.log import logger" in content

    def test_del_cookie_target_has_logger_import(self, bison_base, read_file):
        content = read_file(os.path.join(bison_base, "sub_manager/del_cookie_target.py"))
        assert "from nonebot.log import logger" in content

    def test_del_sub_has_value_error_handler(self, bison_base, read_file):
        content = read_file(os.path.join(bison_base, "sub_manager/del_sub.py"))
        assert "except ValueError:" in content
        assert "请输入正确的数字序号" in content

    def test_del_cookie_has_value_error_handler(self, bison_base, read_file):
        content = read_file(os.path.join(bison_base, "sub_manager/del_cookie.py"))
        assert "except ValueError:" in content

    def test_del_cookie_target_has_value_error_handler(self, bison_base, read_file):
        content = read_file(os.path.join(bison_base, "sub_manager/del_cookie_target.py"))
        assert "except ValueError:" in content

    def test_group_manage_has_value_error_handler(self, bison_base, read_file):
        content = read_file(os.path.join(bison_base, "sub_manager/__init__.py"))
        assert "except ValueError:" in content
        assert "timedelta" in content

    def test_weibo_parse_target_anchored(self, bison_base, read_file):
        content = read_file(os.path.join(bison_base, "platform/weibo.py"))
        assert 'r"^\\d+$"' in content or "r'^\\d+$'" in content

    def test_weibo_long_text_guarded(self, bison_base, read_file):
        content = read_file(os.path.join(bison_base, "platform/weibo.py"))
        assert '"longTextContent" in long_data' in content

    def test_weibo_br_xpath_fixed(self, bison_base, read_file):
        content = read_file(os.path.join(bison_base, "platform/weibo.py"))
        assert 'xpath("//br")' in content
        assert "if br.tail:" in content

    def test_bilibili_parse_target_anchored(self, bison_base, read_file):
        content = read_file(os.path.join(bison_base, "platform/bilibili/platforms.py"))
        assert 'r"^\\d+$"' in content

    def test_bilibili_bangumi_fallback_is_dict(self, bison_base, read_file):
        content = read_file(os.path.join(bison_base, "platform/bilibili/platforms.py"))
        assert 'episodes"][0]' in content
        # Should NOT have multiple [0] appended
        assert 'episodes"][0][0]' not in content

    def test_db_config_del_subscribe_null_check(self, bison_base, read_file):
        content = read_file(os.path.join(bison_base, "config/db_config.py"))
        assert "if not user_obj or not target_obj:" in content

    def test_db_config_update_subscribe_null_check(self, bison_base, read_file):
        content = read_file(os.path.join(bison_base, "config/db_config.py"))
        assert "if not subscribe_obj:" in content

    def test_db_config_weight_config_fixed(self, bison_base, read_file):
        content = read_file(os.path.join(bison_base, "config/db_config.py"))
        assert "target.target not in res[platform_name]" in content

    def test_cookie_target_orphan_filtered(self, bison_base, read_file):
        content = read_file(os.path.join(bison_base, "config/db_config.py"))
        assert "x.target is not None" in content

    def test_choose_cookie_handles_empty_list(self, bison_base, read_file):
        content = read_file(os.path.join(bison_base, "utils/site.py"))
        assert "if not available_cookies:" in content

    def test_should_print_content_handles_missing_header(self, bison_base, read_file):
        content = read_file(os.path.join(bison_base, "utils/context.py"))
        assert 'r.headers.get("content-type", "")' in content

    def test_bilibili_scheduler_handles_empty_cookies(self, bison_base, read_file):
        content = read_file(os.path.join(bison_base, "platform/bilibili/scheduler.py"))
        assert "if not anon_cookies:" in content

    def test_jwt_uses_timezone_aware_utc(self, bison_base, read_file):
        content = read_file(os.path.join(bison_base, "admin_page/jwt.py"))
        assert "datetime.timezone.utc" in content
        assert "utcnow" not in content

    def test_metrics_has_dummy_classes(self, bison_base, read_file):
        content = read_file(os.path.join(bison_base, "metrics.py"))
        assert "class _DummyMetric" in content
        assert "Counter = _DummyMetric" in content

    def test_utils_error_message_is_chinese(self, bison_base, read_file):
        content = read_file(os.path.join(bison_base, "sub_manager/utils.py"))
        assert "未设置目标用户信息" in content
        assert "this shouldn't happen" not in content

    def test_subscription_count_present(self, bison_base, read_file):
        query = read_file(os.path.join(bison_base, "sub_manager/query_sub.py"))
        delete = read_file(os.path.join(bison_base, "sub_manager/del_sub.py"))
        assert "共 {len(sub_list)} 个订阅" in query
        assert "共 {len(sub_list)} 个订阅" in delete

    def test_subscription_count_not_duplicated(self, bison_base, read_file):
        query = read_file(os.path.join(bison_base, "sub_manager/query_sub.py"))
        delete = read_file(os.path.join(bison_base, "sub_manager/del_sub.py"))
        assert query.count("共 {len(sub_list)} 个订阅") == 1
        assert delete.count("共 {len(sub_list)} 个订阅") == 1

    def test_privacy_warning_present(self, bison_base, read_file):
        content = read_file(os.path.join(bison_base, "sub_manager/add_cookie.py"))
        assert "明文显示" in content

    def test_add_cookie_target_specific_exceptions(self, bison_base, read_file):
        content = read_file(os.path.join(bison_base, "sub_manager/add_cookie_target.py"))
        assert "except (ValueError, KeyError, IndexError):" in content
        assert 'except Exception:' not in content

    def test_bilibili_live_disabled(self, bison_base, read_file):
        content = read_file(os.path.join(bison_base, "platform/bilibili/platforms.py"))
        # Find bilibili-live section and check enabled = False
        idx = content.find('platform_name = "bilibili-live"')
        if idx == -1:
            pytest.skip("bilibili-live not found")
        segment = content[idx:idx + 200]
        assert "enabled = False" in segment

    def test_bilibili_bangumi_disabled(self, bison_base, read_file):
        content = read_file(os.path.join(bison_base, "platform/bilibili/platforms.py"))
        idx = content.find('platform_name = "bilibili-bangumi"')
        if idx == -1:
            pytest.skip("bilibili-bangumi not found")
        segment = content[idx:idx + 200]
        assert "enabled = False" in segment

    def test_weibo_proxy_configured(self, bison_base, read_file):
        content = read_file(os.path.join(bison_base, "platform/weibo.py"))
        assert 'proxy="http://127.0.0.1:7890"' in content

    def test_expire_time_not_immediate(self, bison_base, read_file):
        content = read_file(os.path.join(bison_base, "sub_manager/__init__.py"))
        assert "expire_time=datetime.now() + timedelta(minutes=5)" in content
        # Should NOT have multiple timedelta additions
        assert "timedelta(minutes=5) + timedelta" not in content

    def test_weight_config_no_assert(self, bison_base, read_file):
        content = read_file(os.path.join(bison_base, "config/db_config.py"))
        # assert is stripped by -O flag, should use proper null check
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if "assert targetObj" in line:
                pytest.fail(f"assert targetObj found at line {i+1}, should be a proper null check")

    def test_weight_config_has_null_check(self, bison_base, read_file):
        content = read_file(os.path.join(bison_base, "config/db_config.py"))
        assert "if not targetObj:" in content

    def test_http_432_message_generic(self, bison_base, read_file):
        content = read_file(os.path.join(bison_base, "sub_manager/add_cookie.py"))
        # Should NOT have Weibo-specific message in generic handler
        assert "微博 API 拒绝了" not in content
        # Should have generic message
        assert "HTTP 432" in content
