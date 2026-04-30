import asyncio
import logging
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from pyrogram import Client, idle
import config.settings as cfg
from handlers import (
    register_start,
    register_join_request,
    register_channel_cmds,
    register_admin_cmds,
)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")
    def log_message(self, format, *args):
        pass

def run_http_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), Handler)
    logger.info(f"HTTP server started on port {port}")
    server.serve_forever()


# ── In-memory session (file nahi banega) ─────────────
app = Client(
    ":memory:",
    api_id=cfg.API_ID,
    api_hash=cfg.API_HASH,
    bot_token=cfg.BOT_TOKEN,
)

register_start(app)
register_join_request(app)
register_channel_cmds(app)
register_admin_cmds(app)


async def main():
    t = threading.Thread(target=run_http_server, daemon=True)
    t.start()

    await app.start()

    me = await app.get_me()
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

    await idle()
    await app.stop()


if __name__ == "__main__":
    asyncio.run(main())
    
