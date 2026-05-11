from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message
from nonebot.rule import to_me

help_matcher = on_command("help", aliases={"帮助", "?"}, rule=to_me(), priority=8, block=True)

HELP_TEXT = """订阅管理：
  添加订阅 - 交互式添加 B站/微博 订阅
  查询订阅 - 查看所有订阅
  删除订阅 - 删除订阅

Cookie 管理：
  添加cookie - 添加 Cookie
  查看cookie - 查看已添加的 Cookie
  关联cookie - 为订阅关联 Cookie
  取消关联cookie - 取消 Cookie 关联
  删除cookie - 删除 Cookie

后台：
  管理后台 - 生成管理后台地址

其他：
  help / 帮助 / ? - 显示本帮助

提示：微博需要 Cookie 才能使用"""


@help_matcher.handle()
async def handle_help():
    await help_matcher.finish(Message(HELP_TEXT))
