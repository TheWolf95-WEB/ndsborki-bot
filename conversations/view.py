from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import MessageHandler, ConversationHandler, ContextTypes, filters
from utils.db import load_db, load_weapon_types
from utils.translators import load_translation_dict, get_type_label_by_key

VIEW_CATEGORY_SELECT, VIEW_WEAPON, VIEW_SET_COUNT, VIEW_DISPLAY = range(4)


async def view_category_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_db()
    raw_categories = {
        "Топовая мета": "🔥 Топовая мета",
        "Мета": "📈 Мета",
        "Новинки": "🆕 Новинки"
    }

    counts = {
        cat: sum(1 for b in data if b.get("mode", "").lower() == "warzone" and b.get("category") == cat)
        for cat in raw_categories
    }

    user_input = update.message.text.strip().split(" (")[0]
    for key, label in raw_categories.items():
        if user_input == label:
            context.user_data['selected_category'] = key
            type_keys = sorted(set(
                b['type'] for b in data
                if b.get("mode", "").lower() == "warzone" and b.get("category") == key
            ))

            key_to_label = {i["key"]: i["label"] for i in load_weapon_types()}
            context.user_data['label_to_key'] = {v: k for k, v in key_to_label.items()}
            buttons = [[key_to_label.get(t, t)] for t in type_keys]
            await update.message.reply_text("Выберите тип оружия:", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
            return VIEW_WEAPON  # 👈 ОБЯЗАТЕЛЬНО!



async def view_select_weapon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    selected_label = update.message.text.strip()
    label_to_key = context.user_data.get('label_to_key', {})
    selected_key = label_to_key.get(selected_label, selected_label)
    context.user_data['selected_type'] = selected_key

    # 🔍 Логирование в консоль
    print("🔎 Выбранный текст:", selected_label)
    print("🧭 Сопоставление label_to_key:", label_to_key)
    print("✅ Итоговый ключ типа:", selected_key)

    data = load_db()
    weapons = sorted(set(
        b['weapon_name'] for b in data
        if b['type'] == selected_key and b.get('category') == context.user_data.get('selected_category')
    ))

    if not weapons:
        msg = (
            f"⚠️ Не удалось найти оружие для типа: <code>{selected_key}</code>\n\n"
            f"Проверь, что в базе есть сборки с типом <code>{selected_key}</code> и категорией <code>{context.user_data.get('selected_category')}</code>."
        )
        await update.message.reply_text(msg, parse_mode="HTML")
        return ConversationHandler.END

    context.user_data['available_weapons'] = weapons
    buttons = [[w] for w in weapons]
    await update.message.reply_text("Выберите оружие:", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
    return VIEW_SET_COUNT



async def view_set_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['selected_weapon'] = update.message.text
    data = load_db()
    weapon = context.user_data['selected_weapon']
    type_ = context.user_data['selected_type']

    count_5 = sum(1 for b in data if b['weapon_name'] == weapon and b['type'] == type_ and len(b['modules']) == 5)
    count_8 = sum(1 for b in data if b['weapon_name'] == weapon and b['type'] == type_ and len(b['modules']) == 8)

    keyboard = [[f"5 ({count_5})"], [f"8 ({count_8})"]]
    await update.message.reply_text("Выберите количество модулей:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    return VIEW_DISPLAY


async def view_display_builds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_text = update.message.text
    try:
        count = int(raw_text.split()[0])
    except ValueError:
        await update.message.reply_text("⚠️ Пожалуйста, выберите количество модулей с клавиатуры.")
        return VIEW_DISPLAY

    context.user_data['selected_count'] = count
    data = load_db()

    filtered = [
        b for b in data
        if b['type'] == context.user_data['selected_type'] and
           b['weapon_name'] == context.user_data['selected_weapon'] and
           len(b['modules']) == count and
           b.get('category') == context.user_data.get('selected_category')
    ]

    if not filtered:
        context.user_data.pop('selected_count', None)
        return await view_set_count(update, context)

    context.user_data['viewed_builds'] = filtered
    context.user_data['current_index'] = 0
    return await send_build(update, context)


async def send_build(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.user_data['current_index']
    build = context.user_data['viewed_builds'][idx]
    translation = load_translation_dict(build['type'])

    modules_text = "\n".join(
        f"├ {k}: {translation.get(v, v)}"
        for k, v in build['modules'].items()
    )

    caption = (
        f"Оружие: {build['weapon_name']}\n"
        f"Дистанция: {build.get('role', '-')}\n"
        f"Тип: {get_type_label_by_key(build['type'])}\n\n"
        f"Модули: {len(build['modules'])}\n"
        f"{modules_text}\n\n"
        f"Автор: {build['author']}"
    )

    nav = []
    nav_row = []
    if idx > 0:
        nav_row.append("⬅ Предыдущая")
    if idx < len(context.user_data['viewed_builds']) - 1:
        nav_row.append("➡ Следующая")
    if nav_row:
        nav.append(nav_row)
    nav.append(["📋 Сборки Warzone"])
    markup = ReplyKeyboardMarkup(nav, resize_keyboard=True)

    import os
    from telegram import InputFile
    if os.path.exists(build['image']):
        with open(build['image'], 'rb') as img:
            await update.message.reply_photo(photo=InputFile(img), caption=caption, reply_markup=markup, parse_mode="HTML")
    else:
        await update.message.reply_text(caption, reply_markup=markup, parse_mode="HTML")
    return VIEW_DISPLAY


async def next_build(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data['current_index'] < len(context.user_data['viewed_builds']) - 1:
        context.user_data['current_index'] += 1
        return await send_build(update, context)


async def previous_build(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data['current_index'] > 0:
        context.user_data['current_index'] -= 1
        return await send_build(update, context)


from telegram.ext import MessageHandler, ConversationHandler

view_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("📋 Сборки Warzone"), view_category_select)],
    states={
        VIEW_CATEGORY_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, view_category_select)],
        VIEW_WEAPON: [MessageHandler(filters.TEXT & ~filters.COMMAND, view_select_weapon)],  # ✅ сюда мы и должны попасть
        VIEW_SET_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, view_set_count)],
        VIEW_DISPLAY: [
            MessageHandler(filters.Regex("5|8"), view_display_builds),
            MessageHandler(filters.Regex("➡ Следующая"), next_build),
            MessageHandler(filters.Regex("⬅ Предыдущая"), previous_build),
            MessageHandler(filters.Regex("📋 Сборки Warzone"), view_category_select),
        ]
    },
    fallbacks=[],
)


__all__ = ["view_conv"]
