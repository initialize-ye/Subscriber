import os
import sys

import nonebot
from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter
from dotenv import load_dotenv


def main() -> None:
    load_dotenv()

    # Validate critical environment variables
    _required = ["ONEBOT_ACCESS_TOKEN"]
    _missing = [k for k in _required if not os.environ.get(k)]
    if _missing:
        print(f"ERROR: missing required environment variables: {', '.join(_missing)}")
        print("Copy .env.example to .env and fill in the values.")
        sys.exit(1)

    nonebot.init()
    driver = nonebot.get_driver()
    driver.register_adapter(OneBotV11Adapter)
    nonebot.load_plugin("nonebot_plugin_apscheduler")
    nonebot.load_plugin("nonebot_bison")
    nonebot.load_plugins("my_plugins")
    nonebot.run()


if __name__ == "__main__":
    main()
