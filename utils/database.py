"""
utils/database.py
=================
MongoDB se sara data save/load hota hai.
Bot restart hone par bhi sab data safe rahega.

Collections:
  - bot_config     : owner_id, req_mode, req_delay, start_pic, stats
  - admins         : list of admin user_ids
  - channels       : channel_id, channel_name, invite_link, approve_on, dm_on, token
  - tokens         : req_token, channel_id, expires_at  (per channel — ek hi token)
  - pending        : channel_id, user_id, first_name, username, req_time
  - users          : user_id
"""

import time
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from config.settings import MONGO_URL, OWNER_ID, DEFAULT_REQ_DELAY, PIC_START

logger = logging.getLogger(__name__)

# ── MongoDB client ────────────────────────────────────
client = AsyncIOMotorClient(MONGO_URL)
db     = client["auto_approve_bot"]

# Collections
col_config  = db["bot_config"]
col_admins  = db["admins"]
col_channels= db["channels"]
col_tokens  = db["tokens"]
col_pending = db["pending"]
col_users   = db["users"]


# ════════════════════════════════════════════════════
#  CONFIG
# ════════════════════════════════════════════════════

async def get_config() -> dict:
    cfg = await col_config.find_one({"_id": "main"})
    if not cfg:
        cfg = {
            "_id":       "main",
            "owner_id":  OWNER_ID,
            "req_mode":  True,
            "req_delay": DEFAULT_REQ_DELAY,
            "start_pic": PIC_START,
            "stats": {
                "total_approved": 0,
                "total_requests": 0,
            }
        }
        await col_config.insert_one(cfg)
    return cfg


async def set_config(key: str, value):
    await col_config.update_one(
        {"_id": "main"},
        {"$set": {key: value}},
        upsert=True
    )


async def inc_stat(key: str, amount: int = 1):
    await col_config.update_one(
        {"_id": "main"},
        {"$inc": {f"stats.{key}": amount}},
        upsert=True
    )


# ════════════════════════════════════════════════════
#  OWNER / ADMINS
# ════════════════════════════════════════════════════

async def get_owner() -> int:
    cfg = await get_config()
    return cfg.get("owner_id", OWNER_ID)


async def is_owner(uid: int) -> bool:
    owner = await get_owner()
    return uid == owner


async def is_admin(uid: int) -> bool:
    if await is_owner(uid):
        return True
    doc = await col_admins.find_one({"user_id": uid})
    return doc is not None


async def add_admin(uid: int) -> bool:
    """Returns False if already admin."""
    if await col_admins.find_one({"user_id": uid}):
        return False
    await col_admins.insert_one({"user_id": uid})
    return True


async def remove_admin(uid: int) -> bool:
    """Returns False if not found."""
    res = await col_admins.delete_one({"user_id": uid})
    return res.deleted_count > 0


async def get_all_admins() -> list:
    docs = col_admins.find({})
    return [d["user_id"] async for d in docs]


# ════════════════════════════════════════════════════
#  CHANNELS
# ════════════════════════════════════════════════════

async def add_channel(channel_id: int, channel_name: str,
                       invite_link: str, token: str):
    await col_channels.update_one(
        {"channel_id": channel_id},
        {"$set": {
            "channel_id":   channel_id,
            "channel_name": channel_name,
            "invite_link":  invite_link,
            "token":        token,
            "approve_on":   True,
            "dm_on":        True,
        }},
        upsert=True
    )


async def remove_channel(channel_id: int) -> bool:
    res = await col_channels.delete_one({"channel_id": channel_id})
    # Also remove its token and pending
    await col_tokens.delete_one({"channel_id": channel_id})
    await col_pending.delete_many({"channel_id": channel_id})
    return res.deleted_count > 0


async def get_channel(channel_id: int) -> dict | None:
    return await col_channels.find_one({"channel_id": channel_id})


async def get_all_channels() -> list:
    docs = col_channels.find({})
    return [d async for d in docs]


async def update_channel(channel_id: int, key: str, value):
    await col_channels.update_one(
        {"channel_id": channel_id},
        {"$set": {key: value}}
    )


async def channel_exists(channel_id: int) -> bool:
    doc = await col_channels.find_one({"channel_id": channel_id})
    return doc is not None


# ════════════════════════════════════════════════════
#  TOKENS  (ek channel = ek hi token, regenerate karo to update ho)
# ════════════════════════════════════════════════════

async def set_token(channel_id: int, token: str, expires_at: float):
    """
    Ek channel ke liye hamesha ek hi token — agar dobara same
    channel ki link bano to same token milega (ya update hoga).
    """
    await col_tokens.update_one(
        {"channel_id": channel_id},
        {"$set": {
            "channel_id": channel_id,
            "token":      token,
            "expires_at": expires_at,
        }},
        upsert=True
    )


async def get_token_by_channel(channel_id: int) -> dict | None:
    """Get token doc for a channel."""
    return await col_tokens.find_one({"channel_id": channel_id})


async def get_channel_by_token(token: str) -> dict | None:
    """Get token doc by token string."""
    doc = await col_tokens.find_one({"token": token})
    if not doc:
        return None
    # Check expiry
    if doc["expires_at"] < time.time():
        return None   # Expired
    return doc


async def refresh_token(channel_id: int, new_token: str,
                         expires_at: float):
    """Update token for a channel (same channel, new token string)."""
    await set_token(channel_id, new_token, expires_at)


async def clean_expired_tokens():
    """Delete all expired tokens from DB."""
    now = time.time()
    res = await col_tokens.delete_many({"expires_at": {"$lt": now}})
    if res.deleted_count:
        logger.info(f"Cleaned {res.deleted_count} expired tokens")


# ════════════════════════════════════════════════════
#  PENDING REQUESTS
# ════════════════════════════════════════════════════

async def add_pending(channel_id: int, user_id: int,
                       first_name: str, username: str):
    # Avoid duplicate
    exists = await col_pending.find_one({
        "channel_id": channel_id, "user_id": user_id
    })
    if not exists:
        await col_pending.insert_one({
            "channel_id": channel_id,
            "user_id":    user_id,
            "first_name": first_name,
            "username":   username,
            "req_time":   time.time(),
        })


async def remove_pending(channel_id: int, user_id: int):
    await col_pending.delete_one({
        "channel_id": channel_id, "user_id": user_id
    })


async def get_pending_by_channel(channel_id: int) -> list:
    docs = col_pending.find({"channel_id": channel_id})
    return [d async for d in docs]


async def get_all_pending() -> list:
    docs = col_pending.find({})
    return [d async for d in docs]


async def count_pending(channel_id: int) -> int:
    return await col_pending.count_documents({"channel_id": channel_id})


# ════════════════════════════════════════════════════
#  USERS
# ════════════════════════════════════════════════════

async def add_user(user_id: int):
    exists = await col_users.find_one({"user_id": user_id})
    if not exists:
        await col_users.insert_one({"user_id": user_id})


async def get_all_users() -> list:
    docs = col_users.find({})
    return [d["user_id"] async for d in docs]


async def count_users() -> int:
    return await col_users.count_documents({})


async def remove_user(user_id: int):
    await col_users.delete_one({"user_id": user_id})
      
