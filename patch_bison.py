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

TOTAL_STEPS = 38


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


def _step(n: int, msg: str) -> None:
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


# ====== bilibili/platforms.py (steps 3, 26, 27 — single read/write) ======
bili_path = os.path.join(BASE, "platform/bilibili/platforms.py")
bili = _read(bili_path)

# Step 3: Disable bilibili-live and bilibili-bangumi
for name in ["bilibili-live", "bilibili-bangumi"]:
    idx = bili.find(f'platform_name = "{name}"')
    if idx == -1:
        continue
    next_class = bili.find("\nclass ", idx + 1)
    if next_class == -1:
        next_class = len(bili)
    segment = bili[idx:next_class]
    new_segment = segment.replace("enabled = True", "enabled = False")
    new_segment = new_segment.replace("is_common = True", "is_common = False")
    bili = bili.replace(segment, new_segment)
_step(3, "bilibili-live and bilibili-bangumi disabled")

# Step 26: Fix bilibili parse_target regex (anchor end)
bili = bili.replace(
    'if re.match(r"\\d+", target_text):',
    'if re.match(r"^\\d+$", target_text):',
)
bili = bili.replace(
    'if re.match(r"\\d+", target_string):',
    'if re.match(r"^\\d+$", target_string):',
)
_step(26, "bilibili parse_target regex anchored")

# Step 27: Fix bilibili bangumi fallback (list vs dict)
old_bangumi = '            lastest_episode = detail_dict["result"]["episodes"]\n'
new_bangumi = '            lastest_episode = detail_dict["result"]["episodes"][0]\n'
if old_bangumi in bili:
    bili = bili.replace(old_bangumi, new_bangumi)
_step(27, "bilibili bangumi fallback fixed")

_write(bili_path, bili)


# ====== weibo.py (steps 4-7, 23-25 — single read/write) ======
weibo_path = os.path.join(BASE, "platform/weibo.py")
weibo = _read(weibo_path)

# Step 4: Fix parse_target — support weibo.com/UID in addition to weibo.com/u/UID
old_parse = (
    "    @classmethod\n"
    "    async def parse_target(cls, target_text: str) -> Target:\n"
)
parse_end = weibo.find("\n    async def get_sub_list", weibo.find(old_parse))
new_parse = (
    "    @classmethod\n"
    "    async def parse_target(cls, target_text: str) -> Target:\n"
    '        if re.match(r"^\\d+$", target_text):\n'
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

# Step 5: Fix get_cookie_name — support HTTP cookie format (not just JSON)
weibo = weibo.replace(
    "name = await self._get_current_user_name(json.loads(content))",
    'name = await self._get_current_user_name(json.loads(content) if content.strip().startswith("{") else '
    "dict((k.strip(), v.strip()) for k, v in (item.strip().split('=', 1) for item in content.split(';') if '=' in item)))",
)
_assert_not_patched(weibo, 'dict((k.strip(), v.strip())', "step 5")
_step(5, "weibo cookie format fix applied")

# Step 6: Add proxy to _get_current_user_name
weibo = weibo.replace(
    'async with http_client() as client:\n            r = await client.get(url, headers=_HEADER, cookies=cookies)',
    'async with http_client(proxy="http://127.0.0.1:7890") as client:\n            r = await client.get(url, headers=_HEADER, cookies=cookies)',
)
_step(6, "weibo _get_current_user_name proxy applied")
_assert_not_patched(weibo, 'http_client(proxy="http://127.0.0.1:7890")', "step 6")

# Step 7: Add proxy to get_query_name_client
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

# Step 23: Fix weibo longTextContent KeyError crash
old_long_text = '            info["text"] = (await self._get_long_weibo(info["mid"]))["longTextContent"]'
new_long_text = (
    "            long_data = await self._get_long_weibo(info[\"mid\"])\n"
    '            if "longTextContent" in long_data:\n'
    '                info["text"] = long_data["longTextContent"]'
)
if old_long_text in weibo:
    weibo = weibo.replace(old_long_text, new_long_text)
_step(23, "weibo longTextContent KeyError fix applied")

# Step 24: Fix weibo parse_target regex (anchor end)
weibo = weibo.replace(
    'if re.match(r"\\d+", target_text):',
    'if re.match(r"^\\d+$", target_text):',
)
_step(24, "weibo parse_target regex anchored")

# Step 25: Fix weibo br.tail dead code
if 'selector.xpath("br")' in weibo:
    weibo = weibo.replace(
        'for br in selector.xpath("br"):\n            br.tail = "\\n" + br.tail',
        'for br in selector.xpath("//br"):\n            if br.tail:\n                br.tail = "\\n" + br.tail',
    )
_step(25, "weibo br.tail xpath fixed")

_write(weibo_path, weibo)


# ====== add_cookie.py (steps 8, 12 — single read/write) ======
add_cookie_path = os.path.join(BASE, "sub_manager/add_cookie.py")
add_cookie = _read(add_cookie_path)

# Step 8a: Improve validation failure message
add_cookie = add_cookie.replace(
    'if not await client_mgr.validate_cookie(cookie_text):\n            await add_cookie.reject(\n                "无效的 Cookie，请检查后重新输入，详情见https://nonebot-bison.netlify.app/usage/cookie.html"\n            )',
    'if not await client_mgr.validate_cookie(cookie_text):\n            await add_cookie.reject(\n                "Cookie 格式无效，确保是从浏览器完整复制的 Cookie 字符串。\\n详情请查看：https://nonebot-bison.netlify.app/usage/cookie.html"\n            )',
)

# Step 8b: Add loading indicator + catch all errors during cookie validation
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

# Step 8c: Add error handling for cookie save
old_save = '        new_cookie = await client_mgr.add_identified_cookie(state["cookie"], state["cookie_name"])\n        await add_cookie.finish(\n            f"已添加 Cookie: {new_cookie.cookie_name} 到平台 {state[\'platform\']}"\n            + "\\n请使用"关联cookie"为 Cookie 关联订阅"\n        )'
new_save = (
    "        try:\n"
    '            new_cookie = await client_mgr.add_identified_cookie(state["cookie"], state["cookie_name"])\n'
    "        except Exception as e:\n"
    '            logger.error(f"保存 Cookie 失败: {e}")\n'
    '            await add_cookie.finish(f"Cookie 验证通过，但保存失败：{e}")\n'
    "            return\n"
    "        await add_cookie.finish(\n"
    '            f"已添加 Cookie: {new_cookie.cookie_name} 到平台 {state[\'platform\']}"\n'
    '            + "\\n请使用"关联cookie"为 Cookie 关联订阅"\n'
    "        )"
)
add_cookie = add_cookie.replace(old_save, new_save)

if "import httpx" not in add_cookie:
    add_cookie = add_cookie.replace(
        "from nonebot.log import logger",
        "import httpx\nfrom nonebot.log import logger",
    )
_step(8, "add_cookie feedback improved")

# Step 12: Cookie privacy warning
add_cookie = add_cookie.replace(
    'state["_prompt"] = "请输入 Cookie"',
    'state["_prompt"] = "请输入 Cookie\\n⚠ Cookie 将以明文显示在聊天中，建议确认后删除相关消息"',
)
_assert_not_patched(add_cookie, "Cookie 将以明文显示", "step 12")
_step(12, "add_cookie privacy warning added")

_write(add_cookie_path, add_cookie)


# ====== del_sub.py (steps 9, 10, 13, 15, 17 — single read/write) ======
del_sub_path = os.path.join(BASE, "sub_manager/del_sub.py")
del_sub = _read(del_sub_path)

# Step 9: Unify cancel message
if '"删除中止"' in del_sub:
    del_sub = del_sub.replace('"删除中止"', '"已取消删除"')
    _step(9, "cancel msg: del_sub.py")
else:
    _step(9, "SKIP (pattern not found): del_sub.py")

# Step 10: Improve vague error message
_old = 'except Exception:\n            await del_sub.reject("删除错误")'
_new = 'except Exception as e:\n            logger.exception(f"删除失败: {e}")\n            await del_sub.reject("删除失败，请查看日志或联系管理员")'
if _old in del_sub:
    del_sub = del_sub.replace(_old, _new)
    if "logger" not in del_sub and 'from nonebot.log import logger' not in del_sub:
        del_sub = del_sub.replace(
            "from nonebot.matcher import Matcher",
            "from nonebot.log import logger\nfrom nonebot.matcher import Matcher",
        )
    _step(10, "error msg: del_sub.py")
else:
    _step(10, "SKIP: del_sub.py")

# Step 13: Subscription count
if '共 {len(sub_list)} 个订阅' not in del_sub:
    del_sub = del_sub.replace(
        '        res += "请输入要删除的订阅的序号\\n输入\'取消\'中止"',
        '        res += f"\\n共 {len(sub_list)} 个订阅\\n"\n        res += "请输入要删除的订阅的序号\\n输入\'取消\'中止"',
    )
_step(13, "subscription count added to del_sub")

# Step 15: Fix missing logger import
if "from nonebot.log import logger" not in del_sub:
    del_sub = del_sub.replace(
        "from .utils import ensure_user_info, gen_handle_cancel",
        "from nonebot.log import logger\nfrom .utils import ensure_user_info, gen_handle_cancel",
    )
_step(15, "del_sub.py logger import added")

# Step 17: Add ValueError/KeyError handling
if 'except ValueError' not in del_sub:
    old_del_sub_err = (
        "        except Exception as e:\n"
        '            logger.exception(f"删除失败: {e}")\n'
        '            await del_sub.reject("删除失败，请查看日志或联系管理员")'
    )
    new_del_sub_err = (
        '        except ValueError:\n'
        '            await del_sub.reject("请输入正确的数字序号")\n'
        '        except KeyError:\n'
        '            await del_sub.reject("序号错误，请输入列表中的序号")\n'
        "        except Exception as e:\n"
        '            logger.exception(f"删除失败: {e}")\n'
        '            await del_sub.reject("删除失败，请查看日志或联系管理员")'
    )
    del_sub = del_sub.replace(old_del_sub_err, new_del_sub_err)
_step(17, "del_sub.py input validation added")

_write(del_sub_path, del_sub)


# ====== del_cookie.py (steps 9, 10, 16, 18 — single read/write) ======
del_cookie_path = os.path.join(BASE, "sub_manager/del_cookie.py")
del_cookie = _read(del_cookie_path)

# Step 9: Unify cancel message
if '"删除中止"' in del_cookie:
    del_cookie = del_cookie.replace('"删除中止"', '"已取消删除"')
    _step(9, "cancel msg: del_cookie.py")
else:
    _step(9, "SKIP (pattern not found): del_cookie.py")

# Step 10: Improve vague error message
_old = 'except Exception:\n            await del_cookie.reject("删除错误")'
_new = 'except Exception as e:\n            logger.exception(f"删除失败: {e}")\n            await del_cookie.reject("删除失败，请查看日志或联系管理员")'
if _old in del_cookie:
    del_cookie = del_cookie.replace(_old, _new)
    if "logger" not in del_cookie and 'from nonebot.log import logger' not in del_cookie:
        del_cookie = del_cookie.replace(
            "from nonebot.matcher import Matcher",
            "from nonebot.log import logger\nfrom nonebot.matcher import Matcher",
        )
    _step(10, "error msg: del_cookie.py")
else:
    _step(10, "SKIP: del_cookie.py")

# Step 16: Fix missing logger import
if "from nonebot.log import logger" not in del_cookie:
    del_cookie = del_cookie.replace(
        "from .utils import gen_handle_cancel, only_allow_private",
        "from nonebot.log import logger\nfrom .utils import gen_handle_cancel, only_allow_private",
    )
_step(16, "del_cookie.py logger import added")

# Step 18: Add ValueError handling
if 'except ValueError' not in del_cookie:
    old_del_cookie_err = (
        "        except KeyError:\n"
        '            await del_cookie.reject("序号错误")'
    )
    new_del_cookie_err = (
        '        except ValueError:\n'
        '            await del_cookie.reject("请输入正确的数字序号")\n'
        "        except KeyError:\n"
        '            await del_cookie.reject("序号错误")'
    )
    del_cookie = del_cookie.replace(old_del_cookie_err, new_del_cookie_err)
_step(18, "del_cookie.py input validation added")

_write(del_cookie_path, del_cookie)


# ====== del_cookie_target.py (steps 9, 10, 21, 22 — single read/write) ======
del_cookie_target_path = os.path.join(BASE, "sub_manager/del_cookie_target.py")
del_cookie_target = _read(del_cookie_target_path)

# Step 9: Unify cancel message
if '"取消关联中止"' in del_cookie_target:
    del_cookie_target = del_cookie_target.replace('"取消关联中止"', '"已取消关联"')
    _step(9, "cancel msg: del_cookie_target.py")
else:
    _step(9, "SKIP (pattern not found): del_cookie_target.py")

# Step 10: Improve vague error message
_old = 'except Exception:\n            await del_cookie_target.reject("删除错误")'
_new = 'except Exception as e:\n            logger.exception(f"删除失败: {e}")\n            await del_cookie_target.reject("删除失败，请查看日志或联系管理员")'
if _old in del_cookie_target:
    del_cookie_target = del_cookie_target.replace(_old, _new)
    if "logger" not in del_cookie_target and 'from nonebot.log import logger' not in del_cookie_target:
        del_cookie_target = del_cookie_target.replace(
            "from nonebot.matcher import Matcher",
            "from nonebot.log import logger\nfrom nonebot.matcher import Matcher",
        )
    _step(10, "error msg: del_cookie_target.py")
else:
    _step(10, "SKIP: del_cookie_target.py")

# Step 21: Fix missing logger import
if "from nonebot.log import logger" not in del_cookie_target:
    del_cookie_target = del_cookie_target.replace(
        "from .utils import gen_handle_cancel, only_allow_private",
        "from nonebot.log import logger\nfrom .utils import gen_handle_cancel, only_allow_private",
    )
_step(21, "del_cookie_target.py logger import added")

# Step 22: Add ValueError/KeyError handling
if 'except ValueError' not in del_cookie_target:
    old_dct_err = (
        "        except Exception as e:\n"
        '            logger.exception(f"删除失败: {e}")\n'
        '            await del_cookie_target.reject("删除失败，请查看日志或联系管理员")'
    )
    new_dct_err = (
        '        except ValueError:\n'
        '            await del_cookie_target.reject("请输入正确的数字序号")\n'
        '        except KeyError:\n'
        '            await del_cookie_target.reject("序号错误")\n'
        "        except Exception as e:\n"
        '            logger.exception(f"删除失败: {e}")\n'
        '            await del_cookie_target.reject("删除失败，请查看日志或联系管理员")'
    )
    del_cookie_target = del_cookie_target.replace(old_dct_err, new_dct_err)
_step(22, "del_cookie_target.py input validation added")

_write(del_cookie_target_path, del_cookie_target)


# ====== add_sub.py (step 9 — single read/write) ======
add_sub_path = os.path.join(BASE, "sub_manager/add_sub.py")
add_sub = _read(add_sub_path)

# Step 9: Unify cancel message
if '"已中止订阅"' in add_sub:
    add_sub = add_sub.replace('"已中止订阅"', '"已取消订阅"')
    _step(9, "cancel msg: add_sub.py")
else:
    _step(9, "SKIP (pattern not found): add_sub.py")

# Step 14: Better "id输入错误" message
add_sub = add_sub.replace(
    'await add_sub.reject("id输入错误")',
    'await add_sub.reject("无法通过该ID获取用户名，请确认ID是否正确（仅支持数字UID或完整链接）")',
)
_assert_not_patched(add_sub, "无法通过该ID获取用户名", "step 14")
_step(14, "add_sub id输入错误 message improved")

_write(add_sub_path, add_sub)


# ====== sub_manager/__init__.py (steps 9, 11, 19 — single read/write) ======
_init_path = os.path.join(BASE, "sub_manager/__init__.py")
_init = _read(_init_path)

# Step 9: Unify cancel message
if '"已中止添加cookie"' in _init:
    _init = _init.replace('"已中止添加cookie"', '"已取消添加 Cookie"')
    _step(9, "cancel msg: add_cookie (via __init__)")
elif '"已取消"' in _init:
    _init = _init.replace('"已取消"', '"已取消操作"')
    _step(9, "cancel msg: __init__.py")
else:
    _step(9, "SKIP (pattern not found): __init__.py")

# Step 11: Fix expire_time
if 'expire_time=datetime.now(),' in _init:
    _init = _init.replace(
        'expire_time=datetime.now(),',
        'expire_time=datetime.now() + timedelta(minutes=5),',
    )
    if 'timedelta' not in _init:
        _init = _init.replace(
            "from datetime import datetime",
            "from datetime import datetime, timedelta",
        )
    _step(11, "group_manage expire_time fixed")
else:
    _step(11, "SKIP: expire_time already patched or pattern not found")

# Step 19: Add ValueError handling
if 'except ValueError' not in _init:
    old_group_idx = "    idx = int(group_idx)\n    if idx not in group_number_idx.keys():"
    new_group_idx = (
        "    try:\n"
        "        idx = int(group_idx)\n"
        "    except ValueError:\n"
        '        await group_manage_matcher.reject("请输入正确的数字序号")\n'
        "        return\n"
        "    if idx not in group_number_idx.keys():"
    )
    _init = _init.replace(old_group_idx, new_group_idx)
_step(19, "group_manage input validation added")

_write(_init_path, _init)


# ====== query_sub.py (step 13 — single read/write) ======
query_sub_path = os.path.join(BASE, "sub_manager/query_sub.py")
query_sub = _read(query_sub_path)

if '共 {len(sub_list)} 个订阅' not in query_sub:
    query_sub = query_sub.replace(
        "        await MessageFactory(await parse_text(res)).send()\n        await query_sub.finish()",
        '        res += f"\\n共 {len(sub_list)} 个订阅"\n        await MessageFactory(await parse_text(res)).send()\n        await query_sub.finish()',
    )
_step(13, "subscription count added to query_sub")

_write(query_sub_path, query_sub)


# ====== sub_manager/utils.py (step 20 — single read/write) ======
utils_path = os.path.join(BASE, "sub_manager/utils.py")
utils = _read(utils_path)

utils = utils.replace(
    "No target_user_info set, this shouldn't happen, please issue",
    "未设置目标用户信息，这不应该发生，请反馈此问题",
)
_assert_not_patched(utils, "未设置目标用户信息", "step 20")
_step(20, "utils.py English error message fixed")

_write(utils_path, utils)


# ====== db_config.py (steps 28, 30, 33 — single read/write) ======
db_path = os.path.join(BASE, "config/db_config.py")
db = _read(db_path)

# Step 28: null checks
if "if not user_obj or not target_obj:" not in db:
    db = db.replace(
        "            await session.execute(delete(Subscribe).where(Subscribe.user == user_obj, Subscribe.target == target_obj))\n",
        "            if not user_obj or not target_obj:\n                return\n            await session.execute(delete(Subscribe).where(Subscribe.user == user_obj, Subscribe.target == target_obj))\n",
    )
if "if not subscribe_obj:" not in db:
    db = db.replace(
        "            subscribe_obj.tags = tags  # type:ignore\n",
        "            if not subscribe_obj:\n                return\n            subscribe_obj.tags = tags  # type:ignore\n",
    )
_step(28, "db_config null checks added")

# Step 30: Fix get_all_weight_config defaultdict bug
db = db.replace(
    '            if platform_name not in res.keys():',
    '            if target.target not in res[platform_name]:',
)
_step(30, "weight config defaultdict bug fixed")

# Step 33: Fix get_cookie_target orphan handling
if "res = [x for x in res if x.target is not None]" not in db:
    db = db.replace(
        '            res = list((await sess.scalars(query)).all())\n            res.sort(',
        '            res = list((await sess.scalars(query)).all())\n            res = [x for x in res if x.target is not None]\n            res.sort(',
    )
_step(33, "get_cookie_target orphan handling fixed")

_write(db_path, db)


# ====== add_cookie_target.py (step 29) ======
add_ct_path = os.path.join(BASE, "sub_manager/add_cookie_target.py")
add_ct = _read(add_ct_path)

add_ct = add_ct.replace(
    '        except Exception:\n            await add_cookie_target_matcher.reject("序号错误")',
    '        except (ValueError, KeyError, IndexError):\n            await add_cookie_target_matcher.reject("请输入正确的数字序号")',
)
_step(29, "add_cookie_target error handling improved")

_write(add_ct_path, add_ct)


# ====== utils/site.py (step 31) ======
site_path = os.path.join(BASE, "utils/site.py")
site = _read(site_path)

if "available_cookies = (cookie for cookie in" in site:
    site = site.replace(
        "        available_cookies = (cookie for cookie in cookies if cookie.last_usage + cookie.cd < datetime.now())\n        cookie = min(available_cookies, key=lambda x: x.last_usage)\n        return cookie",
        "        available_cookies = [cookie for cookie in cookies if cookie.last_usage + cookie.cd < datetime.now()]\n"
        "        if not available_cookies:\n"
        "            available_cookies = cookies\n"
        "        if not available_cookies:\n"
        '            raise ValueError(f"平台 {self._site_name} 没有可用的 Cookie")\n'
        "        cookie = min(available_cookies, key=lambda x: x.last_usage)\n"
        "        return cookie",
    )
_step(31, "_choose_cookie empty list fix applied")

_write(site_path, site)


# ====== utils/context.py (step 32) ======
ctx_path = os.path.join(BASE, "utils/context.py")
ctx = _read(ctx_path)

ctx = ctx.replace(
    'content_type = r.headers["content-type"]',
    'content_type = r.headers.get("content-type", "")',
)
_step(32, "_should_print_content KeyError fix applied")

_write(ctx_path, ctx)


# ====== utils/__init__.py (step 34) ======
utils_init_path = os.path.join(BASE, "utils/__init__.py")
utils_init = _read(utils_init_path)

if 'query_dict: dict = {}' in utils_init:
    utils_init = utils_init.replace(
        'def html_to_text(html: str, query_dict: dict = {}) -> str:',
        'def html_to_text(html: str, query_dict: dict | None = None) -> str:\n    if query_dict is None:\n        query_dict = {}',
    )
_step(34, "html_to_text mutable default fixed")

_write(utils_init_path, utils_init)


# ====== bilibili/scheduler.py (step 35) ======
bili_sched_path = os.path.join(BASE, "platform/bilibili/scheduler.py")
bili_sched = _read(bili_sched_path)

if "(await config.get_cookie(self._site_name, is_anonymous=True))[0]" in bili_sched:
    bili_sched = bili_sched.replace(
        "return (await config.get_cookie(self._site_name, is_anonymous=True))[0]",
        "anon_cookies = await config.get_cookie(self._site_name, is_anonymous=True)\n"
        '        if not anon_cookies:\n'
        '            raise ValueError(f"平台 {self._site_name} 没有可用的匿名 Cookie")\n'
        "        return anon_cookies[0]",
    )
_step(35, "bilibili scheduler IndexError fix applied")

_write(bili_sched_path, bili_sched)


# ====== admin_page/jwt.py (step 36) ======
jwt_path = os.path.join(BASE, "admin_page/jwt.py")
jwt = _read(jwt_path)

if "datetime.datetime.utcnow()" in jwt:
    jwt = jwt.replace(
        "datetime.datetime.utcnow()",
        "datetime.datetime.now(datetime.timezone.utc)",
    )
_step(36, "jwt.py utcnow() deprecation fixed")

_write(jwt_path, jwt)


# ====== 37. Fix add_cookie HTTP 432 Weibo-specific error message ======
add_cookie_path2 = os.path.join(BASE, "sub_manager/add_cookie.py")
add_cookie2 = _read(add_cookie_path2)
if '微博 API 拒绝了验证请求' in add_cookie2:
    add_cookie2 = add_cookie2.replace(
        '                msg = "微博 API 拒绝了验证请求，可能原因：\\n1. Cookie 已过期，请重新获取\\n2. 服务器 IP 被微博限制"',
        '                msg = "API 拒绝了验证请求 (HTTP 432)，可能原因：\\n1. Cookie 已过期，请重新获取\\n2. 服务器 IP 被限制"',
    )
    _write(add_cookie_path2, add_cookie2)
_step(37, "add_cookie HTTP 432 message made generic")


# ====== 38. Fix db_config assert targetObj (stripped by -O flag) ======
db_path2 = os.path.join(BASE, "config/db_config.py")
db2 = _read(db_path2)
if "assert targetObj" in db2:
    db2 = db2.replace(
        "            assert targetObj\n            return WeightConfig(",
        "            if not targetObj:\n                raise ValueError(f\"目标不存在: {platform_name}/{target}\")\n            return WeightConfig(",
    )
    _write(db_path2, db2)
_step(38, "assert targetObj replaced with proper null check")


print("\nAll patches applied!")
