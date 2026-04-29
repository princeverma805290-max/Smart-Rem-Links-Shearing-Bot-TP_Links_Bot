"""
bot.py
======
Main entry point.
"""

import asyncio
import logging

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


# ── Startup ──────────────────────────────────────────
async def main():
    await app.start()

    # Auto-fetch bot username
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
