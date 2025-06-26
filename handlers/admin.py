import os
import json
import logging
import asyncio
from collections import Counter
from datetime import datetime
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from utils.permissions import admin_only
from utils.keyboards import get_main_menu

DB_PATH = "database/builds.json"
ADMIN_ID = int(os.getenv("ADMIN_ID"))


@admin_only
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not os.path.exists(DB_PATH):
        await update.message.reply_text("❌ База данных отсутствует.")
        return

    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при чтении БД: {e}")
        return

    try:
        proc = await asyncio.create_subprocess_exec(
            "systemctl", "is-active", "ndsborki.service",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, err = await proc.communicate()
        service_status = (out or err).decode().strip()
    except Exception as e:
        service_status = f"⚠️ Ошибка при проверке systemd: {e}"

    total = len(data)
    formatted_time = datetime.fromtimestamp(
        os.path.getmtime(DB_PATH)
    ).strftime("%d.%m.%Y %H:%M")

    authors = Counter(b.get("author", "—") for b in data)
    categories = Counter(b.get("category", "—") for b in data)

    msg = [
        f"🖥 <b>Состояние сервиса:</b> <code>{service_status}</code>",
        f"📦 <b>Всего сборок:</b> <code>{total}</code>",
        f"📅 <b>Обновлено:</b> <code>{formatted_time}</code>",
        "",
        "👥 <b>Авторы:</b>"
    ]
    msg += [f"• <b>{name}</b> — <code>{count}</code>" for name, count in authors.most_common()]

    if categories:
        msg.append("\n📁 <b>Категории сборок:</b>")
        msg += [f"• <b>{cat}</b> — <code>{count}</code>" for cat, count in categories.items()]

    await update.message.reply_text("\n".join(msg), parse_mode="HTML")


@admin_only
async def get_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        proc = await asyncio.create_subprocess_exec(
            "journalctl", "-u", "ndsborki.service", "-n", "30", "--no-pager",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, err = await proc.communicate()
        logs = (out or err).decode().strip() or "⚠️ Логи пусты или недоступны."

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"📄 <b>Последние 30 строк лога:</b>\n<pre>{logs}</pre>",
            parse_mode="HTML"
        )
        await update.message.reply_text("📤 Логи отправлены в админский канал.")
    except Exception:
        logging.exception("Ошибка при получении логов")
        await update.message.reply_text("❌ Не удалось получить логи.")


@admin_only
async def check_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    msg_lines = ["🔍 Проверка файлов в /database:"]
    for key, fname in file_map.items():
        path = f"database/{fname}"
        status = "найден" if os.path.exists(path) else "отсутствует"
        icon = "✅" if status == "найден" else "❌"
        msg_lines.append(f"{icon} {key}: <code>{fname}</code> — {status}")

    await update.message.reply_text("\n".join(msg_lines), parse_mode="HTML")


@admin_only
async def restart_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    kb = get_main_menu(user.id)

    # Сообщаем о перезапуске
    await update.message.reply_text(
        "🔄 Бот перезапускается…",
        reply_markup=kb
    )

    # Сохраняем ID для уведомления об успешном рестарте
    with open("restart_message.txt", "w", encoding="utf-8") as f:
        f.write(str(user.id))

    # Завершаем процесс — systemd поднимет бот заново
    os._exit(0)


# 📦 Экспортируем как список
admin_handlers = [
    CommandHandler("status", status_command),
    CommandHandler("log", get_logs),
    CommandHandler("check_files", check_files),
    CommandHandler("restart", restart_bot)
]
