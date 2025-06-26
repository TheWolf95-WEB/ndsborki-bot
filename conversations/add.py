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
    # Запрос названия оружия
    await update.message.reply_text("Введите название оружия:", reply_markup=ReplyKeyboardRemove())
    return WEAPON_NAME

async def get_weapon_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['weapon'] = update.message.text.strip()
    await update.message.reply_text("Теперь введите дистанцию оружия:")
    return ROLE_INPUT

async def get_weapon_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['role'] = update.message.text.strip()
    # Предоставляем варианты категорий
    buttons = [["Топовая мета"], ["Мета"], ["Новинки"]]
    await update.message.reply_text(
        "Выберите категорию сборки:",
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    )
    return CATEGORY_SELECT

async def get_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['category'] = update.message.text.strip()
    # Предоставляем варианты режима (здесь только Warzone)
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

    # Готовим отображение ключ→метка для типов оружия
    context.user_data['type_map'] = {wt['key']: wt['label'] for wt in weapon_types}
    type_labels = list(context.user_data['type_map'].values())
    # Разбиваем метки по две кнопки в ряд
    buttons = [type_labels[i:i+2] for i in range(0, len(type_labels), 2)]

    await update.message.reply_text(
        "Выберите тип оружия:",
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    )
    return TYPE_CHOICE

# --- Функция должна быть объявлена до создания add_conv! ---
async def get_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    selected_type_label = update.message.text.strip()
    type_map = context.user_data.get('type_map', {})
    # Находим ключ по выбранной метке
    type_key = next((k for k, v in type_map.items() if v == selected_type_label), None)
    if not type_key:
        # Если ввод не соответствует ни одному типу, предлагаем выбрать кнопкой
        await update.message.reply_text(
            "❌ Неизвестный тип. Пожалуйста, выберите тип оружия, используя предложенные кнопки.",
            reply_markup=ReplyKeyboardMarkup([[v] for v in type_map.values()], resize_keyboard=True)
        )
        return TYPE_CHOICE

    context.user_data['type'] = type_key

    # Соответствие типа оружия файлу модулей
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
    fname = file_map.get(type_key)
    if not fname:
        await update.message.reply_text("❌ Для этого типа оружия модули не настроены.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    # Загружаем варианты модулей
    try:
        path = ROOT / "database" / fname
        variants = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logging.exception("Ошибка загрузки модулей")
        await update.message.reply_text(f"❌ Ошибка при загрузке модулей: {e}", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    # Сохраняем варианты модулей и их список
    context.user_data['module_variants'] = variants
    context.user_data['module_options'] = list(variants.keys())

    await update.message.reply_text(
        "Сколько модулей установить (5 или 8)?",
        reply_markup=ReplyKeyboardMarkup([["5"], ["8"]], resize_keyboard=True)
    )
    return MODULE_COUNT

async def get_module_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    count_text = update.message.text.strip()
    if count_text not in ("5", "8"):
        await update.message.reply_text("⚠️ Введите 5 или 8.")
        return MODULE_COUNT
    module_count = int(count_text)
    context.user_data['module_count'] = module_count
    context.user_data['selected_modules'] = []
    context.user_data['detailed_modules'] = {}

    # Предлагаем список модулей для выбора
    module_list = context.user_data['module_options']
    buttons = [module_list[i:i+2] for i in range(0, len(module_list), 2)]
    await update.message.reply_text(
        "Выберите модуль:",
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    )
    return MODULE_SELECT

async def select_modules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    module_name = update.message.text.strip()
    available_options = context.user_data.get('module_options', [])
    # Проверяем, что выбран модуль из списка и ещё не выбран
    if module_name not in available_options or module_name in context.user_data['selected_modules']:
        await update.message.reply_text("❌ Неверный выбор модуля. Пожалуйста, выберите из предложенных вариантов.")
        return MODULE_SELECT

    # Сохраняем текущий выбираемый модуль
    context.user_data['current_module'] = module_name
    variants = context.user_data['module_variants'][module_name]
    # Строим inline-клавиатуру для вариантов одного модуля
    inline_buttons = [[InlineKeyboardButton(v['en'], callback_data=v['en'])] for v in variants]
    variant_keyboard = InlineKeyboardMarkup(inline_buttons)
    await update.message.reply_text(f"Варианты для модуля «{module_name}»:", reply_markup=variant_keyboard)
    return MODULE_SELECT

async def module_variant_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    selected_variant = query.data
    module_name = context.user_data.get('current_module')
    if not module_name:
        await query.message.reply_text("❌ Произошла ошибка при выборе модуля.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    context.user_data['detailed_modules'][module_name] = selected_variant
    context.user_data['selected_modules'].append(module_name)
    # Убираем inline-кнопки после выбора варианта
    await query.edit_message_reply_markup(reply_markup=None)

    # Если выбрали все модули — предложить загрузить изображение
    if len(context.user_data['selected_modules']) >= context.user_data['module_count']:
        await query.message.reply_text("📷 Прикрепите изображение сборки (скриншот):", reply_markup=ReplyKeyboardRemove())
        return IMAGE_UPLOAD

    # Иначе — выбрать следующий модуль
    remaining = [m for m in context.user_data['module_options'] if m not in context.user_data['selected_modules']]
    next_buttons = [remaining[i:i+2] for i in range(0, len(remaining), 2)]
    await query.message.reply_text("Выберите следующий модуль:", reply_markup=ReplyKeyboardMarkup(next_buttons, resize_keyboard=True))
    return MODULE_SELECT

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    file_obj = None
    # Принимаем либо фотографию, либо файл изображения
    if message.photo:
        file_obj = await message.photo[-1].get_file()
    elif message.document and message.document.mime_type and message.document.mime_type.startswith("image/"):
        file_obj = await message.document.get_file()
    else:
        await message.reply_text("❌ Пожалуйста, прикрепите изображение (фото или скриншот).")
        return IMAGE_UPLOAD

    # Убеждаемся, что папка для изображений существует и сохраняем туда файл
    os.makedirs(ROOT / "images", exist_ok=True)
    image_filename = f"{context.user_data['weapon'].replace(' ', '_')}.jpg"
    image_path = ROOT / "images" / image_filename
    await file_obj.download_to_drive(str(image_path))
    context.user_data['image'] = str(image_path)

    # Подтверждаем получение изображения и предлагаем завершить
    await message.reply_text(
        "✅ Изображение получено! Теперь нажмите «Завершить» для сохранения сборки.",
        reply_markup=ReplyKeyboardMarkup([["Завершить"]], resize_keyboard=True)
    )
    return CONFIRMATION

async def confirm_build(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("✅ confirm_build ВЫЗВАН")
    print("🛠 Сохраняем в:", DB_PATH)
    # Готовим данные новой сборки из введённых пользователем
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
    logging.info("[ADD] ➤ confirm_build triggered, new_build = %r", new_build)

    try:
        # Убеждаемся, что директория для builds.json существует
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        logging.info("[ADD] DB_PATH = %s", DB_PATH)

        # Загружаем существующие записи, если файл есть
        if DB_PATH.exists():
            existing_data = json.loads(DB_PATH.read_text(encoding="utf-8"))
        else:
            existing_data = []
        logging.info("[ADD] before save: %d records", len(existing_data))

        # Добавляем новую сборку и записываем обратно
        existing_data.append(new_build)
        DB_PATH.write_text(json.dumps(existing_data, indent=2, ensure_ascii=False), encoding="utf-8")
        logging.info("[ADD] write_text succeeded")

        # Перечитываем данные для проверки сохранения
        updated_data = json.loads(DB_PATH.read_text(encoding="utf-8"))
        logging.info("[ADD] after save: %d records, last entry = %r", len(updated_data), updated_data[-1])

    except Exception:
        logging.exception("[ADD] ❌ saving failed")
        await update.message.reply_text("❌ Внутренняя ошибка при сохранении данных. Попробуйте ещё раз позже.")
        return ConversationHandler.END

    # Подтверждаем успешное сохранение и предлагаем следующий шаг
    await update.message.reply_text(
        "✅ Сборка успешно добавлена! Что вы хотите сделать дальше?",
        reply_markup=ReplyKeyboardMarkup(
            [["➕ Добавить ещё одну сборку"], ["◀ Отмена"]],
            resize_keyboard=True
        )
    )
    return POST_CONFIRM

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Прерывание диалога в любой момент
    await update.message.reply_text("❌ Отменено. Добавление новой сборки прервано.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# Настройка ConversationHandler с указанием состояний и переходов
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
            MessageHandler(filters.Regex("^➕ Добавить ещё одну сборку$"), add_start),
            MessageHandler(filters.Regex("^◀ Отмена$"), cancel)
        ]
    },
    fallbacks=[CommandHandler("cancel", cancel)]
)
