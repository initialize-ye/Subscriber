from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message, MessageEvent
from nonebot.log import logger
from nonebot.rule import to_me
from nonebot_plugin_saa import extract_target

from nonebot_bison.config import config
from nonebot_bison.platform import platform_manager
from nonebot_bison.types import Category

status_matcher = on_command("订阅状态", aliases={"sub_status"}, rule=to_me(), priority=8, block=True)


@status_matcher.handle()
async def handle_status(event: MessageEvent):
    try:
        user = extract_target(event)
        sub_list = await config.list_subscribe(user)
        cookie_targets = await config.get_cookie_target()
    except Exception as e:
        logger.error(f"获取订阅状态失败: {e}")
        await status_matcher.finish(Message("获取订阅状态失败，请稍后重试"))

    if not sub_list:
        await status_matcher.finish(Message("暂无已订阅账号\n请使用「添加订阅」命令添加"))

    # Build set of (platform_name, target) that have cookies
    cookie_set: set[tuple[str, str]] = set()
    for ct in cookie_targets:
        if ct.target:
            cookie_set.add((ct.target.platform_name, ct.target.target))

    lines = ["📋 订阅状态：\n"]
    for i, sub in enumerate(sub_list, 1):
        t = sub.target
        platform = platform_manager.get(t.platform_name)
        plat_name = platform.name if platform else t.platform_name

        # Categories
        if platform and platform.categories and sub.categories:
            cats = ", ".join(platform.categories[Category(c)] for c in sub.categories)
        else:
            cats = "全部"

        # Tags
        tags = ", ".join(sub.tags) if sub.tags else "无"

        # Cookie status
        has_cookie = (t.platform_name, t.target) in cookie_set
        cookie_icon = "✅" if has_cookie else "❌"

        lines.append(f"{i}. [{plat_name}] {t.target_name} ({t.target})")
        lines.append(f"   分类: {cats} | 标签: {tags} | Cookie: {cookie_icon}")

    lines.append(f"\n共 {len(sub_list)} 个订阅")
    await status_matcher.finish(Message("\n".join(lines)))
