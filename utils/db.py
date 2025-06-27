import json
import logging
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
DB_PATH = ROOT / "database" / "builds.json"

def load_db():
    """
    Каждый раз читает файл builds.json «с нуля»,
    возвращает актуальный список сборок.
    """
    if not DB_PATH.exists():
        return []
    try:
        with DB_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.warning(f"❌ Ошибка загрузки БД: {e}")
        return []

def load_weapon_types():
    """
    Каждый раз читает types.json,
    возвращает список типов оружия.
    """
    types_path = ROOT / "database" / "types.json"
    if not types_path.exists():
        return []
    try:
        with types_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.warning(f"❌ Не удалось загрузить types.json: {e}")
        return []

def get_type_label_by_key(type_key: str) -> str:
    """
    Возвращает ярлык типа оружия по его ключу.
    Если ключ не найден, возвращает сам ключ (fallback).
    """
    types_map = {item["key"]: item["label"] for item in load_weapon_types()}
    return types_map.get(type_key, type_key)
