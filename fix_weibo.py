"""Add weibo.com/UID format support to bison weibo platform."""
import re

FILEPATH = "/home/ubuntu/Subscriber/.venv/lib/python3.12/site-packages/nonebot_bison/platform/weibo.py"

with open(FILEPATH, "r") as f:
    content = f.read()

# Original parse_target method
old = '''    async def parse_target(cls, target_text: str) -> Target:
        if re.match(r"\d+", target_text):
            return Target(target_text)
        elif match := re.match(r"(?:https?://)?weibo\.com/u/(\d+)", target_text):
            # 都2202年了应该不会有http了吧，不过还是防一手
            return Target(match.group(1))
        else:
            raise cls.ParseTargetException(prompt="正确格式:\n1. 用户数字UID\n2. https://weibo.com/u/xxxx")'''

new = '''    async def parse_target(cls, target_text: str) -> Target:
        if re.match(r"\d+", target_text):
            return Target(target_text)
        elif match := re.match(r"(?:https?://)?weibo\.com/u/(\d+)", target_text):
            return Target(match.group(1))
        elif match := re.match(r"(?:https?://)?weibo\.com/(\d+)", target_text):
            return Target(match.group(1))
        else:
            raise cls.ParseTargetException(prompt="正确格式:\n1. 用户数字UID (如 7618923072)\n2. https://weibo.com/7618923072\n3. https://weibo.com/u/7618923072")'''

if old in content:
    content = content.replace(old, new)
    with open(FILEPATH, "w") as f:
        f.write(content)
    print("OK: weibo.py patched")
else:
    print("FAIL: old pattern not found in weibo.py")
