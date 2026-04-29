"""
handlers/join_request.py
========================
Auto-approve join requests + DM sender
MongoDB se channel info leta hai
"""

import asyncio
import time
import logging

from pyrogram import Client
from pyrogram.types import ChatJoinRequest
from pyrogram.errors import UserIsBlocked, PeerIdInvalid, FloodWait

import config.settings as cfg
from utils.database import (
    get_config, get_channel, add_pending, remove_pending,
    inc_stat, count_pending
)
from utils.keyboards import approval_dm_kb

logger = logging.getLogger(__name__)


def register_join_request(app: Client):

    @app.on_chat_join_request()
    async def handle_join_request(client: Client, request: ChatJoinRequest):
        channel_id   = request.chat.id
        channel_name = request.chat.title or "Channel"
        user         = request.from_user

        await inc_stat("total_requests")

        # Save to pending
        await add_pending(
            channel_id=channel_id,
            user_id=user.id,
            first_name=user.first_name or "User",
            username=user.username or "",
        )

        # Check per-channel settings
        channel_info = await get_channel(channel_id)
        if not channel_info:
            return

        approve_on = channel_info.get("approve_on", True)
        dm_on      = channel_info.get("dm_on", True)

        # Check global mode
        cfg_doc = await get_config()
        if not cfg_doc.get("req_mode", True) or not approve_on:
            return  # Manual mode ya channel disabled

        delay = cfg_doc.get("req_delay", cfg.DEFAULT_REQ_DELAY)
        await asyncio.sleep(delay)

        try:
            await client.approve_chat_join_request(channel_id, user.id)
            await inc_stat("total_approved")
            await remove_pending(channel_id, user.id)

            if dm_on:
                await send_approval_dm(
                    client, user, channel_id, channel_name, channel_info
                )

        except FloodWait as e:
            logger.warning(f"FloodWait {e.value}s")
            await asyncio.sleep(e.value)
        except Exception as e:
            logger.error(f"Approve error {user.id}: {e}")


async def send_approval_dm(client: Client, user, channel_id: int,
                            channel_name: str, channel_info: dict):
    """Send approval DM with photo + quoted text + 2 buttons."""

    # 5 min expiry join link
    try:
        inv = await client.create_chat_invite_link(
            channel_id,
            expire_date=int(time.time()) + cfg.LINK_EXPIRY_SECONDS,
            member_limit=1,
        )
        ch_join_link = inv.invite_link
    except Exception:
        ch_join_link = channel_info.get("invite_link", "")

    # User mention
    if user.username:
        mention = f"[@{user.username}](tg://user?id={user.id})"
    else:
        mention = f"[{user.first_name}](tg://user?id={user.id})"

    caption = (
        f"ʜᴇʏ {mention},\n\n"
        f"ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ᴛᴏ ᴊᴏɪɴ {channel_name} "
        f"ʜᴀs ʙᴇᴇɴ ᴀᴘᴘʀᴏᴠᴇᴅ."
    )

    try:
        await client.send_photo(
            chat_id=user.id,
            photo=cfg.PIC_APPROVE,
            caption=caption,
            reply_markup=approval_dm_kb(
                channel_name, ch_join_link, cfg.MY_UPDATES_CH
            ),
        )
    except (UserIsBlocked, PeerIdInvalid):
        logger.warning(f"Cannot DM {user.id} — blocked or no chat")
    except Exception as e:
        logger.warning(f"DM failed {user.id}: {e}")
