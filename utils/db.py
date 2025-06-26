import os
import json
import logging
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
DB_PATH = ROOT / "database" / "builds.json"


def load_db():
    if not os.path.exists(DB_PATH):
        return []
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.warning(f"❌ Ошибка загрузки БД: {e}")
        return []

def load_weapon_types():
    try:
        with open("database/types.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.warning(f"❌ Не удалось загрузить types.json: {e}")
        return []

def get_type_label_by_key(type_key: str) -> str:
    for item in load_weapon_types():
        if item["key"] == type_key:
            return item["label"]
    return type_key  # fallback
