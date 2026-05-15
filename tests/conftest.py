"""Shared fixtures for Subscriber tests."""

import os
import sys
from pathlib import Path

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Auto-detect bison package path
_VENV_SITE = PROJECT_ROOT / ".venv" / "Lib" / "site-packages" / "nonebot_bison"
if _VENV_SITE.is_dir():
    BISON_BASE = str(_VENV_SITE)
else:
    BISON_BASE = None


@pytest.fixture
def bison_base():
    """Return the nonebot_bison package path, skip if not found."""
    if BISON_BASE is None:
        pytest.skip("nonebot_bison not installed")
    return BISON_BASE


@pytest.fixture
def read_file():
    """Helper to read a file and return its content."""
    def _read(path: str) -> str:
        with open(path) as f:
            return f.read()
    return _read
