import os
import json
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

ROOT    = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(ROOT, "database", "builds.json")

CATEGORY_EMOJI = {"Топовая мета":"🔥","Мета":"📈","Новинки":"🆕"}
COL_WIDTH      = 38

async def show_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ОТЛАДКА: проверяем, что функция вообще вызывается
    await update.message.reply_text("🚧 Отладка: попали в show_all")

    try:
        with open(DB_PATH, encoding="utf-8") as f:
            builds = json.load(f)
    except Exception as e:
        return await update.message.reply_text(f"Ошибка чтения builds.json: {e}")

    if not builds:
        return await update.message.reply_text("ℹ️ В базе пока нет сборок.")

    blocks = []
    for b in builds:
        nm  = b.get("weapon_name","—")
        cat = b.get("category","—")
        typ = b.get("type","—")
        cnt = len(b.get("modules",{}))
        auth = b.get("author","—")
        emoji_cat = CATEGORY_EMOJI.get(cat,"")
        blocks.append(
            f"<b>🔫 {nm}</b>\n"
            f"{emoji_cat} <i>{cat}</i> | <i>{typ}</i> | 🔩 <b>{cnt}</b>\n"
            f"👤 {auth}"
        )

    pairs = [blocks[i:i+2] for i in range(0, len(blocks), 2)]
    for pair in pairs:
        left = pair[0].split("\n")
        right = pair[1].split("\n") if len(pair)>1 else [""]*3
        while len(left)<3:  left.append("")
        while len(right)<3: right.append("")
        lines=[]
        for i in range(3):
            l = left[i][:COL_WIDTH-3]+"..." if len(left[i])>COL_WIDTH else left[i]
            l = l.ljust(COL_WIDTH)
            lines.append(f"{l}  {right[i]}")
        text = "<pre>" + "\n".join(lines) + "</pre>"
        await update.message.reply_text(text, parse_mode="HTML")

show_all_handler = CommandHandler("show_all", show_all)
