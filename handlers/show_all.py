import os
import json
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from utils.keyboards import get_main_menu

# Путь до файла с базой сборок
ROOT = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(ROOT, "database", "builds.json")


async def show_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Попытка загрузить JSON
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

    # Собираем строки вида: • Название — Категория / Тип
    lines = ["📦 <b>Все сохранённые сборки:</b>\n"]
    for b in builds:
        name = b.get("weapon_name", "—")
        cat  = b.get("category", "—")
        typ  = b.get("type", "—")
        lines.append(f"• <b>{name}</b> — {cat} / {typ}")

    # Объединяем в один текст
    text = "\n".join(lines)
    # Если длина не превышает лимит, отправляем сразу
    if len(text) <= 4000:
        await update.message.reply_text(text, parse_mode="HTML")
        return

    # Иначе разбиваем на чанки по ~4000 символов
    chunk = []
    size = 0
    for line in lines:
        if size + len(line) + 1 > 4000:
            await update.message.reply_text("\n".join(chunk), parse_mode="HTML")
            chunk = []
            size = 0
        chunk.append(line)
        size += len(line) + 1
    if chunk:
        await update.message.reply_text("\n".join(chunk), parse_mode="HTML")


show_all_handler = CommandHandler("show_all", show_all)
