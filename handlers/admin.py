import os
import json
import subprocess
import logging
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
        result = subprocess.run(["systemctl", "is-active", "ndsborki.service"], capture_output=True, text=True)
        service_status = result.stdout.strip()
    except Exception as e:
        service_status = f"⚠️ Ошибка при проверке systemd: {e}"

    total = len(data)
    formatted_time = datetime.fromtimestamp(os.path.getmtime(DB_PATH)).strftime("%d.%m.%Y %H:%M")

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
        result = subprocess.run(
            ["journalctl", "-u", "ndsborki.service", "-n", "30", "--no-pager"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        logs = result.stdout.strip() or result.stderr.strip()
        if not logs:
            logs = "⚠️ Логи пусты или недоступны."

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"📄 <b>Последние 30 строк лога:</b>\n<pre>{logs}</pre>",
            parse_mode="HTML"
        )
        await update.message.reply_text("📤 Логи отправлены в админский канал.")
    except Exception as e:
        await update.message.reply_text("❌ Не удалось получить логи.")
        logging.exception("Ошибка при получении логов")


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
        if os.path.exists(path):
            msg_lines.append(f"✅ {key}: <code>{fname}</code> — найден")
        else:
            msg_lines.append(f"❌ {key}: <code>{fname}</code> — отсутствует")

    await update.message.reply_text("\n".join(msg_lines), parse_mode="HTML")


@admin_only
async def restart_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    context.user_data.clear()
    await update.message.reply_text("🔄 Бот перезапускается...\n⏳ Пожалуйста, подождите пару секунд...")

    with open("restarted_by.txt", "w") as f:
        f.write(f"{user.full_name} (ID: {user.id})")

    with open("restart_message.txt", "w") as f:
        f.write(str(user.id))

    os._exit(0)


# 📦 Экспортируем как список
admin_handlers = [
    CommandHandler("status", status_command),
    CommandHandler("log", get_logs),
    CommandHandler("check_files", check_files),
    CommandHandler("restart", restart_bot)
]
