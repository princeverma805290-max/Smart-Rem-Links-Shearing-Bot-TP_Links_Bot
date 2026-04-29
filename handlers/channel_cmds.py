"""
handlers/channel_cmds.py
========================
/addch /delch /channels /reqlink /links /bulklink
/approveon /approveoff /unapprove

IMPORTANT:
- Ek channel = hamesha ek hi token (same channel dobara link
  banao to same token update hoga, alag nahi banega)
- Alag channel = alag token
"""

import secrets
import time

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

import config.settings as cfg
from utils.database import (
    is_admin, add_channel, remove_channel, get_channel,
    get_all_channels, update_channel, channel_exists,
    set_token, get_token_by_channel, clean_expired_tokens,
    count_pending
)


def register_channel_cmds(app: Client):

    # ── /addch ───────────────────────────────────────
    @app.on_message(filters.command("addch") & filters.private)
    async def cmd_addch(client: Client, message: Message):
        if not await is_admin(message.from_user.id):
            await message.reply("❌ Admins only!"); return

        if len(message.command) < 2:
            await message.reply(
                "⚠️ Usage: `/addch <channel_id>`\n\n"
                "Example: `/addch -1001234567890`"
            ); return

        try:
            cid = int(message.command[1])
        except ValueError:
            await message.reply("❌ Invalid channel ID."); return

        # Check bot is admin in channel
        try:
            chat       = await client.get_chat(cid)
            bot_member = await client.get_chat_member(cid, "me")
            if bot_member.status.value not in ("administrator", "creator"):
                await message.reply(
                    "❌ Bot is not admin in that channel!\n"
                    "Please make bot admin first, then try again."
                ); return
        except Exception as e:
            await message.reply(f"❌ Error accessing channel: `{e}`"); return

        # Already connected?
        if await channel_exists(cid):
            # Get existing token
            tok_doc  = await get_token_by_channel(cid)
            if tok_doc:
                bot_link = f"https://t.me/{cfg.BOT_USERNAME}?start=req_{tok_doc['token']}"
                await message.reply(
                    f"ℹ️ Channel already connected!\n\n"
                    f"🔗 **Existing Link:**\n`{bot_link}`\n\n"
                    f"Use `/reqlink {cid}` to refresh the link."
                ); return

        # Create Telegram invite link
        try:
            inv = await client.create_chat_invite_link(
                cid, creates_join_request=True, name="AutoApprove"
            )
            invite_link = inv.invite_link
        except Exception as e:
            await message.reply(
                f"❌ Could not create invite link: `{e}`"
            ); return

        # Generate token — one per channel
        token      = secrets.token_urlsafe(12)
        expires_at = time.time() + cfg.LINK_EXPIRY_SECONDS

        await add_channel(cid, chat.title or "Channel", invite_link, token)
        await set_token(cid, token, expires_at)

        bot_link = f"https://t.me/{cfg.BOT_USERNAME}?start=req_{token}"
        await message.reply(
            f"✅ **Channel Connected!**\n\n"
            f"📢 **{chat.title}**\n"
            f"🆔 `{cid}`\n\n"
            f"🔗 **Share Link (expires 5 min):**\n`{bot_link}`\n\n"
            f"Use `/reqlink {cid}` to generate fresh link anytime."
        )

    # ── /delch ───────────────────────────────────────
    @app.on_message(filters.command("delch") & filters.private)
    async def cmd_delch(client: Client, message: Message):
        if not await is_admin(message.from_user.id):
            await message.reply("❌ Admins only!"); return

        if len(message.command) < 2:
            await message.reply("⚠️ Usage: `/delch <channel_id>`"); return

        try:
            cid = int(message.command[1])
        except ValueError:
            await message.reply("❌ Invalid ID."); return

        ch = await get_channel(cid)
        if not ch:
            await message.reply("ℹ️ Channel not found."); return

        await remove_channel(cid)
        await message.reply(f"✅ Channel **{ch['channel_name']}** removed.")

    # ── /channels ────────────────────────────────────
    @app.on_message(filters.command("channels") & filters.private)
    async def cmd_channels(client: Client, message: Message):
        if not await is_admin(message.from_user.id):
            await message.reply("❌ Admins only!"); return

        all_ch = await get_all_channels()
        if not all_ch:
            await message.reply("ℹ️ No channels connected."); return

        text = "📋 **Connected Channels:**\n\n"
        for i, ch in enumerate(all_ch, 1):
            pending = await count_pending(ch["channel_id"])
            ap_stat = "🟢 ON" if ch.get("approve_on", True) else "🔴 OFF"
            dm_stat = "🟢 ON" if ch.get("dm_on", True) else "🔴 OFF"
            text += (
                f"{i}. **{ch['channel_name']}**\n"
                f"   🆔 `{ch['channel_id']}`\n"
                f"   ⚡ Auto-Approve: {ap_stat}\n"
                f"   💬 DM: {dm_stat}\n"
                f"   ⏳ Pending: `{pending}`\n\n"
            )
        await message.reply(text)

    # ── /reqlink ─────────────────────────────────────
    @app.on_message(filters.command("reqlink") & filters.private)
    async def cmd_reqlink(client: Client, message: Message):
        if not await is_admin(message.from_user.id):
            await message.reply("❌ Admins only!"); return

        all_ch = await get_all_channels()
        if not all_ch:
            await message.reply("ℹ️ No channels. Use /addch first."); return

        # Optional: specific channel
        target_cid = None
        if len(message.command) > 1:
            try:
                target_cid = int(message.command[1])
            except ValueError:
                pass

        await clean_expired_tokens()
        text = "🔗 **Request Links (expire in 5 min):**\n\n"
        found = False

        for ch in all_ch:
            cid = ch["channel_id"]
            if target_cid and cid != target_cid:
                continue
            found = True

            # SAME channel = SAME token updated (not new one)
            expires_at = time.time() + cfg.LINK_EXPIRY_SECONDS
            tok_doc    = await get_token_by_channel(cid)

            if tok_doc:
                # Reuse same token string, just refresh expiry
                token = tok_doc["token"]
            else:
                token = secrets.token_urlsafe(12)

            await set_token(cid, token, expires_at)
            bot_link = f"https://t.me/{cfg.BOT_USERNAME}?start=req_{token}"
            text += f"📢 **{ch['channel_name']}**\n`{bot_link}`\n\n"

        if not found:
            await message.reply("❌ Channel not found."); return

        await message.reply(text)

    # ── /links ───────────────────────────────────────
    @app.on_message(filters.command("links") & filters.private)
    async def cmd_links(client: Client, message: Message):
        if not await is_admin(message.from_user.id):
            await message.reply("❌ Admins only!"); return

        all_ch = await get_all_channels()
        if not all_ch:
            await message.reply("ℹ️ No channels."); return

        text = "🔗 **Channel Invite Links:**\n\n"
        for ch in all_ch:
            text += f"📢 **{ch['channel_name']}**\n`{ch['invite_link']}`\n\n"
        await message.reply(text)

    # ── /bulklink ────────────────────────────────────
    @app.on_message(filters.command("bulklink") & filters.private)
    async def cmd_bulklink(client: Client, message: Message):
        if not await is_admin(message.from_user.id):
            await message.reply("❌ Admins only!"); return

        all_ch = await get_all_channels()
        if not all_ch:
            await message.reply("ℹ️ No channels connected."); return

        await clean_expired_tokens()
        text     = "📦 **Bulk Links (all channels, expire 5 min):**\n\n"
        keyboard = []

        for ch in all_ch:
            cid        = ch["channel_id"]
            expires_at = time.time() + cfg.LINK_EXPIRY_SECONDS
            tok_doc    = await get_token_by_channel(cid)

            if tok_doc:
                token = tok_doc["token"]
            else:
                token = secrets.token_urlsafe(12)

            await set_token(cid, token, expires_at)
            bot_link = f"https://t.me/{cfg.BOT_USERNAME}?start=req_{token}"
            text    += f"📢 **{ch['channel_name']}**\n`{bot_link}`\n\n"
            keyboard.append([
                InlineKeyboardButton(f"📢 {ch['channel_name']}", url=bot_link)
            ])

        await message.reply(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ── /approveon ───────────────────────────────────
    @app.on_message(filters.command("approveon") & filters.private)
    async def cmd_approveon(client: Client, message: Message):
        if not await is_admin(message.from_user.id):
            await message.reply("❌ Admins only!"); return
        if len(message.command) < 2:
            await message.reply("⚠️ Usage: `/approveon <channel_id>`"); return
        try:
            cid = int(message.command[1])
        except ValueError:
            await message.reply("❌ Invalid ID."); return

        ch = await get_channel(cid)
        if not ch:
            await message.reply("❌ Channel not found."); return

        await update_channel(cid, "approve_on", True)
        await update_channel(cid, "dm_on", True)
        await message.reply(
            f"✅ Auto-approve **enabled** for **{ch['channel_name']}**"
        )

    # ── /approveoff ──────────────────────────────────
    @app.on_message(filters.command("approveoff") & filters.private)
    async def cmd_approveoff(client: Client, message: Message):
        if not await is_admin(message.from_user.id):
            await message.reply("❌ Admins only!"); return
        if len(message.command) < 2:
            await message.reply("⚠️ Usage: `/approveoff <channel_id>`"); return
        try:
            cid = int(message.command[1])
        except ValueError:
            await message.reply("❌ Invalid ID."); return

        ch = await get_channel(cid)
        if not ch:
            await message.reply("❌ Channel not found."); return

        await update_channel(cid, "approve_on", False)
        await message.reply(
            f"🔴 Auto-approve **disabled** for **{ch['channel_name']}**"
        )

    # ── /unapprove ───────────────────────────────────
    @app.on_message(filters.command("unapprove") & filters.private)
    async def cmd_unapprove(client: Client, message: Message):
        """Disable auto-approve AND DM for one channel completely."""
        if not await is_admin(message.from_user.id):
            await message.reply("❌ Admins only!"); return
        if len(message.command) < 2:
            await message.reply(
                "⚠️ Usage: `/unapprove <channel_id>`\n\n"
                "Stops bot from auto-approving AND sending DMs for that channel."
            ); return
        try:
            cid = int(message.command[1])
        except ValueError:
            await message.reply("❌ Invalid ID."); return

        ch = await get_channel(cid)
        if not ch:
            await message.reply("❌ Channel not found."); return

        await update_channel(cid, "approve_on", False)
        await update_channel(cid, "dm_on", False)
        await message.reply(
            f"🚫 **{ch['channel_name']}** (`{cid}`)\n"
            f"Auto-approve & DM both **disabled**.\n\n"
            f"Use `/approveon {cid}` to re-enable."
              )
              
