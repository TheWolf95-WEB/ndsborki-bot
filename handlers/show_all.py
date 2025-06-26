# handlers/show_all.py

import os
import json
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

# Путь до корня проекта и файла сборок
ROOT    = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(ROOT, "database", "builds.json")

# Эмодзи для элементов
EMOJI_WEAPON   = "🔫"
EMOJI_CATEGORY = "📁"
EMOJI_TYPE     = "🛠"
EMOJI_MODULES  = "🔩"
EMOJI_AUTHOR   = "👤"

# Ширина колонки (символов)
COL_WIDTH = 36

async def show_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1) Загружаем JSON
    try:
        with open(DB_PATH, encoding="utf-8") as f:
            builds = json.load(f)
    except Exception as e:
        return await update.message.reply_text(f"❌ Не удалось загрузить builds.json: {e}")

    if not builds:
        return await update.message.reply_text("ℹ️ В базе пока нет ни одной сборки.")

    # 2) Разбиваем на пары по две сборки
    pairs = [builds[i:i+2] for i in range(0, len(builds), 2)]

    # 3) Для каждой пары формируем <pre>-блок
    for pair in pairs:
        # Получаем текстовые строки для левой и (опционально) правой колонок
        left = format_build(pair[0])
        right = format_build(pair[1]) if len(pair) > 1 else [""] * 4

        # Убедимся, что у каждого по 4 строки
        while len(left) < 4:   left.append("")
        while len(right) < 4:  right.append("")

        # Собираем итоговый текст
        lines = []
        for l, r in zip(left, right):
            # Обрезаем и выравниваем левую колонку
            l = (l[:COL_WIDTH-3] + "...") if len(l) > COL_WIDTH else l
            l = l.ljust(COL_WIDTH)
            lines.append(f"{l}  {r}")

        text = "<pre>" + "\n".join(lines) + "</pre>"
        await update.message.reply_text(text, parse_mode="HTML")

def format_build(b: dict) -> list[str]:
    """
    Возвращает список из 4 строк для одной сборки:
      0: 🔫 Название
      1: 📁 Категория | 🛠 Тип | 🔩N
      2: (список модулей не выводим здесь, слишком много)
      3: 👤 Автор
    """
    name = b.get("weapon_name", "—")
    cat  = b.get("category",     "—")
    typ  = b.get("type",         "—")
    cnt  = len(b.get("modules", {}))
    auth = b.get("author",      "—")

    line0 = f"{EMOJI_WEAPON} <b>{name}</b>"
    line1 = f"{EMOJI_CATEGORY} {cat} | {EMOJI_TYPE} {typ} | {EMOJI_MODULES} {cnt}"
    line2 = ""  # можно сюда вкратце перечислить, но я оставил пустым
    line3 = f"{EMOJI_AUTHOR} {auth}"

    return [line0, line1, line2, line3]

show_all_handler = CommandHandler("show_all", show_all)
