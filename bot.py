"""
bot.py
======
Main entry point with fake web server for Render.
"""

import asyncio
import logging
import os
from aiohttp import web

from pyrogram import Client, idle
import config.settings as cfg
from handlers import (
    register_start,
    register_join_request,
    register_channel_cmds,
    register_admin_cmds,
)

# ── Logging ──────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Pyrogram client ──────────────────────────────────
app = Client(
    "auto_approve_bot",
    api_id=cfg.API_ID,
    api_hash=cfg.API_HASH,
    bot_token=cfg.BOT_TOKEN,
)

# ── Register all handlers ────────────────────────────
register_start(app)
register_join_request(app)
register_channel_cmds(app)
register_admin_cmds(app)


# ── Fake web server (Render ke liye) ─────────────────
async def handle(request):
    return web.Response(text="Bot is running! ✅")

async def start_web_server():
    port = int(os.environ.get("PORT", 8080))
    web_app = web.Application()
    web_app.router.add_get("/", handle)
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"✅ Web server started on port {port}")


# ── Main ─────────────────────────────────────────────
async def main():
    # Start fake web server
    await start_web_server()

    # Start bot
    await app.start()

    me               = await app.get_me()
    cfg.BOT_USERNAME = me.username

    from utils.database import get_config, get_all_channels, count_users
    cfg_doc     = await get_config()
    all_ch      = await get_all_channels()
    total_users = await count_users()

    logger.info(f"✅ Bot started as @{me.username}")
    logger.info(f"👑 Owner ID  : {cfg_doc.get('owner_id', cfg.OWNER_ID)}")
    logger.info(f"📢 Channels  : {len(all_ch)}")
    logger.info(f"👥 Users     : {total_users}")
    logger.info(f"⚡ Auto Mode : {'ON' if cfg_doc.get('req_mode', True) else 'OFF'}")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    await idle()
    await app.stop()


if __name__ == "__main__":
    asyncio.run(main())
