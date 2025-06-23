import os
import json
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from telegram import ReplyKeyboardRemove
from telegram.ext import (
    CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, ContextTypes, filters
)
from utils.permissions import ALLOWED_USERS
from utils.db import load_weapon_types
from utils.translators import load_translation_dict
from utils.keyboards import build_keyboard_with_main

WEAPON_NAME, ROLE_INPUT, CATEGORY_SELECT, MODE_SELECT, TYPE_CHOICE, MODULE_COUNT, MODULE_SELECT, IMAGE_UPLOAD, CONFIRMATION, POST_CONFIRM = range(10)
DB_PATH = "database/builds.json"

async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("❌ У вас нет прав добавления.")
        return ConversationHandler.END

    await update.message.reply_text(
        "🛠 <b>Режим добавления сборок включён</b>\n\n"
        "📌 Следуйте пошаговым инструкциям, чтобы добавить новую сборку.\n"
        "Вы можете в любой момент ввести <code>/cancel</code>, чтобы выйти.",
        parse_mode="HTML"
    )

    await update.message.reply_text("Введите название оружия:", reply_markup=ReplyKeyboardRemove())
    return WEAPON_NAME

async def get_weapon_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("⚙️ get_weapon_name called")
    context.user_data['weapon'] = update.message.text
    await update.message.reply_text("Теперь введите Дистанцию оружия")
    return ROLE_INPUT


async def get_weapon_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['role'] = update.message.text
    buttons = [["Топовая мета"], ["Мета"], ["Новинки"]]
    await update.message.reply_text("Выберите категорию сборки:", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
    return CATEGORY_SELECT

async def get_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['category'] = update.message.text
    await update.message.reply_text("Выберите режим:", reply_markup=ReplyKeyboardMarkup([["Warzone"]], resize_keyboard=True))
    return MODE_SELECT

async def get_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['mode'] = update.message.text
    weapon_types = load_weapon_types()
    key_to_label = {item["key"]: item["label"] for item in weapon_types}

    import json
    with open(DB_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    available_keys = sorted(set(
        b['type'] for b in data
        if b.get("mode", "").lower() == context.user_data['mode'].lower()
        and b.get("category") == context.user_data.get("category")
    ))

    context.user_data['type_map'] = {key: key_to_label.get(key, key) for key in available_keys}
    labels = list(context.user_data['type_map'].values())
    buttons = [labels[i:i+2] for i in range(0, len(labels), 2)]

    
    await update.message.reply_text("⬇️ Загрузка доступных типов...", reply_markup=ReplyKeyboardRemove())
    await update.message.reply_text("Выберите тип оружия:", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
    return TYPE_CHOICE

async def get_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    selected_label = update.message.text.strip()
    weapon_types = load_weapon_types()
    label_to_key = {item["label"]: item["key"] for item in weapon_types}
    selected_key = label_to_key.get(selected_label)

    if not selected_key:
        await update.message.reply_text("❌ Тип оружия не распознан. Пожалуйста, выберите из предложенных кнопок.")
        return TYPE_CHOICE

    context.user_data['type'] = selected_key

    file_map = {
        "assault": "modules-assault.json",
        "battle": "modules-battle.json",
        "smg": "modules-pp.json",
        "shotgun": "modules-drobovik.json",
        "marksman": "modules-pehotnay.json",
        "lmg": "modules-pulemet.json",
        "sniper": "modules-snayperki.json",
        "pistol": "modules-pistolet.json",
        "special": "modules-osoboe.json"
    }

    filename = file_map.get(selected_key)
    if not filename:
        await update.message.reply_text("❌ Для выбранного типа оружия модули пока не настроены.")
        return ConversationHandler.END

    with open(f"database/{filename}", "r", encoding="utf-8") as f:
        module_data = json.load(f)

    context.user_data['module_variants'] = module_data
    context.user_data['module_options'] = list(module_data.keys())

    await update.message.reply_text("Сколько модулей:", reply_markup=ReplyKeyboardMarkup([["5"], ["8"]], resize_keyboard=True))
    return MODULE_COUNT

async def get_module_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['module_count'] = int(update.message.text)
    context.user_data['selected_modules'] = []
    context.user_data['detailed_modules'] = {}
    buttons = [context.user_data['module_options'][i:i+2] for i in range(0, len(context.user_data['module_options']), 2)]
    await update.message.reply_text("Выберите модуль:", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
    return MODULE_SELECT

async def select_modules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    module = update.message.text
    if module not in context.user_data['module_options'] or module in context.user_data['selected_modules']:
        await update.message.reply_text("Некорректный или уже выбранный модуль.")
        return MODULE_SELECT

    context.user_data['current_module'] = module
    variants = context.user_data['module_variants'].get(module, [])
    context.user_data['variant_translation'] = {v['en']: v['ru'] for v in variants}
    keyboard = [[InlineKeyboardButton(v['en'], callback_data=v['en'])] for v in variants]

    await update.message.reply_text(f"Выберите вариант для {module}:", reply_markup=InlineKeyboardMarkup(keyboard))
    return MODULE_SELECT

async def module_variant_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    variant = query.data
    current_module = context.user_data.get('current_module')

    if not current_module:
        await query.message.reply_text("⚠️ Ошибка: модуль не выбран.")
        return MODULE_SELECT

    context.user_data['detailed_modules'][current_module] = variant
    if current_module not in context.user_data['selected_modules']:
        context.user_data['selected_modules'].append(current_module)

    if len(context.user_data['selected_modules']) >= context.user_data['module_count']:
        await query.edit_message_reply_markup(reply_markup=None)
        context.user_data.pop('current_module', None)
        context.user_data['waiting_image'] = True
        await query.message.reply_text("📷 Все модули выбраны.\nТеперь прикрепите изображение сборки:")
        return IMAGE_UPLOAD

    remaining = [m for m in context.user_data['module_options'] if m not in context.user_data['selected_modules']]
    buttons = [remaining[i:i+2] for i in range(0, len(remaining), 2)]
    context.user_data['current_module'] = None
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text("Выберите следующий модуль:", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
    return MODULE_SELECT

async def reject_early_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❗ Сначала выберите все модули. Потом отправьте изображение.")
    return MODULE_SELECT

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = None
    if update.message.photo:
        file = await update.message.photo[-1].get_file()
    elif update.message.document and update.message.document.mime_type.startswith("image/"):
        file = await update.message.document.get_file()
    else:
        await update.message.reply_text("❌ Пожалуйста, прикрепите изображение как фото или файл.")
        return IMAGE_UPLOAD

    os.makedirs("images", exist_ok=True)
    path = f"images/{context.user_data['weapon'].replace(' ', '_')}.jpg"
    await file.download_to_drive(path)
    context.user_data['image'] = path

    await update.message.reply_text(
        "✅ Изображение получено.\n\nНажмите «Завершить», чтобы сохранить сборку, или «Отмена», чтобы прервать.",
        reply_markup=ReplyKeyboardMarkup([["Завершить", "Отмена"]], resize_keyboard=True)
    )
    return CONFIRMATION

async def confirm_build(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_build = {
        "weapon_name": context.user_data['weapon'],
        "role": context.user_data.get('role', ''),
        "category": context.user_data.get("category", "Мета"),
        "mode": context.user_data['mode'],
        "type": context.user_data['type'],
        "modules": context.user_data['detailed_modules'],
        "image": context.user_data['image'],
        "author": update.effective_user.full_name
    }

    if os.path.exists(DB_PATH):
        with open(DB_PATH, 'r') as f:
            data = json.load(f)
    else:
        data = []
    data.append(new_build)
    with open(DB_PATH, 'w') as f:
        json.dump(data, f, indent=2)

    keyboard = [["➕ Добавить ещё одну сборку"], ["◀ Отмена"]]
    await update.message.reply_text("✅ Сборка успешно добавлена!\n\nЧто хотите сделать дальше?", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    return POST_CONFIRM

add_conv = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Regex("➕ Добавить сборку"), add_start),
        CommandHandler("add", add_start),
    ],
    states={
        WEAPON_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_weapon_name)],
        ROLE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_weapon_role)],
        CATEGORY_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_category)],
        MODE_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_mode)],
        TYPE_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_type)],
        MODULE_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_module_count)],
        MODULE_SELECT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, select_modules),
            MessageHandler(filters.PHOTO | filters.Document.IMAGE, reject_early_image),
            CallbackQueryHandler(module_variant_callback),
        ],
        IMAGE_UPLOAD: [MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_image)],
        CONFIRMATION: [
            MessageHandler(filters.TEXT & filters.Regex("^Завершить$"), confirm_build),
            MessageHandler(filters.Regex("Отмена"), lambda u, c: u.message.reply_text("❌ Отменено.")),
        ],
        POST_CONFIRM: [
            MessageHandler(filters.Regex("➕ Добавить ещё одну сборку"), add_start),
            MessageHandler(filters.Regex("◀ Отмена"), lambda u, c: u.message.reply_text("🏠 Возврат в главное меню...")),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", lambda u, c: u.message.reply_text("❌ Действие отменено.")),
    ]
)
