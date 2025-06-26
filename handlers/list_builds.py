import json
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from utils.permissions import admin_only  # или без проверки, если любой юзер может
from utils.keyboards import get_main_menu

DB_PATH = "database/builds.json"

@admin_only
async def list_builds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Загружаем весь массив сборок
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            builds = json.load(f)
    except FileNotFoundError:
        await update.message.reply_text("❌ Файл сборок не найден.")
        return
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при чтении БД: {e}")
        return

    if not builds:
        await update.message.reply_text("ℹ️ В базе пока нет ни одной сборки.")
        return

    # Формируем текст
    lines = ["📦 <b>Все сохранённые сборки:</b>\n"]
    for b in builds:
        # Краткий вывод: Название (Категория / Тип)
        lines.append(
            f"• <b>{b['weapon_name']}</b> — {b.get('category','?')} / {b.get('type','?')}"
        )

    # Если слишком длинно, можно разбить на несколько сообщений
    text = "\n".join(lines)
    if len(text) > 4000:
        # разобьём пополам
        mid = len(lines)//2
        await update.message.reply_text("\n".join(lines[:mid]), parse_mode="HTML")
        await update.message.reply_text("\n".join(lines[mid:]), parse_mode="HTML")
    else:
        await update.message.reply_text(text, parse_mode="HTML")

# Регистрация хэндлера
list_builds_handler = CommandHandler("list_builds", list_builds)
