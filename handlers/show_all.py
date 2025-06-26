# handlers/show_all.py

import os
import json
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

ROOT    = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(ROOT, "database", "builds.json")

# Ширина одной «колонки» в символах
COL_WIDTH = 30

async def show_all_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1) Читаем файл
    if not os.path.exists(DB_PATH):
        return await update.message.reply_text("ℹ️ Список сборок пуст.")
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return await update.message.reply_text(f"❌ Ошибка чтения builds.json: {e}")
    if not data:
        return await update.message.reply_text("ℹ️ Список сборок пуст.")

    # 2) Сообщаем заголовок
    await update.message.reply_text("📄 <b>Все сборки:</b>\n", parse_mode="HTML")

    # 3) Разбиваем на пары по 2
    pairs = [data[i:i+2] for i in range(0, len(data), 2)]

    for pair in pairs:
        # Для каждой сборки строим массив строк
        panels = [format_panel(idx + 1 + offset, b)
                  for offset, b in enumerate(pair, start=pairs.index(pair)*2)]
        # Обеспечим одинаковую длину (5 строк)
        for p in panels:
            while len(p) < 5:
                p.append("")

        # Скомпонуем по строкам
        lines = []
        for i in range(5):
            left = panels[0][i].ljust(COL_WIDTH)
            right = panels[1][i] if len(panels) > 1 else ""
            lines.append(f"{left}    {right}")

        text = "<pre>" + "\n".join(lines) + "</pre>"
        await update.message.reply_text(text, parse_mode="HTML")

def format_panel(number: int, b: dict) -> list[str]:
    """
    Возвращает 5 строк для одной сборки:
    0) "1. Название"
    1) "├ 📏 Дистанция: …"
    2) "├ ⚙️ Тип: …"
    3) "├ 🔩 Модулей: …"
    4) "└ 👤 Автор: …"
    """
    nm   = b.get("weapon_name", "—")
    role = b.get("role", "-")
    typ  = b.get("type", "—")
    cnt  = len(b.get("modules", {}))
    auth = b.get("author", "—")

    return [
        f"{number}. {nm}",
        f"├ 📏 Дистанция: {role}",
        f"├ ⚙️ Тип: {typ}",
        f"├ 🔩 Модулей: {cnt}",
        f"└ 👤 Автор: {auth}"
    ]

show_all_handler = CommandHandler("show_all", show_all_command)
