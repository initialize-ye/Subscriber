"""Comprehensive bison patch: disable unwanted platforms + fix weibo + improve errors."""

import os
import re
import sys
from pathlib import Path

# Auto-detect bison package path: prefer .venv in project root, fallback to sys.prefix
_project_root = Path(__file__).resolve().parent
_venv_site = _project_root / ".venv" / "Lib" / "site-packages" / "nonebot_bison"
if _venv_site.is_dir():
    BASE = str(_venv_site)
else:
    # Fallback for production Ubuntu server
    BASE = "/home/ubuntu/Subscriber/.venv/lib/python3.12/site-packages/nonebot_bison"
    if not os.path.isdir(BASE):
        # Last resort: resolve from import
        import importlib.util as _util
        _spec = _util.find_spec("nonebot_bison")
        if _spec and _spec.origin:
            BASE = str(Path(_spec.origin).parent)
        else:
            print("ERROR: cannot find nonebot_bison package")
            sys.exit(1)

TOTAL_STEPS = 8


def _read(path: str) -> str:
    with open(path) as f:
        return f.read()


def _write(path: str, content: str) -> None:
    with open(path, "w") as f:
        f.write(content)


def _assert_patched(content: str, old: str, name: str) -> None:
    """Verify old pattern is GONE from patched content."""
    if old in content:
        print(f"WARN: {name} — pattern still present, patch may have failed")


def _assert_not_patched(content: str, new: str, name: str) -> None:
    """Verify new pattern IS in patched content."""
    if new not in content:
        print(f"WARN: {name} — new pattern not found, patch may have failed")
    print(f"[{n}/{TOTAL_STEPS}] {msg}")


# ====== 1. Patch metrics.py ======
metrics_content = """\
import time
try:
    from nonebot import require
    require("nonebot_plugin_prometheus")
    from nonebot_plugin_prometheus import Counter, Gauge, Histogram
except (ImportError, RuntimeError, ModuleNotFoundError):
    from contextlib import contextmanager
    class _DummyMetric:
        def __init__(self, *args, **kwargs): pass
        def inc(self, *args, **kwargs): pass
        def set(self, *args, **kwargs): pass
        def observe(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self
        @contextmanager
        def time(self):
            yield
    Counter = _DummyMetric; Gauge = _DummyMetric; Histogram = _DummyMetric

request_counter = Counter("bison_request_counter", "The number of requests", ["site_name", "platform_name", "target", "success"])
sent_counter = Counter("bison_sent_counter", "The number of sent messages", ["site_name", "platform_name", "target"])
cookie_choose_counter = Counter("bison_cookie_choose_counter", "The number of cookie choose", ["site_name", "target", "cookie_id"])
request_time_histogram = Histogram("bison_request_histogram", "The time of platform used to request the source", ["site_name", "platform_name"], buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60])
render_time_histogram = Histogram("bison_render_histogram", "The time of theme used to render", ["site_name", "platform_name"], buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60])
start_time = Gauge("bison_start_time", "The start time of the program")
start_time.set(time.time())
"""
_write(os.path.join(BASE, "metrics.py"), metrics_content)
_step(1, "metrics.py patched")


# ====== 2. Disable unwanted platforms ======
for fp in [
    "platform/arknights.py",
    "platform/ff14.py",
    "platform/ncm.py",
    "platform/rss.py",
    "platform/ceobecanteen/platform.py",
]:
    path = os.path.join(BASE, fp)
    if not os.path.isfile(path):
        _step(2, f"SKIP (not found): {fp}")
        continue
    content = _read(path)
    content = re.sub(r"\benabled\s*=\s*True", "enabled = False", content)
    content = re.sub(r"\bis_common\s*=\s*True", "is_common = False", content)
    content = re.sub(r"enabled:\s*bool\s*=\s*True", "enabled: bool = False", content)
    _write(path, content)
_step(2, "Disabled: arknights, ff14, ncm, rss, ceobecanteen")


# ====== 3. Disable bilibili-live and bilibili-bangumi (keep bilibili main) ======
bili_path = os.path.join(BASE, "platform/bilibili/platforms.py")
bili_content = _read(bili_path)
for name in ["bilibili-live", "bilibili-bangumi"]:
    idx = bili_content.find(f'platform_name = "{name}"')
    if idx == -1:
        continue
    segment = bili_content[idx : idx + 200]
    new_segment = segment.replace("enabled = True", "enabled = False")
    new_segment = new_segment.replace("is_common = True", "is_common = False")
    bili_content = bili_content.replace(segment, new_segment)
_write(bili_path, bili_content)
_step(3, "bilibili-live and bilibili-bangumi disabled")


# ====== 4-7. Weibo patches (single read/write) ======
weibo_path = os.path.join(BASE, "platform/weibo.py")
weibo = _read(weibo_path)

# 4. Fix parse_target — support weibo.com/UID in addition to weibo.com/u/UID
old_parse = (
    "    @classmethod\n"
    "    async def parse_target(cls, target_text: str) -> Target:\n"
)
parse_end = weibo.find("\n    async def get_sub_list", weibo.find(old_parse))
new_parse = (
    "    @classmethod\n"
    "    async def parse_target(cls, target_text: str) -> Target:\n"
    '        if re.match(r"\\d+", target_text):\n'
    "            return Target(target_text)\n"
    '        elif match := re.match(r"(?:https?://)?weibo\\.com/u/(\\d+)", target_text):\n'
    "            return Target(match.group(1))\n"
    '        elif match := re.match(r"(?:https?://)?weibo\\.com/(\\d+)", target_text):\n'
    "            return Target(match.group(1))\n"
    "        else:\n"
    '            raise cls.ParseTargetException(prompt="正确格式:\\n1. 用户数字UID (如 7618923072)\\n2. https://weibo.com/7618923072\\n3. https://weibo.com/u/7618923072")\n'
)
if old_parse in weibo and parse_end > 0:
    weibo = weibo[: weibo.index(old_parse)] + new_parse + weibo[parse_end:]
    _assert_not_patched(weibo, 'raise cls.ParseTargetException(prompt="正确格式:\\n1. 用户数字UID (如 7618923072)', "step 4")
    _step(4, "weibo parse_target fixed")
else:
    _step(4, "weibo parse_target SKIP (pattern not found)")

# 5. Fix get_cookie_name — support HTTP cookie format (not just JSON)
weibo = weibo.replace(
    "name = await self._get_current_user_name(json.loads(content))",
    'name = await self._get_current_user_name(json.loads(content) if content.strip().startswith("{") else '
    "dict((k.strip(), v.strip()) for k, v in (item.strip().split('=', 1) for item in content.split(';') if '=' in item)))",
)
_assert_not_patched(weibo, 'dict((k.strip(), v.strip())', "step 5")
_step(5, "weibo cookie format fix applied")

# 6. Add proxy to _get_current_user_name
weibo = weibo.replace(
    'async with http_client() as client:\n            r = await client.get(url, headers=_HEADER, cookies=cookies)',
    'async with http_client(proxy="http://127.0.0.1:7890") as client:\n            r = await client.get(url, headers=_HEADER, cookies=cookies)',
)
_step(6, "weibo _get_current_user_name proxy applied")
_assert_not_patched(weibo, 'http_client(proxy="http://127.0.0.1:7890")', "step 6")

# 7. Add proxy to get_query_name_client (fix: replace entire block, not just append)
old_block = """    @override
    async def get_client(self, target: Target | None) -> AsyncClient:
        client = await super().get_client(target)

        if len(client.cookies) == 0:
            client.cookies.update({"dummycookie": "1"})

        return client

    @classmethod
    async def get_query_name_client(cls) -> AsyncClient:
        client = http_client()

        if len(client.cookies) == 0:
            client.cookies.update({"dummycookie": "1"})

        return client"""

new_block = """    @override
    async def get_client(self, target: Target | None) -> AsyncClient:
        client = await super().get_client(target)

        if len(client.cookies) == 0:
            client.cookies.update({"dummycookie": "1"})

        return client

    @classmethod
    async def get_query_name_client(cls) -> AsyncClient:
        client = http_client(proxy="http://127.0.0.1:7890")

        if len(client.cookies) == 0:
            client.cookies.update({"dummycookie": "1"})

        return client"""

if old_block in weibo:
    weibo = weibo.replace(old_block, new_block)
    _assert_not_patched(weibo, 'http_client(proxy="http://127.0.0.1:7890")\n\n        if len(client.cookies) == 0', "step 7")
    _step(7, "weibo proxy configured")
else:
    _step(7, "weibo proxy SKIP (pattern not found)")

_write(weibo_path, weibo)


# ====== 8. Better feedback for add_cookie ======
add_cookie_path = os.path.join(BASE, "sub_manager/add_cookie.py")
add_cookie = _read(add_cookie_path)

# 8a. Improve validation failure message
add_cookie = add_cookie.replace(
    'if not await client_mgr.validate_cookie(cookie_text):\n            await add_cookie.reject(\n                "无效的 Cookie，请检查后重新输入，详情见https://nonebot-bison.netlify.app/usage/cookie.html"\n            )',
    'if not await client_mgr.validate_cookie(cookie_text):\n            await add_cookie.reject(\n                "Cookie 格式无效，确保是从浏览器完整复制的 Cookie 字符串。\\n详情请查看：https://nonebot-bison.netlify.app/usage/cookie.html"\n            )',
)

# 8b. Add loading indicator + catch all errors (including network) during cookie validation
old_err = '            cookie_name = await client_mgr.get_cookie_name(cookie_text)\n            state["cookie"] = cookie_text\n            state["cookie_name"] = cookie_name\n        except JSONDecodeError as e:\n            logger.error("获取 Cookie 名称失败:" + str(e))\n            await add_cookie.reject(\n                "获取 Cookie 名称失败，请检查后重新输入，详情见https://nonebot-bison.netlify.app/usage/cookie.html"\n            )'
new_err = (
    '            await add_cookie.send("正在验证 Cookie...")\n'
    "            cookie_name = await client_mgr.get_cookie_name(cookie_text)\n"
    '            state["cookie"] = cookie_text\n'
    '            state["cookie_name"] = cookie_name\n'
    "        except (JSONDecodeError, KeyError) as e:\n"
    '            logger.error("获取 Cookie 名称失败: " + str(e))\n'
    '            await add_cookie.reject(f"Cookie 解析失败：{e}")\n'
    "        except httpx.HTTPStatusError as e:\n"
    '            logger.error(f"获取 Cookie 名称失败: HTTP {e.response.status_code}")\n'
    "            status = e.response.status_code\n"
    "            if status == 432:\n"
    '                msg = "微博 API 拒绝了验证请求，可能原因：\\n1. Cookie 已过期，请重新获取\\n2. 服务器 IP 被微博限制"\n'
    "            else:\n"
    '                msg = f"微博 API 返回错误 (HTTP {status})"\n'
    "            await add_cookie.reject(msg)\n"
    "        except (httpx.ConnectError, httpx.TimeoutException) as e:\n"
    '            logger.error(f"网络请求失败: {e}")\n'
    '            await add_cookie.reject(f"网络请求失败，请检查网络连接后重试：{type(e).__name__}")'
)
add_cookie = add_cookie.replace(old_err, new_err)

# 8c. Add error handling for cookie save (add_identified_cookie)
old_save = '        new_cookie = await client_mgr.add_identified_cookie(state["cookie"], state["cookie_name"])\n        await add_cookie.finish(\n            f"已添加 Cookie: {new_cookie.cookie_name} 到平台 {state[\'platform\']}"\n            + "\\n请使用“关联cookie”为 Cookie 关联订阅"\n        )'
new_save = (
    "        try:\n"
    '            new_cookie = await client_mgr.add_identified_cookie(state["cookie"], state["cookie_name"])\n'
    "        except Exception as e:\n"
    '            logger.error(f"保存 Cookie 失败: {e}")\n'
    '            await add_cookie.finish(f"Cookie 验证通过，但保存失败：{e}")\n'
    "            return\n"
    "        await add_cookie.finish(\n"
    '            f"已添加 Cookie: {new_cookie.cookie_name} 到平台 {state[\'platform\']}"\n'
    '            + "\\n请使用“关联cookie”为 Cookie 关联订阅"\n'
    "        )"
)
add_cookie = add_cookie.replace(old_save, new_save)

if "import httpx" not in add_cookie:
    add_cookie = add_cookie.replace(
        "from nonebot.log import logger",
        "import httpx\nfrom nonebot.log import logger",
    )

_write(add_cookie_path, add_cookie)
_step(8, "add_cookie feedback improved")

print("\nAll patches applied!")
