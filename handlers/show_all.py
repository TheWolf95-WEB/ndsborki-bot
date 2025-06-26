# handlers/show_all.py

import os
import json
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

ROOT     = os.path.dirname(os.path.dirname(__file__))
DB_PATH  = os.path.join(ROOT, "database", "builds.json")
PAGE_SIZE = 5

# Названия категорий и эмодзи (должны совпадать с полем "category" в JSON)
CATEGORY_EMOJI = {
    "Мета": "📈",
    "Новинки": "🆕",
    "Топовая мета": "🔥",
}

async def show_all_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Шаг 1: вывод списка категорий."""
    # читаем все сборки
    try:
        with open(DB_PATH, encoding="utf-8") as f:
            builds = json.load(f)
    except:
        return await update.message.reply_text("ℹ️ База сборок пуста или файл не найден.")

    # считаем по категориям
    counts = {}
    for b in builds:
        cat = b.get("category", "—")
        counts[cat] = counts.get(cat, 0) + 1

    # соберём кнопки: Категория (кол-во)
    buttons = []
    for cat, emoji in CATEGORY_EMOJI.items():
        cnt = counts.get(cat, 0)
        buttons.append(
            InlineKeyboardButton(
                f"{emoji} {cat} ({cnt})",
                callback_data=f"showcat|{cat}|1"
            )
        )
    markup = InlineKeyboardMarkup([buttons])
    await update.message.reply_text(
        "📦 <b>Все сборки по категориям:</b>",
        parse_mode="HTML",
        reply_markup=markup
    )

async def show_category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Шаг 2 и 3: показываем страницу сборок выбранной категории."""
    query = update.callback_query
    await query.answer()

    # разобрать callback_data = "showcat|<category>|<page>"
    _, category, page_str = query.data.split("|")
    page = int(page_str)

    # читаем сборки
    with open(DB_PATH, encoding="utf-8") as f:
        builds = [b for b in json.load(f) if b.get("category") == category]

    total = len(builds)
    pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    start = (page-1) * PAGE_SIZE
    end   = start + PAGE_SIZE
    chunk = builds[start:end]

    # собираем текст
    lines = [f"📂 <b>Сборки категории «{category}» ({total}):</b>"]
    for idx, b in enumerate(chunk, start=start+1):
        # найдём красивый лейбл типа
        typ_key = b.get("type", "")
        # предположим, есть утилита load_weapon_types()
        from utils.db import load_weapon_types
        types = {wt["key"]: wt["label"] for wt in load_weapon_types()}
        typ_label = types.get(typ_key, typ_key)

        lines.append(
            f"\n<b>{idx}. {b.get('weapon_name','—')}</b>\n"
            f"├ 📏 Дистанция: {b.get('role','-')}\n"
            f"├ ⚙️ Тип: {typ_label}\n"
            f"├ 🔩 Модулей: {len(b.get('modules', {}))}\n"
            f"└ 👤 Автор: {b.get('author','-')}"
        )

    text = "\n".join(lines)

    # кнопки пагинации и «назад»
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("← Назад", callback_data=f"showcat|{category}|{page-1}"))
    if page < pages:
        nav.append(InlineKeyboardButton("Вперёд →", callback_data=f"showcat|{category}|{page+1}"))
    # внизу всегда кнопка «назад к категориям»
    nav.append(InlineKeyboardButton("🔙 К категориям", callback_data="showcat|_back|0"))

    markup = InlineKeyboardMarkup([nav])

    # редактируем сообщение
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=markup)

async def back_to_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатываем кнопку «к категориям»."""
    query = update.callback_query
    if not query:  # вызвано из меню команд
        return await show_all_command(update, context)
    await query.answer()
    await show_all_command(query, context)

# Регистрация хэндлеров
show_all_handler      = CommandHandler("show_all", show_all_command)
showcat_callback      = CallbackQueryHandler(show_category_callback, pattern=r"^showcat\|[^|]+\|\d+$")
backcat_callback      = CallbackQueryHandler(back_to_categories, pattern=r"^showcat\|\_back\|0$")
