# Subscriber

基于 NoneBot2 + [nonebot-bison](https://github.com/MountainDash/nonebot-bison) 的社交媒体动态订阅推送 QQ 机器人。

自动监测 Bilibili、微博等平台用户动态，检测到新内容时通过 QQ 私聊/群聊推送通知。

## 架构

```
bot.py              # 入口 — 初始化 NoneBot，加载 nonebot-bison 插件
.env                # 环境配置
requirements.txt    # Python 依赖
data/               # bison 订阅数据（运行时生成）
```

### 数据流

```
Bilibili/微博 → nonebot-bison 定时轮询 → 检测新动态
→ NoneBot2 → NapCatQQ（反向 WebSocket）→ QQ 私聊/群聊推送
```

## 支持平台

nonebot-bison 支持的平台包括：

- **Bilibili** — UP 主动态、直播
- **微博** — 用户动态
- **RSS** — 任意 RSS 源
- 更多平台详见 [bison 文档](https://github.com/MountainDash/nonebot-bison)

## 部署

### 前置条件

- Python 3.10+
- NapCatQQ（作为 QQ 协议端）
- Ubuntu 云服务器（systemd 管理）

### 配置（`.env`）

| 键 | 说明 |
|---|---|
| `HOST` / `PORT` | NoneBot 监听地址（默认 `0.0.0.0:28080`） |
| `ONEBOT_ACCESS_TOKEN` | OneBot 连接令牌 |
| `SUPERUSERS` | 管理员 QQ 号（JSON 数组格式） |
| `BISON_DB_DIR` | bison 数据存储目录（默认 `data`） |

### 手动部署

```bash
git clone https://github.com/initialize-ye/Subscriber.git
cd Subscriber
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install --with-deps chromium
# 编辑 .env 配置
python bot.py
```

### 自动部署

推送到 `main` 分支后，GitHub Actions 自动部署到服务器。

需要在 GitHub 仓库 Settings → Secrets 中配置：
- `SSH_HOST` — 服务器 IP
- `SSH_USER` — SSH 用户名
- `SSH_KEY` — SSH 私钥

## NapCatQQ 配置

使用 [NapCatQQ Desktop](https://github.com/NapNeko/NapCatQQ-Desktop) 管理多账号，添加第二个 QQ 号并配置反向 WebSocket：

| 配置项 | 值 |
|---|---|
| 类型 | 反向 WebSocket |
| URL | `ws://服务器IP:28080/onebot/v11/ws` |
| Access Token | 与 `.env` 中 `ONEBOT_ACCESS_TOKEN` 一致 |

## 使用方式（QQ 命令）

通过 QQ 私聊机器人发送命令：

| 命令 | 说明 |
|---|---|
| `添加订阅` | 交互式添加订阅（选择平台 → 输入用户 ID） |
| `查看订阅` | 查看当前所有订阅 |
| `删除订阅` | 删除指定订阅 |

## 服务管理

```bash
sudo systemctl status subscriber      # 查看状态
sudo systemctl restart subscriber     # 重启
sudo journalctl -u subscriber -f      # 实时日志
```
