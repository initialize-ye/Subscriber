from nonebot import on_command
from nonebot.adapters import Message
from nonebot.params import CommandArg
from nonebot.rule import to_me

help_matcher = on_command("help", aliases={"帮助", "?"}, rule=to_me(), priority=1, block=True)

HELP_TEXT = """订阅管理：
  添加订阅 - 添加 B站/微博 订阅
  查询订阅 - 查看所有订阅
  删除订阅 - 删除指定订阅

Cookie 管理：
  添加cookie <平台> <Cookie> - 为微博等平台添加登录 Cookie
  关联cookie <平台> <UID> - 为订阅关联 Cookie
  取消关联cookie <平台> <UID> - 取消 Cookie 关联
  删除cookie <平台> <编号> - 删除 Cookie

后台管理：
  管理后台 - 生成管理后台地址
  群管理 - 群聊管理入口

其他：
  help / 帮助 / ? - 显示本帮助
  stats - 查看统计信息

提示：微博需要添加 Cookie 才能使用，发 "添加cookie weibo <你的Cookie>" """

HELP_DETAIL = {
    "添加订阅": "添加订阅\n交互式添加 B站/微博 订阅，机器人会引导选择平台和输入 UID",
    "查询订阅": "查询订阅\n列出所有已添加的订阅及其状态",
    "删除订阅": "删除订阅\n按编号删除指定订阅",
    "添加cookie": "添加cookie weibo <Cookie>\n为微博添加登录 Cookie（从浏览器复制）",
    "添加订阅": "添加订阅\n交互式添加 B站/微博 订阅",
}


@help_matcher.handle()
async def handle_help():
    await help_matcher.finish(Message(HELP_TEXT))
