import logging
import os
from logging.handlers import RotatingFileHandler

def configure_logging():
    os.makedirs("logs", exist_ok=True)

    info_handler = RotatingFileHandler("logs/info.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    info_handler.setLevel(logging.INFO)
    info_handler.addFilter(lambda record: record.levelno < logging.WARNING)

    error_handler = RotatingFileHandler("logs/error.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    error_handler.setLevel(logging.WARNING)

    logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
