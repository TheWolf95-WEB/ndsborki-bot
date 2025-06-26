# handlers/show_all.py

import os
import json
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

# Путь до файла сборок
ROOT    = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(ROOT, "database", "builds.json")

async def show_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1) Загрузка JSON
    try:
        with open(DB_PATH, encoding="utf-8") as f:
            builds = json.load(f)
    except FileNotFoundError:
        return await update.message.reply_text("❌ Файл сборок не найден.")
    except Exception as e:
        return await update.message.reply_text(f"❌ Ошибка при чтении builds.json: {e}")

    # 2) Проверяем, сколько записей
    count = len(builds)
    await update.message.reply_text(f"ℹ️ В базе найдено сборок: {count}")

    if count == 0:
        return

    # 3) Формируем и отправляем по 2 сборки в одном сообщении
    chunks = [builds[i:i+2] for i in range(0, count, 2)]
    for pair in chunks:
        lines = []
        for b in pair:
            name = b.get("weapon_name", "—")
            cat  = b.get("category",      "—")
            typ  = b.get("type",          "—")
            cnt  = len(b.get("modules", {}))
            auth = b.get("author",        "—")
            lines.append(
                f"🔫 <b>{name}</b>\n"
                f"📁 {cat} | 🛠 {typ} | 🔩 {cnt}\n"
                f"👤 {auth}"
            )
        # Объединяем 1 или 2 блока
        text = "\n\n".join(lines)
        await update.message.reply_text(text, parse_mode="HTML")

show_all_handler = CommandHandler("show_all", show_all)
