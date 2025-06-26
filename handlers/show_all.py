# handlers/show_all.py

import os
import json
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

# Путь до корня проекта и файла сборок
ROOT    = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(ROOT, "database", "builds.json")

async def show_all_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1) Проверяем наличие файла и читаем
    if not os.path.exists(DB_PATH):
        return await update.message.reply_text("ℹ️ Список сборок пуст.")

    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return await update.message.reply_text(f"❌ Не удалось прочитать builds.json: {e}")

    if not data:
        return await update.message.reply_text("ℹ️ Список сборок пуст.")

    # 2) Формируем строки
    lines = ["📄 <b>Все сборки:</b>"]
    for idx, b in enumerate(data, start=1):
        name = b.get("weapon_name", "—")
        role = b.get("role", "-")
        typ  = b.get("type", "—")
        cnt  = len(b.get("modules", {}))
        auth = b.get("author", "—")

        lines.append(
            f"\n<b>{idx}. {name}</b>\n"
            f"├ 📏 Дистанция: {role}\n"
            f"├ ⚙️ Тип: {typ}\n"
            f"├ 🔩 Модулей: {cnt}\n"
            f"└ 👤 Автор: {auth}"
        )

    # 3) Склеиваем и отправляем
    text = "\n".join(lines)
    await update.message.reply_text(text, parse_mode="HTML")

show_all_handler = CommandHandler("show_all", show_all_command)
