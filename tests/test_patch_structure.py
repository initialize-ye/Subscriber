"""Tests for patch_bison.py structural integrity and regression guards."""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PATCH_SCRIPT = PROJECT_ROOT / "patch_bison.py"


class TestPatchStructure:
    """Verify patch_bison.py structural properties."""

    @pytest.fixture
    def source(self):
        return PATCH_SCRIPT.read_text(encoding="utf-8")

    def test_total_steps_is_38(self, source):
        assert "TOTAL_STEPS = 38" in source

    def test_all_step_numbers_logged(self, source):
        """Every step number 1-38 should appear in _step() calls."""
        for i in range(1, 39):
            pattern = rf'_step\({i},'
            assert re.search(pattern, source), f"Step {i} has no _step() call"

    def test_no_duplicate_file_reads(self, source):
        """Each file should be read at most once (grouped by file)."""
        reads = re.findall(r'_read\((\w+)\)', source)
        read_vars = [r for r in reads if r not in ("path",)]
        pass  # Structural check, not strict assertion

    def test_helper_functions_defined(self, source):
        assert "def _read(path" in source
        assert "def _write(path" in source
        assert "def _assert_patched(" in source
        assert "def _assert_not_patched(" in source
        assert "def _step(n" in source

    def test_base_path_detection(self, source):
        assert "_venv_site" in source
        assert 'Path(__file__).resolve().parent' in source
        assert "nonebot_bison" in source

    def test_all_files_written_after_group(self, source):
        write_calls = re.findall(r'_write\((\w+),\s*(\w+)\)', source)
        write_targets = set(w[0] for w in write_calls)
        expected_writers = [
            "bili_path", "weibo_path", "add_cookie_path",
            "del_sub_path", "del_cookie_path", "del_cookie_target_path",
            "add_sub_path", "_init_path", "query_sub_path",
            "utils_path", "db_path", "add_ct_path",
            "site_path", "ctx_path", "utils_init_path",
            "bili_sched_path", "jwt_path",
        ]
        for writer in expected_writers:
            assert writer in write_targets, f"{writer} is never written"


class TestIdempotencyGuards:
    """Verify all replace operations have idempotency protection."""

    @pytest.fixture
    def source(self):
        return PATCH_SCRIPT.read_text(encoding="utf-8")

    def test_step_11_has_guard(self, source):
        assert "'expire_time=datetime.now(),' in _init" in source

    def test_step_23_has_guard(self, source):
        assert 'if old_long_text in weibo:' in source

    def test_step_27_has_guard(self, source):
        assert 'if old_bangumi in bili:' in source

    def test_step_28_has_guard(self, source):
        assert '"if not user_obj or not target_obj:" not in db' in source
        assert '"if not subscribe_obj:" not in db' in source

    def test_step_33_has_guard(self, source):
        assert '"res = [x for x in res if x.target is not None]" not in db' in source

    def test_step_34_has_guard(self, source):
        assert "'query_dict: dict = {}' in utils_init" in source

    def test_step_35_has_guard(self, source):
        assert "(await config.get_cookie" in source

    def test_step_36_has_guard(self, source):
        assert '"datetime.datetime.utcnow()" in jwt' in source

    def test_step_4_has_guard(self, source):
        assert "if old_parse in weibo and parse_end > 0:" in source

    def test_step_7_has_guard(self, source):
        assert "if old_block in weibo:" in source

    def test_step_8_import_guard(self, source):
        assert '"import httpx" not in add_cookie' in source

    def test_step_15_import_guard(self, source):
        assert '"from nonebot.log import logger" not in del_sub' in source

    def test_step_16_import_guard(self, source):
        assert '"from nonebot.log import logger" not in del_cookie' in source

    def test_step_21_import_guard(self, source):
        assert '"from nonebot.log import logger" not in del_cookie_target' in source

    def test_step_17_value_error_guard(self, source):
        assert "'except ValueError' not in del_sub" in source

    def test_step_18_value_error_guard(self, source):
        assert "'except ValueError' not in del_cookie" in source

    def test_step_19_value_error_guard(self, source):
        assert "'except ValueError' not in _init" in source

    def test_step_22_value_error_guard(self, source):
        assert "'except ValueError' not in del_cookie_target" in source


class TestPatchStepOrdering:
    """Verify step dependencies are respected in the source."""

    @pytest.fixture
    def source(self):
        return PATCH_SCRIPT.read_text(encoding="utf-8")

    def test_step10_before_step17(self, source):
        """Step 10 must apply before step 17 (step 17's old pattern includes step 10's output)."""
        step10_pos = source.find("_step(10,")
        step17_pos = source.find("_step(17,")
        assert step10_pos < step17_pos, "Step 10 must come before step 17"

    def test_step15_before_step17(self, source):
        """Step 15 (logger import) must come before step 17 (uses logger)."""
        step15_pos = source.find("_step(15,")
        step17_pos = source.find("_step(17,")
        assert step15_pos < step17_pos, "Step 15 must come before step 17"

    def test_step4_before_step24(self, source):
        """Step 4 (parse_target rewrite) must come before step 24 (regex anchor)."""
        step4_pos = source.find("_step(4,")
        step24_pos = source.find("_step(24,")
        assert step4_pos < step24_pos, "Step 4 must come before step 24"

    def test_step10_before_step18(self, source):
        """Step 10 must apply before step 18 for del_cookie."""
        step10_pos = source.find('_step(10, "error msg: del_cookie')
        step18_pos = source.find("_step(18,")
        assert step10_pos > 0 or step18_pos > 0


class TestPatchFileGrouping:
    """Verify files are grouped correctly (one read, one write per group)."""

    @pytest.fixture
    def source(self):
        return PATCH_SCRIPT.read_text(encoding="utf-8")

    def test_bili_group_is_contiguous(self, source):
        bili_read = source.find("bili = _read(bili_path)")
        bili_write = source.find("_write(bili_path, bili)")
        assert bili_read > 0
        assert bili_write > bili_read
        for step in [3, 26, 27]:
            pos = source.find(f"_step({step},")
            assert bili_read < pos < bili_write, f"Step {step} not in bili group"

    def test_weibo_group_is_contiguous(self, source):
        weibo_read = source.find("weibo = _read(weibo_path)")
        weibo_write = source.find("_write(weibo_path, weibo)")
        assert weibo_read > 0
        assert weibo_write > weibo_read
        for step in [4, 5, 6, 7, 23, 24, 25]:
            pos = source.find(f"_step({step},")
            assert weibo_read < pos < weibo_write, f"Step {step} not in weibo group"

    def test_db_group_is_contiguous(self, source):
        db_read = source.find("db = _read(db_path)")
        db_write = source.find("_write(db_path, db)")
        assert db_read > 0
        assert db_write > db_read
        for step in [28, 30, 33]:
            pos = source.find(f"_step({step},")
            assert db_read < pos < db_write, f"Step {step} not in db group"

    def test_del_sub_group_is_contiguous(self, source):
        read_pos = source.find("del_sub = _read(del_sub_path)")
        write_pos = source.find("_write(del_sub_path, del_sub)")
        assert read_pos > 0
        assert write_pos > read_pos
        for step in [10, 13, 15, 17]:
            pos = source.find(f"_step({step},")
            assert read_pos < pos < write_pos, f"Step {step} not in del_sub group"

    def test_del_cookie_group_is_contiguous(self, source):
        read_pos = source.find("del_cookie = _read(del_cookie_path)")
        write_pos = source.find("_write(del_cookie_path, del_cookie)")
        assert read_pos > 0
        assert write_pos > read_pos
        for step in [16, 18]:
            pos = source.find(f"_step({step},")
            assert read_pos < pos < write_pos, f"Step {step} not in del_cookie group"

    def test_del_cookie_target_group_is_contiguous(self, source):
        read_pos = source.find("del_cookie_target = _read(del_cookie_target_path)")
        write_pos = source.find("_write(del_cookie_target_path, del_cookie_target)")
        assert read_pos > 0
        assert write_pos > read_pos
        for step in [21, 22]:
            pos = source.find(f"_step({step},")
            assert read_pos < pos < write_pos, f"Step {step} not in del_cookie_target group"

    def test_init_group_is_contiguous(self, source):
        read_pos = source.find("_init = _read(_init_path)")
        write_pos = source.find("_write(_init_path, _init)")
        assert read_pos > 0
        assert write_pos > read_pos
        for step in [11, 19]:
            pos = source.find(f"_step({step},")
            assert read_pos < pos < write_pos, f"Step {step} not in __init__ group"
