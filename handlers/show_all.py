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

# Путь к корню проекта и builds.json
ROOT     = os.path.dirname(os.path.dirname(__file__))
DB_PATH  = os.path.join(ROOT, "database", "builds.json")
PAGE_SIZE = 5

# Эмодзи для категорий (ключи должны совпадать с полем "category")
CATEGORY_EMOJI = {
    "Мета": "📈",
    "Новинки": "🆕",
    "Топовая мета": "🔥",
}

async def show_all_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Шаг 1: /show_all — инлайн-меню категорий."""
    try:
        with open(DB_PATH, encoding="utf-8") as f:
            builds = json.load(f)
    except:
        return await update.message.reply_text("ℹ️ База сборок пуста или файл не найден.")

    # Подсчёт сборок по категориям
    counts = {}
    for b in builds:
        cat = b.get("category", "—")
        counts[cat] = counts.get(cat, 0) + 1

    # Кнопки категории (инлайн)
    buttons = []
    for cat, emoji in CATEGORY_EMOJI.items():
        cnt = counts.get(cat, 0)
        buttons.append(
            InlineKeyboardButton(
                f"{emoji} {cat} ({cnt})",
                callback_data=f"CAT|{cat}|1"
            )
        )

    await update.message.reply_text(
        "📦 <b>Все сборки по категориям:</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([buttons])
    )

async def category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Шаг 2: показываем страницу сборок выбранной категории."""
    query = update.callback_query
    await query.answer()

    # Распарсим data: CAT|<category>|<page>
    _, category, page_str = query.data.split("|")
    page = int(page_str)

    # Сохраняем состояние: текущая категория и страница
    context.user_data["showall_state"] = {"category": category, "page": page}

    # Загрузим и отфильтруем сборки
    with open(DB_PATH, encoding="utf-8") as f:
        all_builds = json.load(f)
    builds = [b for b in all_builds if b.get("category") == category]

    total = len(builds)
    pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    start = (page - 1) * PAGE_SIZE
    chunk = builds[start:start + PAGE_SIZE]

    # Загрузим лейблы типов из utils.db
    from utils.db import load_weapon_types
    type_map = {wt["key"]: wt["label"] for wt in load_weapon_types()}

    # Собираем текст
    lines = [f"📂 <b>Сборки «{category}» ({total}):</b>"]
    for idx, b in enumerate(chunk, start=start + 1):
        typ_label = type_map.get(b.get("type", ""), b.get("type", "—"))
        lines.append(
            f"\n<b>{idx}. {b.get('weapon_name','—')}</b>\n"
            f"├ 📏 Дистанция: {b.get('role','-')}\n"
            f"├ ⚙️ Тип: {typ_label}\n"
            f"├ 🔩 Модулей: {len(b.get('modules', {}))}\n"
            f"└ 👤 Автор: {b.get('author','—')}"
        )

    text = "\n".join(lines)

    # Обычная клавиатура для навигации
    nav = []
    if page > 1:
        nav.append("← Назад")
    if page < pages:
        nav.append("Вперёд →")
    nav.append("🏠 Категории")
    reply_kb = ReplyKeyboardMarkup([nav], resize_keyboard=True, one_time_keyboard=True)

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_kb)

async def navigation_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Шаг 3: обрабатываем ‘← Назад’, ‘Вперёд →’ и ‘🏠 Категории’."""
    text = update.message.text
    state = context.user_data.get("showall_state")
    # Если нет state — просто сбросим на категории
    if not state or text == "🏠 Категории":
        return await show_all_command(update, context)

    category = state["category"]
    page     = state["page"]

    if text == "← Назад":
        page = max(1, page - 1)
    elif text == "Вперёд →":
        page += 1
    else:
        return  # игнорируем прочие

    # эмулируем callback_data и переходим в category_callback
    fake = update  # переиспользуем объект
    fake.callback_query = update.message
    fake.callback_query.data = f"CAT|{category}|{page}"
    return await category_callback(fake, context)

# Экспортируем хэндлеры
show_all_handler      = CommandHandler("show_all", show_all_command)
showcat_callback      = CallbackQueryHandler(category_callback, pattern=r"^CAT\|")
navigation_handler    = MessageHandler(filters.Regex(r"^(← Назад|Вперёд →|🏠 Категории)$"), navigation_handler)
