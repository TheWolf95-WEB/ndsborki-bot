# handlers/show_all.py

import os
import json
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

# Путь до вашей папки проекта и файла сборок
ROOT = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(ROOT, "database", "builds.json")

# Эмодзи для категорий
CATEGORY_EMOJI = {
    "Топовая мета": "🔥",
    "Мета":       "📈",
    "Новинки":    "🆕"
}
# Фиксированная ширина колонки в символах
COL_WIDTH = 38

async def show_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Загрузка JSON
    try:
        with open(DB_PATH, encoding="utf-8") as f:
            builds = json.load(f)
    except FileNotFoundError:
        return await update.message.reply_text("❌ Файл сборок не найден.")
    except Exception as e:
        return await update.message.reply_text(f"❌ Ошибка при чтении сборок: {e}")

    if not builds:
        return await update.message.reply_text("ℹ️ В базе пока нет ни одной сборки.")

    # Формируем текстовые блоки по сборке
    blocks = []
    for b in builds:
        name = b.get("weapon_name", "—")
        cat  = b.get("category", "—")
        typ  = b.get("type", "—")
        cnt  = len(b.get("modules", {}))
        auth = b.get("author", "—")

        emoji_cat = CATEGORY_EMOJI.get(cat, "")
        # Собираем HTML-блок
        block = (
            f"<b>🔫 {name}</b>\n"
            f"{emoji_cat} <i>{cat}</i> | <i>{typ}</i> | 🔩 <b>{cnt}</b>\n"
            f"👤 {auth}"
        )
        blocks.append(block)

    # Разбиваем на пары (две колонки)
    pairs = [blocks[i:i+2] for i in range(0, len(blocks), 2)]

    # Для каждой пары строим выровненный <pre> блок
    for left_right in pairs:
        left = left_right[0].split("\n")
        right = left_right[1].split("\n") if len(left_right) == 2 else ["", "", ""]

        # Убедимся, что у обоих по три строки
        while len(left) < 3:  left.append("")
        while len(right) < 3: right.append("")

        # Составляем по строкам
        lines = []
        for i in range(3):
            l = left[i]
            r = right[i]
            # обрезаем/выравниваем левую колонку
            if len(l) > COL_WIDTH:
                l = l[:COL_WIDTH-3] + "..."
            l = l.ljust(COL_WIDTH)
            lines.append(f"{l}  {r}")

        text = "<pre>" + "\n".join(lines) + "</pre>"
        await update.message.reply_text(text, parse_mode="HTML")

show_all_handler = CommandHandler("show_all", show_all)
