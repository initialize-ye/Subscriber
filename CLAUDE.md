# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

QQ chatbot that monitors social media platforms (Bilibili, Weibo, RSS) for new posts and pushes notifications to QQ users. Built on **NoneBot2** with **nonebot-bison** as the subscription/polling engine.

## Commands

```bash
# Setup
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install --with-deps chromium

# Run locally
python bot.py

# Apply bison patches (must re-run after pip install/upgrade of nonebot-bison)
python patch_bison.py

# Production service management
sudo systemctl status subscriber
sudo systemctl restart subscriber
sudo journalctl -u subscriber -f

# Syntax check (same as CI uses)
python -m py_compile bot.py
```

No formal test suite or linter is configured.

## Architecture

**Entry point:** `bot.py` — loads `.env`, initializes NoneBot2, registers OneBot v11 adapter, loads plugins in order: apscheduler → bison → `my_plugins/`.

**Data flow:** Social platform → nonebot-bison (APScheduler polls) → NoneBot2 message dispatch → NapCatQQ (reverse WebSocket, OneBot v11 protocol) → QQ chat.

**Communication model:** Bot runs as a WebSocket *server* on `0.0.0.0:28080`. NapCatQQ (the QQ protocol client) connects *to it* via reverse WebSocket. All QQ commands require @mentioning the bot (`rule=to_me()`).

**Custom plugins** (`my_plugins/`): NoneBot2 command handlers. `help.py` provides help text; `cookie_mgr.py` lists stored cookies. New commands follow the pattern: `on_command("命令名", rule=to_me(), priority=8, block=True)`.

**Monkey-patching pattern:** `patch_bison.py` directly modifies installed nonebot-bison source files inside `.venv/` to disable unused platforms, fix bugs, add proxy support, and improve error messages. This is not imported at runtime — it's run manually after dependency installation. Must be re-applied after any `pip install` or upgrade of nonebot-bison.

## Key Configuration

All runtime config lives in `.env` (loaded by python-dotenv before NoneBot init):

| Key | Purpose |
|---|---|
| `HOST` / `PORT` | NoneBot listen address (default `0.0.0.0:28080`) |
| `ONEBOT_ACCESS_TOKEN` | Auth token for OneBot WebSocket |
| `SUPERUSERS` | Admin QQ numbers (JSON array) |
| `BISON_DB_DIR` | SQLite data directory (default `data/`) |
| `BISON_USE_BROWSER` | Enable headless browser for scraping |
| `BISON_BROWSER_UA` | Browser user agent string |

## Deployment

Pushing to `main` triggers `.github/workflows/deploy.yml` → SSH to Ubuntu server → pull code → restore `.env` and `data/` → `pip install` → `py_compile` check → restart systemd service. Auto-rolls back on failure.

## Conventions

- Chinese command names for user-facing QQ interactions (添加订阅, 查看订阅, etc.)
- Weibo requires authenticated cookies (JSON or HTTP `key=value;` format) — managed via QQ commands
- Weibo API requests go through local proxy at `127.0.0.1:7890` (configured in `patch_bison.py`)
- `data/` directory is gitignored — subscription database is runtime state, not version-controlled
