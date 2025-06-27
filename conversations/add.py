import os
import json
import logging
import pathlib

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
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
    # Убираем старую клавиатуру
    await update.message.reply_text(
        "🛠 <b>Режим добавления сборок включён</b>\n\n"
        "📌 Следуйте пошаговым инструкциям. В любой момент /cancel для выхода.",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )
    # Первый шаг: ввод названия
    await update.message.reply_text("Введите название оружия:")
    return WEAPON_NAME


async def get_weapon_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['weapon'] = update.message.text.strip()
    await update.message.reply_text("Теперь введите дистанцию оружия (любым текстом):")
    return ROLE_INPUT


async def get_weapon_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['role'] = update.message.text.strip()
    # Далее — выбор категории сборки
    buttons = [["Топовая мета"], ["Мета"], ["Новинки"]]
    await update.message.reply_text(
        "Выберите категорию сборки:",
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    )
    return CATEGORY_SELECT


async def get_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text not in ("Топовая мета", "Мета", "Новинки"):
        # не распознали — повторяем
        buttons = [["Топовая мета"], ["Мета"], ["Новинки"]]
        await update.message.reply_text(
            "❌ Пожалуйста, выберите кнопку.",
            reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        )
        return CATEGORY_SELECT

    context.user_data['category'] = text
    # Выбор режима (единственный вариант — Warzone)
    await update.message.reply_text(
        "Выберите режим:",
        reply_markup=ReplyKeyboardMarkup([["Warzone"]], resize_keyboard=True)
    )
    return MODE_SELECT


async def get_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.lower() != "warzone":
        await update.message.reply_text(
            "❌ Нажмите кнопку <b>Warzone</b>.",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup([["Warzone"]], resize_keyboard=True)
        )
        return MODE_SELECT

    context.user_data['mode'] = text
    # Загружаем типы оружия для выбора
    weapon_types = load_weapon_types()
    if not weapon_types:
        await update.message.reply_text(
            "❌ Нет доступных типов оружия.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    # строим reply-кнопки по 2 в ряд
    context.user_data['type_map'] = {wt['key']: wt['label'] for wt in weapon_types}
    labels = list(context.user_data['type_map'].values())
    buttons = [labels[i:i+2] for i in range(0, len(labels), 2)]

    await update.message.reply_text(
        "Выберите тип оружия:",
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    )
    return TYPE_CHOICE


async def get_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sel = update.message.text.strip()
    type_map = context.user_data['type_map']
    key = next((k for k, v in type_map.items() if v == sel), None)
    if not key:
        # повтор выбора
        buttons = [[v] for v in type_map.values()]
        await update.message.reply_text(
            "❌ Нажмите кнопку с типом оружия.",
            reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        )
        return TYPE_CHOICE

    context.user_data['type'] = key

    # Загружаем варианты модулей из соответствующего файла
    file_map = {
        "assault":  "modules-assault.json",
        "battle":   "modules-battle.json",
        "smg":      "modules-pp.json",
        "shotgun":  "modules-drobovik.json",
        "marksman": "modules-pehotnay.json",
        "lmg":      "modules-pulemet.json",
        "sniper":   "modules-snayperki.json",
        "pistol":   "modules-pistolet.json",
        "special":  "modules-osoboe.json",
    }
    fname = file_map.get(key)
    if not fname:
        await update.message.reply_text(
            "❌ Для этого типа модули не настроены.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    try:
        path = ROOT / "database" / fname
        variants = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logging.exception("Ошибка загрузки модулей")
        await update.message.reply_text(
            f"❌ Ошибка загрузки: {e}",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    context.user_data['module_variants'] = variants
    context.user_data['module_options'] = list(variants.keys())

    await update.message.reply_text(
        "Сколько модулей установить? (5 или 8)",
        reply_markup=ReplyKeyboardMarkup([["5"], ["8"]], resize_keyboard=True)
    )
    return MODULE_COUNT


async def get_module_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text not in ("5", "8"):
        await update.message.reply_text("⚠️ Введите 5 или 8.")
        return MODULE_COUNT

    count = int(text)
    context.user_data['module_count'] = count
    context.user_data['selected_modules'] = []
    context.user_data['detailed_modules'] = {}

    # показываем reply-кнопки для выбора модулей
    opts = context.user_data['module_options']
    buttons = [opts[i:i+2] for i in range(0, len(opts), 2)]
    await update.message.reply_text(
        "Выберите модуль (категорию):",
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    )
    return MODULE_SELECT


async def select_modules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    module = update.message.text.strip()
    opts = context.user_data['module_options']
    if module not in opts or module in context.user_data['selected_modules']:
        await update.message.reply_text("❌ Нажмите кнопку с модулем.")
        return MODULE_SELECT

    context.user_data['current_module'] = module
    variants = context.user_data['module_variants'][module]

    # Inline-кнопки для вариантов этого модуля
    inline = [[InlineKeyboardButton(v['en'], callback_data=v['en'])] for v in variants]
    await update.message.reply_text(
        f"Варианты для «{module}»:",
        reply_markup=InlineKeyboardMarkup(inline)
    )
    return MODULE_SELECT


async def module_variant_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data
    module = context.user_data.get('current_module')
    if not module:
        await query.message.reply_text("❌ Ошибка.")
        return ConversationHandler.END

    context.user_data['detailed_modules'][module] = choice
    context.user_data['selected_modules'].append(module)
    # убираем inline-кнопки
    await query.edit_message_reply_markup(None)

    # если все модули выбраны
    if len(context.user_data['selected_modules']) >= context.user_data['module_count']:
        await query.message.reply_text(
            "📷 Прикрепите изображение сборки:",
            reply_markup=ReplyKeyboardRemove()
        )
        return IMAGE_UPLOAD

    # иначе — следующий модуль
    remaining = [m for m in context.user_data['module_options'] if m not in context.user_data['selected_modules']]
    buttons = [remaining[i:i+2] for i in range(0, len(remaining), 2)]
    await query.message.reply_text(
        "Выберите следующий модуль:",
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    )
    return MODULE_SELECT


async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    file_obj = None
    if msg.photo:
        file_obj = await msg.photo[-1].get_file()
    elif msg.document and msg.document.mime_type.startswith("image/"):
        file_obj = await msg.document.get_file()
    else:
        await msg.reply_text("❌ Отправьте фото или скриншот.")
        return IMAGE_UPLOAD

    os.makedirs(ROOT / "images", exist_ok=True)
    img_name = f"{context.user_data['weapon'].replace(' ', '_')}.jpg"
    img_path = ROOT / "images" / img_name
    await file_obj.download_to_drive(str(img_path))
    context.user_data['image'] = str(img_path)

    await msg.reply_text(
        "✅ Изображение получено. Нажмите «Завершить»:",
        reply_markup=ReplyKeyboardMarkup([["Завершить"]], resize_keyboard=True)
    )
    return CONFIRMATION


async def confirm_build(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_build = {
        "weapon_name": context.user_data.get('weapon', ''),
        "role":        context.user_data.get('role', ''),
        "category":    context.user_data.get('category', ''),
        "mode":        context.user_data.get('mode', ''),
        "type":        context.user_data.get('type', ''),
        "modules":     context.user_data.get('detailed_modules', {}),
        "image":       context.user_data.get('image', ''),
        "author":      update.effective_user.full_name
    }
    logging.info("[ADD] New build: %r", new_build)

    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = json.loads(DB_PATH.read_text(encoding="utf-8")) if DB_PATH.exists() else []
        data.append(new_build)
        DB_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        logging.exception("[ADD] Save failed")
        await update.message.reply_text("❌ Ошибка сохранения.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    await update.message.reply_text(
        "✅ Сборка добавлена! Что дальше?",
        reply_markup=ReplyKeyboardMarkup([["➕ Добавить ещё"], ["◀ Отмена"]], resize_keyboard=True)
    )
    return POST_CONFIRM


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Отменено.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


add_conv = ConversationHandler(
    entry_points=[
        CommandHandler("add", add_start),
        MessageHandler(filters.Regex("^➕ Добавить сборку$"), add_start),
    ],
    states={
        WEAPON_NAME:     [MessageHandler(filters.TEXT & ~filters.COMMAND, get_weapon_name)],
        ROLE_INPUT:      [MessageHandler(filters.TEXT & ~filters.COMMAND, get_weapon_role)],
        CATEGORY_SELECT: [MessageHandler(filters.Regex("^(Топовая мета|Мета|Новинки)$"), get_category)],
        MODE_SELECT:     [MessageHandler(filters.Regex("^Warzone$"), get_mode)],
        TYPE_CHOICE:     [MessageHandler(filters.TEXT & ~filters.COMMAND, get_type)],
        MODULE_COUNT:    [MessageHandler(filters.Regex("^[58]$"), get_module_count)],
        MODULE_SELECT:   [
            CallbackQueryHandler(module_variant_callback),
            MessageHandler(filters.TEXT & ~filters.COMMAND, select_modules),
        ],
        IMAGE_UPLOAD:    [MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_image)],
        CONFIRMATION:    [MessageHandler(filters.Regex("^Завершить$"), confirm_build)],
        POST_CONFIRM:    [
            MessageHandler(filters.Regex("^➕ Добавить ещё$"), add_start),
            MessageHandler(filters.Regex("^◀ Отмена$"), cancel),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

__all__ = ["add_conv"]
