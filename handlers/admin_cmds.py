"""
handlers/admin_cmds.py
======================
/addadmin /deladmin /viewadminlist
/reqmode /reqtime /approveall
/status /stats /broadcast /cleanup /setpic /help
"""

import asyncio
import logging

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait

import config.settings as cfg
from utils.database import (
    is_owner, is_admin, add_admin, remove_admin, get_all_admins,
    get_config, set_config, inc_stat,
    get_all_channels, get_channel, update_channel,
    get_pending_by_channel, remove_pending,
    get_all_users, count_users, remove_user
)

logger = logging.getLogger(__name__)


def register_admin_cmds(app: Client):

    # ── /addadmin ────────────────────────────────────
    @app.on_message(filters.command("addadmin") & filters.private)
    async def cmd_addadmin(client: Client, message: Message):
        if not await is_owner(message.from_user.id):
            await message.reply("❌ Owner only!"); return
        if len(message.command) < 2:
            await message.reply("⚠️ Usage: `/addadmin <user_id>`"); return
        try:
            uid = int(message.command[1])
        except ValueError:
            await message.reply("❌ Invalid ID."); return

        added = await add_admin(uid)
        if not added:
            await message.reply("ℹ️ Already an admin."); return
        await message.reply(f"✅ `{uid}` added as admin.")

    # ── /deladmin ────────────────────────────────────
    @app.on_message(filters.command("deladmin") & filters.private)
    async def cmd_deladmin(client: Client, message: Message):
        if not await is_owner(message.from_user.id):
            await message.reply("❌ Owner only!"); return
        if len(message.command) < 2:
            await message.reply("⚠️ Usage: `/deladmin <user_id>`"); return
        try:
            uid = int(message.command[1])
        except ValueError:
            await message.reply("❌ Invalid ID."); return

        removed = await remove_admin(uid)
        if not removed:
            await message.reply("ℹ️ Not an admin."); return
        await message.reply(f"✅ `{uid}` removed from admins.")

    # ── /viewadminlist ───────────────────────────────
    @app.on_message(filters.command("viewadminlist") & filters.private)
    async def cmd_viewadminlist(client: Client, message: Message):
        if not await is_admin(message.from_user.id):
            await message.reply("❌ Admins only!"); return

        cfg_doc = await get_config()
        owner   = cfg_doc.get("owner_id", "Not set")
        admins  = await get_all_admins()

        text  = f"👑 **Owner:** `{owner}`\n\n🛡 **Admins:**\n"
        text += "\n".join(
            f"  {i+1}. `{a}`" for i, a in enumerate(admins)
        ) if admins else "  None"
        await message.reply(text)

    # ── /reqmode ─────────────────────────────────────
    @app.on_message(filters.command("reqmode") & filters.private)
    async def cmd_reqmode(client: Client, message: Message):
        if not await is_owner(message.from_user.id):
            await message.reply("❌ Owner only!"); return

        cfg_doc    = await get_config()
        new_mode   = not cfg_doc.get("req_mode", True)
        await set_config("req_mode", new_mode)
        status = "🟢 **ON**" if new_mode else "🔴 **OFF**"
        await message.reply(f"⚡ Global Auto-Approve Mode: {status}")

    # ── /reqtime ─────────────────────────────────────
    @app.on_message(filters.command("reqtime") & filters.private)
    async def cmd_reqtime(client: Client, message: Message):
        if not await is_owner(message.from_user.id):
            await message.reply("❌ Owner only!"); return

        cfg_doc = await get_config()
        if len(message.command) < 2:
            await message.reply(
                f"⏱ Current delay: `{cfg_doc.get('req_delay', 4)}s`\n\n"
                "Usage: `/reqtime <seconds>`"
            ); return
        try:
            secs = int(message.command[1])
            if not 0 <= secs <= 60:
                raise ValueError
        except ValueError:
            await message.reply("❌ Enter a number between 0 and 60."); return

        await set_config("req_delay", secs)
        await message.reply(f"✅ Approve delay set to `{secs}s`.")

    # ── /approveall ──────────────────────────────────
    @app.on_message(filters.command("approveall") & filters.private)
    async def cmd_approveall(client: Client, message: Message):
        if not await is_owner(message.from_user.id):
            await message.reply("❌ Owner only!"); return

        from handlers.join_request import send_approval_dm

        msg    = await message.reply("⏳ Processing all pending requests...")
        total  = 0
        failed = 0

        all_ch = await get_all_channels()
        for ch in all_ch:
            cid     = ch["channel_id"]
            ch_name = ch["channel_name"]

            if not ch.get("approve_on", True):
                continue

            pending_list = await get_pending_by_channel(cid)
            if not pending_list:
                continue

            for p in pending_list:
                try:
                    await client.approve_chat_join_request(cid, p["user_id"])
                    await inc_stat("total_approved")
                    await remove_pending(cid, p["user_id"])
                    total += 1

                    if ch.get("dm_on", True):
                        class FakeUser:
                            def __init__(self, uid, fname, uname):
                                self.id         = uid
                                self.first_name = fname
                                self.username   = uname

                        await send_approval_dm(
                            client,
                            FakeUser(p["user_id"], p["first_name"], p["username"]),
                            cid, ch_name, ch
                        )
                    await asyncio.sleep(0.3)

                except FloodWait as e:
                    await asyncio.sleep(e.value)
                except Exception as e:
                    logger.warning(f"Approve failed {p['user_id']}: {e}")
                    failed += 1

        await msg.edit(
            f"✅ **Approve All Done!**\n\n"
            f"✔️ Approved: `{total}`\n"
            f"❌ Failed: `{failed}`"
        )

    # ── /status ──────────────────────────────────────
    @app.on_message(filters.command("status") & filters.private)
    async def cmd_status(client: Client, message: Message):
        if not await is_admin(message.from_user.id):
            await message.reply("❌ Admins only!"); return

        cfg_doc  = await get_config()
        all_ch   = await get_all_channels()
        mode     = "🟢 ON" if cfg_doc.get("req_mode", True) else "🔴 OFF"
        pending  = 0
        for ch in all_ch:
            pending += await __import__("utils.database", fromlist=["count_pending"]).count_pending(ch["channel_id"])
        total_users = await count_users()

        await message.reply(
            f"📊 **Bot Status**\n\n"
            f"⚡ Auto-Approve: {mode}\n"
            f"⏱ Delay: `{cfg_doc.get('req_delay', 4)}s`\n"
            f"📢 Channels: `{len(all_ch)}`\n"
            f"⏳ Pending: `{pending}`\n"
            f"🛡 Admins: `{len(await get_all_admins())}`\n"
            f"👥 Users: `{total_users}`"
        )

    # ── /stats ───────────────────────────────────────
    @app.on_message(filters.command("stats") & filters.private)
    async def cmd_stats(client: Client, message: Message):
        if not await is_owner(message.from_user.id):
            await message.reply("❌ Owner only!"); return

        cfg_doc     = await get_config()
        s           = cfg_doc.get("stats", {})
        all_ch      = await get_all_channels()
        total_users = await count_users()
        admins      = await get_all_admins()

        await message.reply(
            f"📈 **Full Statistics**\n\n"
            f"✅ Total Approved: `{s.get('total_approved', 0)}`\n"
            f"📨 Total Requests: `{s.get('total_requests', 0)}`\n"
            f"👥 Total Users: `{total_users}`\n"
            f"📢 Channels: `{len(all_ch)}`\n"
            f"🛡 Admins: `{len(admins)}`\n"
            f"⏱ Delay: `{cfg_doc.get('req_delay', 4)}s`\n"
            f"⚡ Mode: `{'ON' if cfg_doc.get('req_mode', True) else 'OFF'}`"
        )

    # ── /broadcast ───────────────────────────────────
    @app.on_message(filters.command("broadcast") & filters.private)
    async def cmd_broadcast(client: Client, message: Message):
        if not await is_owner(message.from_user.id):
            await message.reply("❌ Owner only!"); return

        bc_msg = message.reply_to_message
        if not bc_msg and len(message.command) < 2:
            await message.reply(
                "⚠️ Reply to a message with `/broadcast`\n"
                "OR use `/broadcast <text>`"
            ); return

        users      = await get_all_users()
        sent       = 0
        failed     = 0
        status_msg = await message.reply(
            f"📡 Broadcasting to `{len(users)}` users..."
        )

        for uid in users:
            try:
                if bc_msg:
                    await bc_msg.forward(uid)
                else:
                    text = " ".join(message.command[1:])
                    await client.send_message(uid, text)
                sent += 1
                await asyncio.sleep(0.05)
            except Exception:
                failed += 1

        await status_msg.edit(
            f"📡 **Broadcast Done!**\n\n"
            f"✅ Sent: `{sent}`\n"
            f"❌ Failed: `{failed}`"
        )

    # ── /cleanup ─────────────────────────────────────
    @app.on_message(filters.command("cleanup") & filters.private)
    async def cmd_cleanup(client: Client, message: Message):
        if not await is_owner(message.from_user.id):
            await message.reply("❌ Owner only!"); return

        msg    = await message.reply("🧹 Cleaning inactive users...")
        users  = await get_all_users()
        before = len(users)
        active = []

        for uid in users:
            try:
                await client.send_chat_action(uid, "typing")
                active.append(uid)
                await asyncio.sleep(0.05)
            except Exception:
                await remove_user(uid)

        removed = before - len(active)
        await msg.edit(
            f"🧹 **Cleanup Done!**\n\n"
            f"Before: `{before}`\n"
            f"Active: `{len(active)}`\n"
            f"Removed: `{removed}`"
        )

    # ── /setpic ──────────────────────────────────────
    @app.on_message(filters.command("setpic") & filters.private)
    async def cmd_setpic(client: Client, message: Message):
        if not await is_owner(message.from_user.id):
            await message.reply("❌ Owner only!"); return

        cfg_doc = await get_config()
        if len(message.command) < 2:
            await message.reply(
                f"⚠️ `/setpic <image_url>`\n\n"
                f"Current: `{cfg_doc.get('start_pic', cfg.PIC_START)}`"
            ); return

        new_pic = message.command[1]
        await set_config("start_pic", new_pic)
        await message.reply_photo(
            photo=new_pic,
            caption="✅ **Start picture updated!**"
        )

    # ── /help ────────────────────────────────────────
    @app.on_message(filters.command("help") & filters.private)
    async def cmd_help(client: Client, message: Message):
        await message.reply(
            "📖 **All Commands:**\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "🛡 **Admin Commands:**\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "`/status` — Bot status\n"
            "`/addch <id>` — Add channel\n"
            "`/delch <id>` — Remove channel\n"
            "`/channels` — List all channels\n"
            "`/reqlink [id]` — Generate expiring link\n"
            "`/links` — Show invite links\n"
            "`/bulklink` — All channel links at once\n"
            "`/approveon <id>` — Enable auto-approve\n"
            "`/approveoff <id>` — Disable auto-approve\n"
            "`/unapprove <id>` — Disable approve + DM\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "👑 **Owner Commands:**\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "`/stats` — Full statistics\n"
            "`/broadcast` — Broadcast to all users\n"
            "`/cleanup` — Remove inactive users\n"
            "`/reqtime <sec>` — Set approve delay\n"
            "`/reqmode` — Toggle global auto-approve\n"
            "`/approveall` — Approve all pending\n"
            "`/addadmin <id>` — Add admin\n"
            "`/deladmin <id>` — Remove admin\n"
            "`/viewadminlist` — View all admins\n"
            "`/setpic <url>` — Set start picture\n\n"
            "👤 Dev: @TAlone\\_boy"
      )
      
