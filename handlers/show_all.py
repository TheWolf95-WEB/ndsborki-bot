# handlers/show_all.py

import os
import json
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Путь к проекту и builds.json
ROOT     = os.path.dirname(os.path.dirname(__file__))
DB_PATH  = os.path.join(ROOT, "database", "builds.json")
PAGE_SIZE = 5

# Категории с эмодзи
CATEGORIES = [
    ("Мета",        "📈"),
    ("Новинки",     "🆕"),
    ("Топовая мета","🔥"),
]

async def show_all_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/show_all → инлайн-меню категорий."""
    # Загружаем сборки, чтобы подсчитать
    try:
        with open(DB_PATH, encoding="utf-8") as f:
            builds = json.load(f)
    except:
        builds = []

    # Считаем по категориям
    counts = {}
    for b in builds:
        counts[b.get("category","—")] = counts.get(b.get("category","—"), 0) + 1

    text = (
        "📦 <b>Все сборки по категориям</b>\n\n"
        "Нажмите на нужную категорию:"
    )

    # Строим инлайн-кнопки по одной в ряд
    buttons = [
        [InlineKeyboardButton(f"{emoji} {name} ({counts.get(name,0)})",
                              callback_data=f"CAT|{name}|1")]
        for name, emoji in CATEGORIES
    ]
    markup = InlineKeyboardMarkup(buttons)

    await update.message.reply_text(text, parse_mode="HTML", reply_markup=markup)
    context.user_data.pop("showall_state", None)


async def category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора категории из инлайн-меню."""
    query = update.callback_query
    await query.answer()

    # data = "CAT|<category>|<page>"
    _, category, page_str = query.data.split("|")
    page = int(page_str)

    context.user_data["showall_state"] = {"category": category, "page": page}
    await _send_page(update, context)


async def navigation_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """← Назад / Вперёд → / 🏠 Категории обычной клавиатурой."""
    text = update.message.text
    state = context.user_data.get("showall_state")

    # если «🏠 Категории» или state отсутствует → заново /show_all
    if text == "🏠 Категории" or not state:
        return await show_all_command(update, context)

    category = state["category"]
    page     = state["page"]

    if text == "← Назад":
        page = max(1, page - 1)
    elif text == "Вперёд →":
        page += 1
    else:
        return  # не наша кнопка

    context.user_data["showall_state"]["page"] = page

    # эмулируем callback_query
    fake = update
    fake.callback_query = update.message
    fake.callback_query.data = f"CAT|{category}|{page}"
    await category_callback(fake, context)


async def _send_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выводит текст и обычную навигацию."""
    state = context.user_data["showall_state"]
    category = state["category"]
    page     = state["page"]

    # читаем сборки
    try:
        with open(DB_PATH, encoding="utf-8") as f:
            all_builds = json.load(f)
    except:
        return await update.callback_query.edit_message_text("❌ Не удалось загрузить базы.")

    builds = [b for b in all_builds if b.get("category") == category]
    total = len(builds)
    pages = (total + PAGE_SIZE - 1) // PAGE_SIZE

    # корректируем page
    page = max(1, min(page, pages))
    start = (page - 1) * PAGE_SIZE
    chunk = builds[start:start + PAGE_SIZE]

    # текст
    header = (
        f"📂 <b>Сборки «{category}»</b>\n"
        f"Стр. {page}/{pages} — всего {total}\n\n"
    )
    lines = [header]
    for idx, b in enumerate(chunk, start + 1):
        lines.append(
            f"<b>{idx}. {b.get('weapon_name','—')}</b>\n"
            f"├ 📏 Дистанция: {b.get('role','-')}\n"
            f"├ ⚙️ Тип: {b.get('type','—')}\n"
            f"├ 🔩 Модулей: {len(b.get('modules',{}))}\n"
            f"└ 👤 Автор: {b.get('author','—')}\n"
        )

    text = "\n".join(lines).strip()

    # строим обычную клавиатуру навигации
    nav = []
    if page > 1:       nav.append("← Назад")
    if page < pages:   nav.append("Вперёд →")
    nav.append("🏠 Категории")

    reply_kb = ReplyKeyboardMarkup([nav], resize_keyboard=True, one_time_keyboard=True)

    # обновляем сообщение (callback) или шлём новое (команда)
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_kb)
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_kb)


# Экспортируем
show_all_handler   = CommandHandler("show_all", show_all_command)
category_cb        = CallbackQueryHandler(category_callback, pattern=r"^CAT\|")
navigation_handler = MessageHandler(
    filters.Regex(r"^(← Назад|Вперёд →|🏠 Категории)$"),
    navigation_handler
)
