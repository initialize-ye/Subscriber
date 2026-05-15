from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message, MessageEvent
from nonebot.log import logger
from nonebot.params import ArgPlainText
from nonebot.rule import to_me
from nonebot.typing import T_State
from nonebot_plugin_saa import extract_target

from nonebot_bison.config import config
from nonebot_bison.platform import platform_manager
from nonebot_bison.types import Category

edit_matcher = on_command("编辑订阅", aliases={"edit_sub"}, rule=to_me(), priority=8, block=True)


def _format_categories(platform, cats: list[int]) -> str:
    if not platform or not platform.categories:
        return "全部"
    return ", ".join(platform.categories[Category(c)] for c in cats)


def _parse_categories(platform, text: str) -> list[int] | None:
    """Parse user input into category list. Returns None if '不变'."""
    if text.strip() == "不变":
        return None
    if not platform or not platform.categories:
        return []
    # Try matching by number
    try:
        nums = [int(x) for x in text.replace(",", " ").replace("，", " ").split()]
        valid = [c for c in nums if c in platform.categories]
        if valid:
            return valid
    except ValueError:
        pass
    # Try matching by name
    cat_map = {v: k for k, v in platform.categories.items()}
    parts = [x.strip() for x in text.replace(",", " ").replace("，", " ").split()]
    result = [cat_map[p] for p in parts if p in cat_map]
    return result if result else None


@edit_matcher.handle()
async def start_edit(event: MessageEvent, state: T_State):
    try:
        user = extract_target(event)
        sub_list = await config.list_subscribe(user)
    except Exception as e:
        logger.error(f"获取订阅列表失败: {e}")
        await edit_matcher.finish(Message("获取订阅列表失败，请稍后重试"))

    if not sub_list:
        await edit_matcher.finish(Message("暂无已订阅账号\n请使用「添加订阅」命令添加"))

    state["sub_list"] = sub_list
    state["user"] = user

    lines = ["📝 请输入要编辑的订阅序号：\n"]
    for i, sub in enumerate(sub_list, 1):
        t = sub.target
        platform = platform_manager.get(t.platform_name)
        plat_name = platform.name if platform else t.platform_name
        cats = _format_categories(platform, sub.categories)
        tags = ", ".join(sub.tags) if sub.tags else "无"
        lines.append(f"{i}. [{plat_name}] {t.target_name} | 分类: {cats} | 标签: {tags}")

    lines.append("\n输入「取消」中止")
    await edit_matcher.send(Message("\n".join(lines)))


@edit_matcher.got("index")
async def got_index(event: MessageEvent, state: T_State, index: str = ArgPlainText()):
    if index.strip() == "取消":
        await edit_matcher.finish("已取消编辑")

    sub_list = state["sub_list"]
    try:
        idx = int(index.strip())
        if idx < 1 or idx > len(sub_list):
            raise ValueError
    except ValueError:
        await edit_matcher.reject(f"请输入 1-{len(sub_list)} 的序号")

    sub = sub_list[idx - 1]
    t = sub.target
    platform = platform_manager.get(t.platform_name)
    state["platform"] = platform
    state["sub"] = sub

    cats_text = _format_categories(platform, sub.categories)
    if platform and platform.categories:
        cat_options = " | ".join(f"{k}:{v}" for k, v in platform.categories.items())
        prompt = f"当前分类: {cats_text}\n可选: {cat_options}\n输入新分类编号（空格分隔），或输入「不变」："
    else:
        prompt = f"当前分类: {cats_text}\n该平台无分类选项，输入「不变」跳过："

    await edit_matcher.send(Message(prompt))


@edit_matcher.got("cats")
async def got_cats(state: T_State, cats: str = ArgPlainText()):
    if cats.strip() == "取消":
        await edit_matcher.finish("已取消编辑")

    platform = state["platform"]
    result = _parse_categories(platform, cats)
    if result is None:
        state["new_cats"] = state["sub"].categories
    else:
        state["new_cats"] = result

    current_tags = ", ".join(state["sub"].tags) if state["sub"].tags else "无"
    await edit_matcher.send(
        Message(f"当前标签: {current_tags}\n输入新标签（空格分隔），输入「无」清除，或输入「不变」：")
    )


@edit_matcher.got("tags")
async def got_tags(event: MessageEvent, state: T_State, tags: str = ArgPlainText()):
    if tags.strip() == "取消":
        await edit_matcher.finish("已取消编辑")

    sub = state["sub"]
    if tags.strip() == "不变":
        new_tags = sub.tags
    elif tags.strip() == "无":
        new_tags = []
    else:
        new_tags = [t.strip() for t in tags.replace(",", " ").replace("，", " ").split() if t.strip()]

    try:
        await config.update_subscribe(
            user=state["user"],
            target=sub.target.target,
            target_name=sub.target.target_name,
            platform_name=sub.target.platform_name,
            cats=state["new_cats"],
            tags=new_tags,
        )
    except Exception as e:
        logger.error(f"更新订阅失败: {e}")
        await edit_matcher.finish(Message("更新订阅失败，请稍后重试"))

    platform = state["platform"]
    cats_text = _format_categories(platform, state["new_cats"])
    tags_text = ", ".join(new_tags) if new_tags else "无"
    await edit_matcher.finish(Message(f"✅ 已更新订阅\n  分类: {cats_text}\n  标签: {tags_text}"))
