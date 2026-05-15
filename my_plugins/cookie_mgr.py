from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message, MessageEvent
from nonebot.log import logger
from nonebot.rule import to_me

from nonebot_bison.config import config

view_cookie_matcher = on_command("查看cookie", aliases={"我的cookie", "cookie列表"}, rule=to_me(), priority=8, block=True)


@view_cookie_matcher.handle()
async def handle_view_cookie(event: MessageEvent):
    try:
        cookies = await config.get_cookie(is_anonymous=False)
        targets = await config.get_cookie_target()
    except Exception as e:
        logger.error(f"获取 Cookie 列表失败: {e}")
        await view_cookie_matcher.finish(Message("获取 Cookie 列表失败，请稍后重试"))

    if not cookies:
        await view_cookie_matcher.finish(Message("暂无已添加的 Cookie"))

    # Group associations by cookie_id
    assoc_count = {}
    for t in targets:
        assoc_count[t.cookie_id] = assoc_count.get(t.cookie_id, 0) + 1

    lines = ["📋 已添加的 Cookie："]
    for c in cookies:
        status_icon = "✅" if c.status == "success" else "⏸"
        name = c.cookie_name or "未命名"
        site = c.site_name or "未知平台"
        n = assoc_count.get(c.id, 0)
        assoc = f"关联 {n} 个订阅" if n else "未关联"
        lines.append(f"#{c.id} {site} - {name} {status_icon} | {assoc}")

    lines.append(f"\n共 {len(cookies)} 个")
    await view_cookie_matcher.finish(Message("\n".join(lines)))
