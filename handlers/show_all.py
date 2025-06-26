# handlers/show_all.py

import os
import json
import textwrap
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

# Путь до базы
ROOT = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(ROOT, "database", "builds.json")

COLUMN_WIDTH = 40  # Ширина колонки в символах

async def show_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Загружаем данные
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            builds = json.load(f)
    except FileNotFoundError:
        await update.message.reply_text("❌ Файл сборок не найден.")
        return
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при чтении файла сборок: {e}")
        return

    if not builds:
        await update.message.reply_text("ℹ️ В базе пока нет ни одной сборки.")
        return

    # Форматируем каждую сборку в блок текста
    entries = []
    for b in builds:
        name = b.get("weapon_name", "—")
        cat  = b.get("category", "—")
        typ  = b.get("type", "—")
        mod_count = len(b.get("modules", {}))
        auth = b.get("author", "—")

        block = (
            f"<b>{name}</b>\n"
            f"{cat} | {typ} ({mod_count})\n"
            f"Автор: {auth}"
        )
        # Заменяем потенциальные теги на безопасные
        entries.append(block)

    # Разбиваем на пары по 2
    pairs = [entries[i:i+2] for i in range(0, len(entries), 2)]

    # Собираем финальные строки с выравниванием
    messages = []
    for pair in pairs:
        left = pair[0].split("\n")
        right = pair[1].split("\n") if len(pair) == 2 else ["", "", ""]

        # Для каждой из трёх строк в блоке формируем строку с двумя колонками
        combined = []
        for i in range(3):
            l = left[i] if i < len(left) else ""
            r = right[i] if i < len(right) else ""
            # выравниваем по COLUMN_WIDTH
            l_pad = l.ljust(COLUMN_WIDTH)
            combined.append(f"{l_pad} {r}")

        messages.append("<pre>" + "\n".join(combined) + "</pre>")

    # Если слишком много, отправляем сообщениями
    for msg in messages:
        await update.message.reply_text(msg, parse_mode="HTML")


show_all_handler = CommandHandler("show_all", show_all)
