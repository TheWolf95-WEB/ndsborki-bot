import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def configure_logging():
    logs_dir = Path(__file__).resolve().parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)

    info = RotatingFileHandler(logs_dir / "info.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    info.setLevel(logging.INFO)
    info.addFilter(lambda rec: rec.levelno < logging.WARNING)

    err = RotatingFileHandler(logs_dir / "error.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    err.setLevel(logging.WARNING)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[info, err]
    )
