# handlers/show_all.py
import os
import json
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ParseMode,
)
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# Константы
ROOT = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(ROOT, "database", "builds.json")
PAGE_SIZE = 5

# Эмодзи для категорий
CATEGORY_EMOJI = {
    "Топовая мета": "🔥",
    "Мета":       "📈",
    "Новинки":    "🆕",
}


def load_builds() -> list[dict]:
    if not os.path.exists(DB_PATH):
        return []
    with open(DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def make_categories_keyboard(builds: list[dict]) -> InlineKeyboardMarkup:
    # считаем сборки по категориям
    counts: dict[str,int] = {}
    for b in builds:
        counts[b.get("category","—")] = counts.get(b.get("category","—"), 0) + 1

    buttons = []
    for cat, emoji in CATEGORY_EMOJI.items():
        cnt = counts.get(cat, 0)
        # callback_data = cat — в обработчике разбирать имя категории
        buttons.append([InlineKeyboardButton(f"{emoji} {cat} ({cnt})", callback_data=f"cat|{cat}|0")])
    return InlineKeyboardMarkup(buttons)


def make_page_keyboard(category: str, page: int, total: int) -> InlineKeyboardMarkup:
    kb = []
    # «⬅» если не на первой странице
    if page > 0:
        kb.append(InlineKeyboardButton("⬅ Пред.", callback_data=f"cat|{category}|{page-1}"))
    # «➡» если есть следующая
    if (page+1)*PAGE_SIZE < total:
        kb.append(InlineKeyboardButton("След. ➡", callback_data=f"cat|{category}|{page+1}"))
    # Кнопка возврата
    kb.append(InlineKeyboardButton("🏠 К категориям", callback_data="back|0|0"))
    # каждая кнопка в отдельной строке
    return InlineKeyboardMarkup([[b] for b in kb])


async def show_all_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    builds = load_builds()
    total = len(builds)
    text = (
        f"📦 <b>Все сборки</b> (<code>{total}</code>)\n\n"
        "Нажмите на нужную категорию ниже, чтобы посмотреть сборки в ней:"
    )
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=make_categories_keyboard(builds)
    )


async def category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает нажатия:
    - cat|<Категория>|<Страница>
    - back|0|0
    """
    query = update.callback_query
    await query.answer()

    data = query.data.split("|")
    action = data[0]

    builds = load_builds()

    if action == "back":
        # возвращаем к списку категорий
        total = len(builds)
        text = (
            f"📦 <b>Все сборки</b> (<code>{total}</code>)\n\n"
            "Нажмите на нужную категорию ниже, чтобы посмотреть сборки в ней:"
        )
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=make_categories_keyboard(builds)
        )
        return

    # иначе action == "cat"
    category = data[1]
    page = int(data[2])

    # фильтруем сборки по категории
    filtered = [b for b in builds if b.get("category") == category]
    total_in_cat = len(filtered)

    # отрезаем нужную страницу
    chunk = filtered[page*PAGE_SIZE:(page+1)*PAGE_SIZE]

    # собираем текст
    lines = [f"📂 <b>Сборки категории «{category}»</b> (<code>{total_in_cat}</code>)\n"]
    for idx, b in enumerate(chunk, start=page*PAGE_SIZE + 1):
        name = b.get("weapon_name", "—")
        role = b.get("role", "-")
        typ  = b.get("type", "—")
        cnt  = len(b.get("modules", {}))
        auth = b.get("author", "—")

        lines.append(
            f"<b>{idx}. {name}</b>\n"
            f"├ 📏 Дистанция: {role}\n"
            f"├ ⚙️ Тип: {typ}\n"
            f"├ 🔩 Модулей: {cnt}\n"
            f"└ 👤 Автор: {auth}\n"
        )

    # правим клавиатуру «пред/след/к категориям»
    kb = make_page_keyboard(category, page, total_in_cat)

    await query.edit_message_text(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )


# регистрируем оба хэндлера
show_all_handler       = CommandHandler("show_all", show_all_command)
show_all_callback      = CallbackQueryHandler(category_callback, pattern="^(cat|back)\|")
