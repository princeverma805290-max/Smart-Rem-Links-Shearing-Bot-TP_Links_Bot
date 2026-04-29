"""
config/settings.py
==================
Saari settings ek jagah — .env ya Render variables se load hoti hain
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Credentials ──────────────────────────────────────
API_ID    = int(os.environ["API_ID"])
API_HASH  = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
OWNER_ID  = int(os.environ["OWNER_ID"])
MONGO_URL = os.environ["MONGO_URL"]

# ── Bot username (startup par auto-fill hoga) ────────
BOT_USERNAME = ""

# ── Images ───────────────────────────────────────────
PIC_START    = "https://graph.org/file/c45ac4408f69284ad2c8c-68340af5343e9aaa11.jpg"
PIC_ABOUT    = "https://graph.org/file/58ab949dae3199bd85950-9bd5847274e7d03c2d.jpg"
PIC_CHANNELS = "https://graph.org/file/a532833489fea2f887248-11386494e2152588a7.jpg"
PIC_APPROVE  = "https://graph.org/file/65f5e31912b4bc796b332-1cb31de4e7ac9aa5b4.jpg"

# ── Fixed links ──────────────────────────────────────
MY_CHANNEL    = "https://t.me/TP_02_Bots"
MY_UPDATES_CH = "https://t.me/Crunchyroll_Offical0"
PYTHON_DOCS   = "https://docs.python.org/3/"
PYROGRAM_DOCS = "https://docs.pyrogram.org/"
MONGODB_DOCS  = "https://www.mongodb.com/docs/"

# ── Timings ──────────────────────────────────────────
LINK_EXPIRY_SECONDS = 300    # 5 minutes
DEFAULT_REQ_DELAY   = 4      # seconds before approving
