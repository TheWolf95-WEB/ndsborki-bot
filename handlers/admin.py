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

# Путь до вашего репозитория
REPO_DIR = "/root/NDsborki"
GIT_REMOTE = "origin"
GIT_BRANCH = "main"

# КОМАНДА РЕСТАРТ
@admin_only
async def restart_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    kb = get_main_menu(user.id)

    # 1) Оповещаем о перезапуске бота
    await update.message.reply_text(
        "🔄 Перезапуск бота…",
        reply_markup=kb
    )

    # 2) Пытаемся подтянуть актуальный код из Git
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "pull", GIT_REMOTE, GIT_BRANCH,
            cwd=REPO_DIR,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        rc = await proc.wait()
    except Exception:
        await update.message.reply_text(
            "❌ Ошибка при обновлении кода.",
            reply_markup=kb
        )
        return

    if rc != 0:
        await update.message.reply_text(
            "❌ Ошибка при обновлении кода.",
            reply_markup=kb
        )
        return

    # 3) Успешно обновили — завершаем процесс для перезапуска
    os._exit(0)

restart_handler = CommandHandler("restart", restart_bot)

# КОМАНДА СТАТУС
@admin_only
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем БД
    if not os.path.exists(DB_PATH):
        await update.message.reply_text("❌ База данных отсутствует.")
        return

    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при чтении БД: {e}")
        return

    # Проверяем статус systemd
    try:
        proc = await asyncio.create_subprocess_exec(
            "/usr/bin/systemctl", "is-active", "ndsborki.service",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        out, err = await proc.communicate()
        service_status = (out or err).decode().strip()
    except Exception as e:
        service_status = f"⚠️ Ошибка при проверке systemd: {e}"

    # Статистика по сборкам
    total = len(data)
    authors = Counter(b.get("author", "—") for b in data)
    categories = Counter(b.get("category", "—") for b in data)

    # Информация о последнем коммите
    last_commit_time = "—"
    last_commit_files = []
    try:
        proc2 = await asyncio.create_subprocess_exec(
            "git", "-C", REPO_DIR,
            "log", "-1", "--format=%ci", "--name-only",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        out2, err2 = await proc2.communicate()
        text = (out2 or err2).decode().strip().splitlines()
        if text:
            last_commit_time = text[0]  # строка вида "2025-06-26 14:05:12 +0000"
            last_commit_files = [f for f in text[1:] if f]
    except Exception:
        logging.exception("Не удалось получить данные о последнем коммите")

    # Формируем сообщение
    msg = [
        f"🖥 <b>Состояние сервиса:</b> <code>{service_status}</code>",
        f"📦 <b>Всего сборок:</b> <code>{total}</code>",
        "",
        f"🕑 <b>Последний коммит:</b> <code>{last_commit_time}</code>"
    ]
    if last_commit_files:
        msg += ["📁 <b>Файлы в коммите:</b>"] + [f"• <code>{fn}</code>" for fn in last_commit_files]

    msg += [
        "",
        "👥 <b>Авторы:</b>"
    ] + [f"• <b>{name}</b> — <code>{count}</code>" for name, count in authors.most_common()]

    if categories:
        msg += [
            "",
            "📂 <b>Категории сборок:</b>"
        ] + [f"• <b>{cat}</b> — <code>{count}</code>" for cat, count in categories.items()]

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


# 📦 Экспортируем как список
admin_handlers = [
    CommandHandler("status", status_command),
    CommandHandler("log", get_logs),
    CommandHandler("check_files", check_files),
    CommandHandler("restart", restart_bot)
]
