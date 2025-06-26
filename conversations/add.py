# conversations/add.py

import os
import json
import logging
import pathlib
import traceback

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

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
DB_PATH = ROOT / "database" / "builds.json"

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
    await update.message.reply_text("Введите название оружия:", reply_markup=ReplyKeyboardRemove())
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
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    )
    return CATEGORY_SELECT


async def get_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['category'] = update.message.text.strip()
    await update.message.reply_text(
        "Выберите режим:",
        reply_markup=ReplyKeyboardMarkup([["Warzone"]], resize_keyboard=True)
    )
    return MODE_SELECT


async def get_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['mode'] = update.message.text.strip()

    weapon_types = load_weapon_types()
    if not weapon_types:
        await update.message.reply_text("❌ Нет доступных типов оружия.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    context.user_data['type_map'] = {wt['key']: wt['label'] for wt in weapon_types}
    labels = list(context.user_data['type_map'].values())
    buttons = [labels[i:i+2] for i in range(0, len(labels), 2)]

    await update.message.reply_text(
        "Выберите тип оружия:",
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    )
    return TYPE_CHOICE


# --- Обязательно до вызова add_conv! ---
async def get_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    selected = update.message.text.strip()
    type_map = context.user_data.get('type_map', {})
    key = next((k for k, v in type_map.items() if v == selected), None)
    if not key:
        await update.message.reply_text(
            "❌ Неизвестный тип. Пожалуйста, выберите кнопкой.",
            reply_markup=ReplyKeyboardMarkup([[v] for v in type_map.values()], resize_keyboard=True)
        )
        return TYPE_CHOICE

    context.user_data['type'] = key

    file_map = {
        "assault": "modules-assault.json",
        "battle": "modules-battle.json",
        "smg":     "modules-pp.json",
        "shotgun": "modules-drobovik.json",
        "marksman":"modules-pehotnay.json",
        "lmg":     "modules-pulemet.json",
        "sniper":  "modules-snayperki.json",
        "pistol":  "modules-pistolet.json",
        "special": "modules-osoboe.json"
    }
    fname = file_map.get(key)
    if not fname:
        await update.message.reply_text("❌ Для этого типа модули не настроены.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    try:
        path = ROOT / "database" / fname
        variants = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logging.exception("Ошибка загрузки модулей")
        await update.message.reply_text(f"❌ Ошибка: {e}", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    context.user_data['module_variants'] = variants
    context.user_data['module_options'] = list(variants.keys())

    await update.message.reply_text(
        "Сколько модулей (5 или 8)?",
        reply_markup=ReplyKeyboardMarkup([["5"], ["8"]], resize_keyboard=True)
    )
    return MODULE_COUNT


async def get_module_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    if txt not in ("5","8"):
        await update.message.reply_text("⚠️ Введите 5 или 8.")
        return MODULE_COUNT
    cnt = int(txt)
    context.user_data['module_count'] = cnt
    context.user_data['selected_modules'] = []
    context.user_data['detailed_modules'] = {}

    opts = context.user_data['module_options']
    buttons = [opts[i:i+2] for i in range(0, len(opts), 2)]
    await update.message.reply_text(
        "Выберите модуль:",
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    )
    return MODULE_SELECT


async def select_modules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mod = update.message.text.strip()
    opts = context.user_data['module_options']
    if mod not in opts or mod in context.user_data['selected_modules']:
        await update.message.reply_text("❌ Неверный выбор.")
        return MODULE_SELECT

    context.user_data['current_module'] = mod
    variants = context.user_data['module_variants'][mod]
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(v['en'], callback_data=v['en'])] for v in variants])
    await update.message.reply_text(f"Вариант для {mod}:", reply_markup=kb)
    return MODULE_SELECT


async def module_variant_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    var = q.data
    mod = context.user_data['current_module']
    context.user_data['detailed_modules'][mod] = var
    context.user_data['selected_modules'].append(mod)
    await q.edit_message_reply_markup(None)

    if len(context.user_data['selected_modules']) >= context.user_data['module_count']:
        await q.message.reply_text("📷 Прикрепите изображение:", reply_markup=ReplyKeyboardRemove())
        return IMAGE_UPLOAD

    rem = [m for m in context.user_data['module_options'] if m not in context.user_data['selected_modules']]
    btns = [rem[i:i+2] for i in range(0, len(rem), 2)]
    await q.message.reply_text("Следующий модуль:", reply_markup=ReplyKeyboardMarkup(btns, resize_keyboard=True))
    return MODULE_SELECT


async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    file = None
    if msg.photo:
        file = await msg.photo[-1].get_file()
    elif msg.document and msg.document.mime_type.startswith("image/"):
        file = await msg.document.get_file()
    else:
        await msg.reply_text("❌ Прикрепите изображение.")
        return IMAGE_UPLOAD

    os.makedirs(ROOT/"images", exist_ok=True)
    p = ROOT/"images"/f"{context.user_data['weapon'].replace(' ','_')}.jpg"
    await file.download_to_drive(str(p))
    context.user_data['image'] = str(p)

    await msg.reply_text("✅ Изображение получено! Нажмите «Завершить».",
                        reply_markup=ReplyKeyboardMarkup([["Завершить"]], resize_keyboard=True))
    return CONFIRMATION


async def confirm_build(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new = {
        "weapon_name": context.user_data['weapon'],
        "role":        context.user_data.get('role',''),
        "category":    context.user_data.get('category',''),
        "mode":        context.user_data['mode'],
        "type":        context.user_data['type'],
        "modules":     context.user_data['detailed_modules'],
        "image":       context.user_data['image'],
        "author":      update.effective_user.full_name
    }
    try:
        logging.info(f"[ADD] Saving → {new}")
        DB_PATH.parent.mkdir(exist_ok=True)
        arr = json.loads(DB_PATH.read_text(encoding="utf-8")) if DB_PATH.exists() else []
        arr.append(new)
        DB_PATH.write_text(json.dumps(arr, indent=2, ensure_ascii=False), encoding="utf-8")
        logging.info("[ADD] Saved to %s", DB_PATH)
    except Exception:
        logging.exception("[ADD] Save failed")
        await update.message.reply_text("❌ Ошибка сохранения.")
        return ConversationHandler.END

    await update.message.reply_text("✅ Добавлено! Что дальше?",
                                    reply_markup=ReplyKeyboardMarkup([["➕ Добавить ещё"], ["◀ Отмена"]], resize_keyboard=True))
    return POST_CONFIRM


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Отменено.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


add_conv = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Regex("➕ Добавить сборку"), add_start),
        CommandHandler("add", add_start)
    ],
    states={
        WEAPON_NAME:     [MessageHandler(filters.TEXT & ~filters.COMMAND, get_weapon_name)],
        ROLE_INPUT:      [MessageHandler(filters.TEXT & ~filters.COMMAND, get_weapon_role)],
        CATEGORY_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_category)],
        MODE_SELECT:     [MessageHandler(filters.TEXT & ~filters.COMMAND, get_mode)],
        TYPE_CHOICE:     [MessageHandler(filters.TEXT & ~filters.COMMAND, get_type)],
        MODULE_COUNT:    [MessageHandler(filters.TEXT & ~filters.COMMAND, get_module_count)],
        MODULE_SELECT:   [
            MessageHandler(filters.TEXT & ~filters.COMMAND, select_modules),
            CallbackQueryHandler(module_variant_callback)
        ],
        IMAGE_UPLOAD:    [MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_image)],
        CONFIRMATION:    [MessageHandler(filters.Regex("^Завершить$"), confirm_build)],
        POST_CONFIRM:    [
            MessageHandler(filters.Regex("^➕ Добавить ещё$"), add_start),
            MessageHandler(filters.Regex("^◀ Отмена$"), cancel)
        ]
    },
    fallbacks=[CommandHandler("cancel", cancel)]
)
