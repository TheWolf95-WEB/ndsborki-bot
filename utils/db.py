import json
import logging
import pathlib
from functools import lru_cache

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
DB_PATH = ROOT / "database" / "builds.json"

@lru_cache(maxsize=1)
def load_db():
    """
    Загружает файл builds.json единожды и кэширует результат.
    При ошибке чтения возвращает пустой список.
    """
    if not DB_PATH.exists():
        return []
    try:
        with DB_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.warning(f"❌ Ошибка загрузки БД: {e}")
        return []

@lru_cache(maxsize=1)
def load_weapon_types():
    """
    Загружает файл types.json единожды и кэширует результат.
    При ошибке чтения возвращает пустой список.
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

@lru_cache(maxsize=None)
def get_type_label_by_key(type_key: str) -> str:
    """
    Возвращает ярлык типа оружия по его ключу.
    Если ключ не найден, возвращает сам ключ (fallback).
    """
    types_map = {item["key"]: item["label"] for item in load_weapon_types()}
    return types_map.get(type_key, type_key)
