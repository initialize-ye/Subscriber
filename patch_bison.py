"""Comprehensive bison patch: disable unwanted platforms + fix weibo parse_target."""

import os
import re
import json

BASE = "/home/ubuntu/Subscriber/.venv/lib/python3.12/site-packages/nonebot_bison"

def parse_cookie_string(cookie_str: str) -> dict:
    """Parse cookie string like 'key=value; key2=value2' into dict."""
    result = {}
    for item in cookie_str.split(";"):
        item = item.strip()
        if "=" in item:
            key, value = item.split("=", 1)
            result[key.strip()] = value.strip()
    return result

# ====== 1. Patch metrics.py ======
metrics_path = os.path.join(BASE, "metrics.py")
with open(metrics_path, "w") as f:
    f.write("""import time
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
""")
print("1/4 metrics.py patched")

# ====== 2. Disable unwanted platforms ======
for fp in [
    "platform/arknights.py",
    "platform/ff14.py",
    "platform/ncm.py",
    "platform/rss.py",
    "platform/ceobecanteen/platform.py",
]:
    path = os.path.join(BASE, fp)
    with open(path, "r") as f:
        content = f.read()
    content = re.sub(r"\b(enabled)\s*=\s*True", r"\1 = False", content)
    content = re.sub(r"\b(is_common)\s*=\s*True", r"\1 = False", content)
    content = re.sub(r"enabled:\s*bool\s*=\s*True", "enabled: bool = False", content)
    with open(path, "w") as f:
        f.write(content)
    print(f"2/4 Disabled: {fp}")

# ====== 3. Disable bilibili-live and bilibili-bangumi (keep bilibili main) ======
bili_path = os.path.join(BASE, "platform/bilibili/platforms.py")
with open(bili_path, "r") as f:
    bili_content = f.read()

# Find bilibili-live and bilibili-bangumi classes and disable them
for platform_name in ["bilibili-live", "bilibili-bangumi"]:
    # Find the class with this platform_name and disable its enabled/is_common
    idx = bili_content.find(f'platform_name = "{platform_name}"')
    if idx == -1:
        continue
    # Search forward from this point to find enabled and is_common
    segment = bili_content[idx:idx+200]
    old_segment = segment
    segment = re.sub(r"\b(enabled)\s*=\s*True", r"\1 = False", segment)
    segment = re.sub(r"\b(is_common)\s*=\s*True", r"\1 = False", segment)
    bili_content = bili_content.replace(old_segment, segment)

with open(bili_path, "w") as f:
    f.write(bili_content)
print("3/4 bilibili-live and bilibili-bangumi disabled")

# ====== 4. Fix weibo parse_target ======
weibo_path = os.path.join(BASE, "platform/weibo.py")
with open(weibo_path, "r") as f:
    content = f.read()

# Represent literal \n in file as \\n in our strings
new_method = (
    "    @classmethod\n"
    "    async def parse_target(cls, target_text: str) -> Target:\n"
    "        if re.match(r\"\\d+\", target_text):\n"
    "            return Target(target_text)\n"
    "        elif match := re.match(r\"(?:https?://)?weibo\\.com/u/(\\d+)\", target_text):\n"
    "            return Target(match.group(1))\n"
    "        elif match := re.match(r\"(?:https?://)?weibo\\.com/(\\d+)\", target_text):\n"
    "            return Target(match.group(1))\n"
    "        else:\n"
    "            raise cls.ParseTargetException(prompt=\"正确格式:\\n1. 用户数字UID (如 7618923072)\\n2. https://weibo.com/7618923072\\n3. https://weibo.com/u/7618923072\")\n"
)

# Find the old parse_target method and replace it
method_start = content.find("    @classmethod\n    async def parse_target")
if method_start >= 0:
    method_end = content.find("\n    async def get_sub_list", method_start)
    if method_end >= 0:
        content = content[:method_start] + new_method + content[method_end:]
        with open(weibo_path, "w") as f:
            f.write(content)
        print("4/4 weibo.py patched")
    else:
        print("4/4 FAIL: could not find end of parse_target")
else:
    print("4/4 FAIL: could not find parse_target")

# ====== 5. Fix weibo cookie get_cookie_name (support HTTP cookie format, not just JSON) ======
weibo_path = os.path.join(BASE, "platform/weibo.py")
with open(weibo_path, "r") as f:
    content = f.read()

# Replace the problematic json.loads with parse_cookie_string
old_cookie_method = """    @override
    async def get_cookie_name(self, content: str) -> str:
        \"\"\"从cookie内容中获取cookie的友好名字，添加cookie时调用，持久化在数据库中\"\"\"
        name = await self._get_current_user_name(json.loads(content))

        return text_fletten(f"weibo: [{name[:10]}]")"""

new_cookie_method = """    @override
    async def get_cookie_name(self, content: str) -> str:
        \"\"\"从cookie内容中获取cookie的友好名字，添加cookie时调用，持久化在数据库中\"\"\"
        cookies = json.loads(content) if content.strip().startswith(\"{\") else parse_cookie_string(content)
        name = await self._get_current_user_name(cookies)

        return text_fletten(f"weibo: [{name[:10]}]")"""

if old_cookie_method in content:
    content = content.replace(old_cookie_method, new_cookie_method)
else:
    print("5/5 WARN: old cookie method pattern not found in weibo.py")

with open(weibo_path, "w") as f:
    f.write(content)

# Also add parse_cookie_string import to weibo.py
if "parse_cookie_string" not in content:
    # Add it right after json import if exists, otherwise at top of non-class section
    content_lines = content.split("\n")
    # Find the imports section
    for i, line in enumerate(content_lines):
        if "from nonebot_bison.utils.site import" in line:
            content_lines.insert(i, "from nonebot_bison.config import parse_cookie_string")
            break
    content = "\n".join(content_lines)

    # Actually, parse_cookie_string is local to patch script, not in bison.
    # We need to add it to weibo.py itself or use another approach.
    # Let's undo the import and just embed the function.
    content_lines = content.split("\n")
    for i, line in enumerate(content_lines):
        if "from nonebot_bison.config import parse_cookie_string" in line:
            content_lines.pop(i)
            break
    content = "\n".join(content_lines)

# Actually, let's embed the helper directly in weibo.py
weibo_func = """
def _parse_cookie_str(cookie_str: str) -> dict:
    \"\"\"Parse cookie string like 'key=value; key2=value2' into dict.\"\"\"
    result = {}
    items = cookie_str.split(\";\")
    for item in items:
        item = item.strip()
        if \"=\" in item:
            key, value = item.split(\"=\", 1)
            result[key.strip()] = value.strip()
    return result
"""

weibo_path = os.path.join(BASE, "platform/weibo.py")
with open(weibo_path, "r") as f:
    content = f.read()

# Add helper function and fix get_cookie_name
# First add the helper function after imports
content = content.replace(
    "from nonebot_bison.utils.site import",
    "_parse_cookie_str = lambda s: dict((k.strip(), v.strip()) for k, v in (item.strip().split('=', 1) for item in s.split(';') if '=' in item))\nfrom nonebot_bison.utils.site import"
)

# Now fix get_cookie_name
content = content.replace(
    "name = await self._get_current_user_name(json.loads(content))",
    "name = await self._get_current_user_name(json.loads(content) if content.strip().startswith('{') else _parse_cookie_str(content))"
)

with open(weibo_path, "w") as f:
    f.write(content)

print("5/5 weibo cookie format fix applied")

# ====== 6. Configure weibo to use proxy ======
with open(weibo_path, "r") as f:
    content = f.read()

# Add proxy to weibo's get_client
old_get_client = """    @override
    async def get_client(self, target: Target | None) -> AsyncClient:
        client = await super().get_client(target)

        if len(client.cookies) == 0:
            client.cookies.update({"dummycookie": "1"})

        return client"""

new_get_client = """    @override
    async def get_client(self, target: Target | None) -> AsyncClient:
        client = await super().get_client(target)

        if len(client.cookies) == 0:
            client.cookies.update({"dummycookie": "1"})

        return client

    @override
    async def get_query_name_client(cls) -> AsyncClient:
        from nonebot_bison.utils.http import http_client
        client = http_client(proxy="http://127.0.0.1:7890")
        if len(client.cookies) == 0:
            client.cookies.update({"dummycookie": "1"})
        return client

    @classmethod"""

if old_get_client in content:
    content = content.replace(old_get_client, new_get_client)
    print("6/6 weibo proxy configured")
else:
    print("6/6 FAIL: get_client pattern not found")

with open(weibo_path, "w") as f:
    f.write(content)

print("\nAll patches applied!")
