"""
handlers/start.py
"""

import secrets
import time

from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InputMediaPhoto

import config.settings as cfg
from utils.database import (
    add_user, get_config, get_channel, get_channel_by_token,
    set_token, get_token_by_channel, clean_expired_tokens,
)
from utils.keyboards import start_kb, about_kb, channels_kb, request_join_kb


def register_start(app: Client):

    @app.on_message(filters.command("start"))
    async def cmd_start(client: Client, message: Message):
        user = message.from_user
        await add_user(user.id)

        args = message.command

        if len(args) > 1 and args[1].startswith("req_"):
            token = args[1][4:]
            await clean_expired_tokens()

            tok_doc = await get_channel_by_token(token)

            if not tok_doc:
                await message.reply(
                    "**Note:** If the link is expired, "
                    "please click the post link again to get a new one."
                )
                return

            channel_id   = tok_doc["channel_id"]
            channel_info = await get_channel(channel_id)
            if not channel_info:
                await message.reply("❌ Channel not found.")
                return

            invite_link = channel_info.get("invite_link", "")

            await message.reply("**HERE IS YOUR LINK! CLICK BELOW TO PROCEED**")
            await message.reply(
                "\u200b",
                reply_markup=request_join_kb(invite_link)
            )
            await message.reply(
                "Note: If the link is expired, "
                "please click the post link again to get a new one."
            )
            return

        cfg_doc = await get_config()
        pic     = cfg_doc.get("start_pic", cfg.PIC_START)

        caption = (
            "**WELCOME TO THE ADVANCED LINKS SHARING BOT.\n"
            "WITH THIS BOT, YOU CAN SHARE LINKS AND KEEP\n"
            "YOUR CHANNELS SAFE FROM COPYRIGHT ISSUES.**\n\n"
            f"▶ **MAINTAINED BY :** [**@TAlone\\_boy**]({cfg.MY_CHANNEL})"
        )
        await message.reply_photo(
            photo=pic,
            caption=caption,
            reply_markup=start_kb()
        )

    @app.on_callback_query()
    async def handle_callbacks(client: Client, query: CallbackQuery):
        data = query.data
        await query.answer()

        cfg_doc = await get_config()
        pic     = cfg_doc.get("start_pic", cfg.PIC_START)

        if data == "close":
            try:
                await query.message.delete()
            except Exception:
                pass

        elif data == "about":
            caption = (
                f"**›› ᴄᴏᴍᴍᴜɴɪᴛʏ:** [ᴄʟɪᴄᴋ ʜᴇʀᴇ]({cfg.MY_CHANNEL})\n\n"
                f"**›› ᴜᴘᴅᴀᴛᴇs ᴄʜᴀɴɴᴇʟ:** [Cʟɪᴄᴋ ʜᴇʀᴇ]({cfg.MY_CHANNEL})\n"
                f"**›› ᴏᴡɴᴇʀ:** @TAlone\\_boy\n"
                f"**›› ʟᴀɴɢᴜᴀɢᴇ:** [Pʏᴛʜᴏɴ 3]({cfg.PYTHON_DOCS})\n"
                f"**›› ʟɪʙʀᴀʀʏ:** [Pʏʀᴏɢʀᴀᴍ ᴠ2]({cfg.PYROGRAM_DOCS})\n"
                f"**›› ᴅᴀᴛᴀʙᴀsᴇ:** [Mᴏɴɢᴏ ᴅʙ]({cfg.MONGODB_DOCS})\n"
                f"**›› ᴅᴇᴠᴇʟᴏᴘᴇʀ:** @TAlone\\_boy"
            )
            try:
                await query.message.edit_media(
                    InputMediaPhoto(media=cfg.PIC_ABOUT, caption=caption),
                    reply_markup=about_kb()
                )
            except Exception:
                await query.message.reply_photo(
                    photo=cfg.PIC_ABOUT,
                    caption=caption,
                    reply_markup=about_kb()
                )

        elif data == "channels_menu":
            caption = (
                f"**›› ᴄʜᴀɴɴᴇʟ:** [ᴊᴏɪɴ ᴜᴘᴅᴀᴛᴇs]({cfg.MY_CHANNEL})\n\n"
                f"**›› ᴄᴏᴍᴍᴜɴɪᴛʏ:** [TP Bots]({cfg.MY_CHANNEL})\n"
                f"**›› ᴅᴇᴠᴇʟᴏᴘᴇʀ:** @TAlone\\_boy"
            )
            try:
                await query.message.edit_media(
                    InputMediaPhoto(media=cfg.PIC_CHANNELS, caption=caption),
                    reply_markup=channels_kb()
                )
            except Exception:
                await query.message.reply_photo(
                    photo=cfg.PIC_CHANNELS,
                    caption=caption,
                    reply_markup=channels_kb()
                )

        elif data == "back_start":
            caption = (
                "**WELCOME TO THE ADVANCED LINKS SHARING BOT.\n"
                "WITH THIS BOT, YOU CAN SHARE LINKS AND KEEP\n"
                "YOUR CHANNELS SAFE FROM COPYRIGHT ISSUES.**\n\n"
                f"▶ **MAINTAINED BY :** [**@TAlone\\_boy**]({cfg.MY_CHANNEL})"
            )
            try:
                await query.message.edit_media(
                    InputMediaPhoto(media=pic, caption=caption),
                    reply_markup=start_kb()
                )
            except Exception:
                await query.message.reply_photo(
                    photo=pic,
                    caption=caption,
                    reply_markup=start_kb()
                )
