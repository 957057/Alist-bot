# -*- coding: UTF-8 -*-
import json
import os
import random
import urllib.parse

from pyrogram import filters, Client
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    CallbackQuery,
)

from api.alist.alist_api import alist
from config.config import chat_data, roll_cfg, bot_cfg
from module.roll.random_kaomoji import random_kaomoji
from tools.filters import is_admin
from tools.utils import pybyte

return_button = [
    InlineKeyboardButton("↩️返回菜单", callback_data="sr_return"),
    InlineKeyboardButton("❌关闭菜单", callback_data="sr_close"),
]


def btn():
    return [
        [
            InlineKeyboardButton("🛠修改配置", callback_data="edit_roll"),
            InlineKeyboardButton(
                "✅随机推荐" if roll_cfg.roll_disable else "❎随机推荐",
                callback_data="roll_off" if roll_cfg.roll_disable else "roll_on",
            ),
        ],
        [InlineKeyboardButton("❌关闭菜单", callback_data="sr_close")],
    ]


# 随机推荐菜单
@Client.on_message(filters.command("sr") & filters.private & is_admin)
async def sr_menu(_, message: Message):
    chat_data["sr_menu"] = await message.reply(
        text=random_kaomoji(), reply_markup=InlineKeyboardMarkup(btn())
    )


# 随机推荐
@Client.on_message(filters.command("roll"))
async def roll(_, message: Message):
    if bot_cfg.member and message.chat.id not in bot_cfg.member:
        return
    if not roll_cfg.roll_disable:
        return
    roll_str = " ".join(message.command[1:])
    if roll_str.replace("？", "?") == "?":
        t = "\n".join(list(roll_cfg.path.keys()))
        text = f"已添加的关键词：\n<code>{t}</code>"
        return await message.reply(text)
    if roll_cfg.path:
        names, sizes, url = await generate(key=roll_str or "")
        text = f"""
{random_kaomoji()}：<a href="{url}">{names}</a>
{f'{random_kaomoji()}：{sizes}' if sizes != '0.0b' else ''}
"""
        await message.reply(text, disable_web_page_preview=True)
    else:
        await message.reply("请先添加路径")


# 菜单按钮回调
@Client.on_callback_query(filters.regex("^sr_"))
async def menu(_, query: CallbackQuery):
    data = query.data
    if data == "sr_return":
        chat_data["edit_roll"] = False
        await chat_data["sr_menu"].edit(
            text=random_kaomoji(), reply_markup=InlineKeyboardMarkup(btn())
        )
    elif data == "sr_close":
        chat_data["edit_roll"] = False
        await chat_data["sr_menu"].edit(text=random_kaomoji())


# 修改配置按钮回调
@Client.on_callback_query(filters.regex("edit_roll"))
async def edit_roll(_, query: CallbackQuery):
    j = json.dumps(roll_cfg.path, indent=4, ensure_ascii=False)
    text = (
        f"""
```json
{j}
```


修改后发送，格式为json
一个关键词可以包含多个路径，使用列表格式
"""
        if j != "null"
        else """
```json
{
    "关键词": "路径",
    "slg": "/slg",
    "gal": [
        "/gal",
        "/123"
    ]
}
```

修改后发送，格式为json
一个关键词可以包含多个路径，使用列表格式
"""
    )
    await query.message.edit(
        text=text, reply_markup=InlineKeyboardMarkup([return_button])
    )
    chat_data["edit_roll"] = True


# 开关回调
@Client.on_callback_query(filters.regex("^roll_"))
async def roll_of(_, message):
    query = message.data
    roll_cfg.roll_disable = query != "roll_off"
    await chat_data["sr_menu"].edit(
        text=random_kaomoji(), reply_markup=InlineKeyboardMarkup(btn())
    )


def _edit_roll_filter(_, __, ___):
    return bool("edit_roll" in chat_data and chat_data["edit_roll"])


edit_roll_filter = filters.create(_edit_roll_filter)


# 写入配置
@Client.on_message(filters.text & filters.private & edit_roll_filter & is_admin)
async def change_setting(_, message: Message):
    msg = message.text
    try:
        path = json.loads(msg)
    except Exception as e:
        await message.reply(text=f"错误：{str(e)}\n\n请修改后重新发送")
    else:
        await message.delete()
        chat_data["edit_roll"] = False
        roll_cfg.path = path
        await chat_data["sr_menu"].edit(
            text="修改成功", reply_markup=InlineKeyboardMarkup(btn())
        )


async def generate(key=""):
    # 使用os.urandom生成随机字节串作为种子
    random.seed(os.urandom(32))

    values_list = list(roll_cfg.path.values()) if key == "" else roll_cfg.path[key]
    r_path = get_random_value(values_list)
    data = await alist.fs_list(r_path)
    content = data.data["content"]

    selected_item = random.choice(content)
    name = selected_item["name"]
    size = selected_item["size"]
    get_path = f"{r_path}/{name}"

    url = bot_cfg.alist_web + get_path
    url = urllib.parse.quote(url, safe=":/")
    return name, pybyte(size), url


# 递归列表，返回随机值
def get_random_value(data):
    if not isinstance(data, list):
        return data
    random_value = random.choice(data)
    return (
        get_random_value(random_value)
        if isinstance(random_value, list)
        else random_value
    )
