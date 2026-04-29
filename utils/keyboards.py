"""
utils/keyboards.py
==================
Saare InlineKeyboard yahan defined hain.
"""

from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def start_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("• ABOUT",    callback_data="about"),
            InlineKeyboardButton("• CHANNELS", callback_data="channels_menu"),
        ],
        [InlineKeyboardButton("• Close •", callback_data="close")],
    ])


def about_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("• BACK",  callback_data="back_start"),
            InlineKeyboardButton("CLOSE •", callback_data="close"),
        ],
    ])


def channels_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("• BACK", callback_data="back_start"),
            InlineKeyboardButton("home•",  callback_data="back_start"),
        ],
    ])


def request_join_kb(invite_link: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("• REQUEST TO JOIN •", url=invite_link)],
    ])


def approval_dm_kb(channel_name: str, ch_join_link: str,
                    updates_link: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("• JOIN MY UPDATES •",         url=updates_link)],
        [InlineKeyboardButton(f"• Join {channel_name} •",   url=ch_join_link)],
    ])
      
