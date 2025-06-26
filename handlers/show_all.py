# handlers/show_all.py

import os
import json
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

# Путь до файла сборок
ROOT    = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(ROOT, "database", "builds.json")

# Эмодзи
E_GIFT     = "📦"
E_WEAPON   = "🔫"
E_TYPE     = "⚙️"
E_CATEGORY = "📁"
E_MODULES  = "🔩"
E_AUTHOR   = "👤"

async def show_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1) Загрузка БД
    try:
        with open(DB_PATH, encoding="utf-8") as f:
            builds = json.load(f)
    except Exception as e:
        return await update.message.reply_text(f"❌ Не удалось открыть builds.json: {e}")

    if not builds:
        return await update.message.reply_text("ℹ️ В базе ещё нет сборок.")

    # 2) Заголовок
    await update.message.reply_text(f"{E_GIFT} <b>Все сохранённые сборки:</b>\n", parse_mode="HTML")

    # 3) Разбиваем на пары по две сборки
    pairs = [builds[i:i+2] for i in range(0, len(builds), 2)]

    for pair in pairs:
        parts = []
        for b in pair:
            # Собираем HTML блок одной сборки
            name = b.get("weapon_name", "—")
            typ  = b.get("type",        "—")
            cat  = b.get("category",    "—")
            cnt  = len(b.get("modules", {}))
            auth = b.get("author",      "—")

            block = (
                f"{E_WEAPON} <b>{name}</b>\n"
                f"{E_TYPE} Тип: <i>{typ}</i>\n"
                f"{E_CATEGORY} Категория: <i>{cat}</i>\n"
                f"{E_MODULES} Модули: <b>{cnt}</b>\n"
                f"{E_AUTHOR} {auth}"
            )
            parts.append(block)

        # Если парная — выводим две колонки через табуляцию
        if len(parts) == 2:
            left, right = parts
            # простейшая разбивка: соединяем по строкам
            left_lines  = left.split("\n")
            right_lines = right.split("\n")
            # соберём максимум по 5 строк
            rows = max(len(left_lines), len(right_lines))
            combined = []
            for i in range(rows):
                L = left_lines[i]  if i < len(left_lines) else ""
                R = right_lines[i] if i < len(right_lines) else ""
                combined.append(f"{L:40}    {R}")
            text = "\n".join(combined)
            await update.message.reply_text(f"<pre>{text}</pre>", parse_mode="HTML")
        else:
            # Только одна колонка
            await update.message.reply_text(parts[0], parse_mode="HTML")

        # Разделитель между «строками» таблицы
        await update.message.reply_text("─" * 40)

show_all_handler = CommandHandler("show_all", show_all)
