# conversations/add.py

import os
import json
import logging
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from utils.permissions import admin_only
from utils.db import load_weapon_types

# Путь к файлу с готовыми сборками
DB_PATH = "database/builds.json"

# Шаги диалога
(
    WEAPON_NAME,
    ROLE_INPUT,
    CATEGORY_SELECT,
    MODE_SELECT,
    TYPE_CHOICE,
    MODULE_COUNT,
    MODULE_SELECT,
    IMAGE_UPLOAD,
    CONFIRMATION,
    POST_CONFIRM
) = range(10)


@admin_only
async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛠 <b>Режим добавления сборок включён</b>\n\n"
        "📌 Следуйте пошаговым инструкциям, чтобы добавить новую сборку.\n"
        "Вы можете в любой момент ввести <code>/cancel</code>, чтобы выйти.",
        parse_mode="HTML"
    )
    await update.message.reply_text(
        "Введите название оружия:",
        reply_markup=ReplyKeyboardRemove()
    )
    return WEAPON_NAME


async def get_weapon_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['weapon'] = update.message.text.strip()
    await update.message.reply_text("Теперь введите дистанцию оружия:")
    return ROLE_INPUT


async def get_weapon_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['role'] = update.message.text.strip()
    buttons = [["Топовая мета"], ["Мета"], ["Новинки"]]
    await update.message.reply_text(
        "Выберите категорию сборки:",
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=False)
    )
    return CATEGORY_SELECT


async def get_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['category'] = update.message.text.strip()
    await update.message.reply_text(
        "Выберите режим:",
        reply_markup=ReplyKeyboardMarkup([["Warzone"]], resize_keyboard=True, one_time_keyboard=False)
    )
    return MODE_SELECT


async def get_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['mode'] = update.message.text.strip()

    # Загружаем все возможные типы оружия из database/types.json
    weapon_types = load_weapon_types()  # [{"key": "...", "label": "..."}, ...]
    if not weapon_types:
        await update.message.reply_text(
            "❌ Нет доступных типов оружия.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    # Сохраняем key->label для следующего шага
    context.user_data['type_map'] = {wt['key']: wt['label'] for wt in weapon_types}

    labels = list(context.user_data['type_map'].values())
    buttons = [labels[i:i+2] for i in range(0, len(labels), 2)]

    await update.message.reply_text(
        "Выберите тип оружия:",
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=False)
    )
    return TYPE_CHOICE


async def get_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    selected_label = update.message.text.strip()
    type_map = context.user_data.get('type_map', {})
    selected_key = next((k for k, v in type_map.items() if v == selected_label), None)
    if not selected_key:
        # Повторяем выбор, если label не распознан
        await update.message.reply_text(
            "❌ Неизвестный тип оружия. Пожалуйста, выберите из списка.",
            reply_markup=ReplyKeyboardMarkup(
                [[v] for v in type_map.values()],
                resize_keyboard=True,
                one_time_keyboard=False
            )
        )
        return TYPE_CHOICE

    context.user_data['type'] = selected_key

    # Загружаем варианты модулей для выбранного типа
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
        await update.message.reply_text(
            "❌ Для этого типа оружия модули не настроены.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    try:
        with open(f"database/{filename}", "r", encoding="utf-8") as f:
            variants = json.load(f)
    except Exception as e:
        logging.exception(f"Ошибка при загрузке {filename}")
        await update.message.reply_text(
            f"❌ Не удалось загрузить модули: {e}",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    context.user_data['module_variants'] = variants
    context.user_data['module_options'] = list(variants.keys())

    await update.message.reply_text(
        "Сколько модулей требуется (5 или 8)?",
        reply_markup=ReplyKeyboardMarkup([["5"], ["8"]], resize_keyboard=True, one_time_keyboard=False)
    )
    return MODULE_COUNT


async def get_module_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text not in ("5", "8"):
        await update.message.reply_text("⚠️ Введите либо 5, либо 8.")
        return MODULE_COUNT
    count = int(text)
    context.user_data['module_count'] = count
    context.user_data['selected_modules'] = []
    context.user_data['detailed_modules'] = {}

    opts = context.user_data['module_options']
    buttons = [opts[i:i+2] for i in range(0, len(opts), 2)]
    await update.message.reply_text(
        "Выберите первый модуль:",
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=False)
    )
    return MODULE_SELECT


async def select_modules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    module = update.message.text.strip()
    opts = context.user_data.get('module_options', [])
    if module not in opts or module in context.user_data.get('selected_modules', []):
        await update.message.reply_text("❌ Неверный выбор. Попробуйте снова.")
        return MODULE_SELECT

    context.user_data['current_module'] = module
    variants = context.user_data['module_variants'][module]
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(v['en'], callback_data=v['en'])] for v in variants])

    await update.message.reply_text(f"Выберите вариант для {module}:", reply_markup=kb)
    return MODULE_SELECT


async def module_variant_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    variant = query.data
    mod = context.user_data.get('current_module')
    context.user_data['detailed_modules'][mod] = variant
    context.user_data['selected_modules'].append(mod)
    await query.edit_message_reply_markup(reply_markup=None)

    if len(context.user_data['selected_modules']) >= context.user_data['module_count']:
        await query.message.reply_text(
            "📷 Прикрепите изображение сборки:",
            reply_markup=ReplyKeyboardRemove()
        )
        return IMAGE_UPLOAD

    remaining = [m for m in context.user_data['module_options'] if m not in context.user_data['selected_modules']]
    buttons = [remaining[i:i+2] for i in range(0, len(remaining), 2)]
    await query.message.reply_text(
        "Выберите следующий модуль:",
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=False)
    )
    return MODULE_SELECT


async def reject_early_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❗ Сначала выберите все модули, затем отправьте изображение.")
    return MODULE_SELECT


async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        file = await update.message.photo[-1].get_file()
    elif update.message.document and update.message.document.mime_type.startswith("image/"):
        file = await update.message.document.get_file()
    else:
        await update.message.reply_text("❌ Прикрепите изображение.")
        return IMAGE_UPLOAD

    os.makedirs("images", exist_ok=True)
    path = f"images/{context.user_data['weapon'].replace(' ', '_')}.jpg"
    await file.download_to_drive(path)
    context.user_data['image'] = path

    await update.message.reply_text(
        "✅ Изображение получено. Нажмите «Завершить» или «Отмена».",
        reply_markup=ReplyKeyboardMarkup([["Завершить"], ["Отмена"]], resize_keyboard=True, one_time_keyboard=False)
    )
    return CONFIRMATION


async def confirm_build(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_build = {
        "weapon_name": context.user_data['weapon'],
        "role": context.user_data.get('role', ''),
        "category": context.user_data.get('category', ''),
        "mode": context.user_data['mode'],
        "type": context.user_data['type'],
        "modules": context.user_data['detailed_modules'],
        "image": context.user_data['image'],
        "author": update.effective_user.full_name
    }

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    data = []
    if os.path.exists(DB_PATH):
        with open(DB_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
    data.append(new_build)
    with open(DB_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    await update.message.reply_text(
        "✅ Сборка успешно добавлена! Что дальше?",
        reply_markup=ReplyKeyboardMarkup([["➕ Добавить ещё одну сборку"], ["◀ Отмена"]], resize_keyboard=True, one_time_keyboard=False)
    )
    return POST_CONFIRM


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Действие отменено.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


add_conv = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Regex("➕ Добавить сборку"), add_start),
        CommandHandler("add", add_start)
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
            CallbackQueryHandler(module_variant_callback),
            MessageHandler(filters.PHOTO | filters.Document.IMAGE, reject_early_image)
        ],
        IMAGE_UPLOAD: [MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_image)],
        CONFIRMATION: [
            MessageHandler(filters.Regex("^Завершить$"), confirm_build),
            MessageHandler(filters.Regex("^Отмена$"), cancel)
        ],
        POST_CONFIRM: [
            MessageHandler(filters.Regex("^➕ Добавить ещё одну сборку$"), add_start),
            MessageHandler(filters.Regex("^◀ Отмена$"), cancel)
        ]
    },
    fallbacks=[
        CommandHandler("cancel", cancel)
    ]
)
