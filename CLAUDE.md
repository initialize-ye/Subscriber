# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

QQ chatbot that monitors social media platforms (Bilibili, Weibo, RSS) for new posts and pushes notifications to QQ users. Built on **NoneBot2** with **nonebot-bison** as the subscription/polling engine.

## Commands

```bash
# Setup (use .venv/Scripts/ on Windows)
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install --with-deps chromium

# Apply bison patches (must re-run after pip install/upgrade of nonebot-bison)
python patch_bison.py

# Run locally
python bot.py

# Syntax check — CI checks all project .py files
python -m py_compile bot.py
python -m py_compile my_plugins/help.py
python -m py_compile my_plugins/cookie_mgr.py
python -m py_compile patch_bison.py

# Production service management
sudo systemctl status subscriber
sudo systemctl restart subscriber
sudo journalctl -u subscriber -f
```

No formal test suite or linter is configured. CI uses `py_compile` as the smoke test.

## Architecture

**Entry point:** `bot.py` — loads `.env`, initializes NoneBot2, registers OneBot v11 adapter, loads plugins in order: apscheduler → bison → `my_plugins/`.

**Data flow:** Social platform → nonebot-bison (APScheduler polls) → NoneBot2 message dispatch → NapCatQQ (reverse WebSocket, OneBot v11 protocol, URL: `ws://<host>:28080/onebot/v11/ws`) → QQ chat.

**Communication model:** Bot runs as a WebSocket *server* on `0.0.0.0:28080`. NapCatQQ (the QQ protocol client) connects *to it* via reverse WebSocket. All QQ commands require @mentioning the bot (`rule=to_me()`).

**Enabled platforms:** Only Bilibili (动态) and Weibo (微博) are kept. All other nonebot-bison platforms (arknights, ff14, ncm, rss, ceobecanteen, bilibili-live, bilibili-bangumi) are disabled by `patch_bison.py`.

**Custom plugins** (`my_plugins/`): Lightweight NoneBot2 command handlers that route user commands into nonebot-bison's built-in subscription management. `help.py` provides the command list; `cookie_mgr.py` lists stored cookies with their validation status and subscription associations.

**Monkey-patching pattern:** `patch_bison.py` (21 steps) directly modifies installed nonebot-bison source files inside `.venv/` — it replaces metrics imports with safe fallbacks, disables 7+ unused platforms, fixes weibo target parsing and cookie handling, injects proxy configuration for weibo API calls, and improves Chinese-language error messages throughout the bison subscription UI. It is not imported at runtime — run manually after dependency installation and must be re-applied after any `pip install` or upgrade of nonebot-bison.

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

- Python 3.10+ required
- Chinese command names for user-facing QQ interactions (添加订阅, 查看订阅, etc.)
- Weibo requires authenticated cookies (JSON or HTTP `key=value;` format) — managed via QQ commands
- Weibo API requests go through local proxy at `127.0.0.1:7890` (configured in `patch_bison.py`)
- Playwright Chromium is used by nonebot-bison for HTML rendering (screenshots in QQ messages)
- `data/` directory is gitignored — subscription database is runtime state, not version-controlled
- `.env` is gitignored — use `.env.example` as template, create `.env` manually on server
