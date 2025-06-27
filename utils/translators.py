import json
import pathlib
import logging
from functools import lru_cache

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
DB_DIR = ROOT / "database"

# Маппинг ключей оружия на файлы переводов модулей
FILE_MAP = {
    "assault":  "modules-assault.json",
    "battle":   "modules-battle.json",
    "smg":      "modules-pp.json",
    "shotgun":  "modules-drobovik.json",
    "marksman": "modules-pehotnay.json",
    "lmg":      "modules-pulemet.json",
    "sniper":   "modules-snayperki.json",
    "pistol":   "modules-pistolet.json",
    "special":  "modules-osoboe.json",
}

@lru_cache(maxsize=None)
def load_translation_dict(weapon_key: str) -> dict:
    """
    Загружает и кэширует JSON-файл переводов для заданного типа оружия.
    Возвращает словарь {английское имя модуля: русское имя}.
    """
    filename = FILE_MAP.get(weapon_key)
    if not filename:
        logging.warning(f"⚠️ Нет файла перевода для weapon_key='{weapon_key}'")
        return {}

    path = DB_DIR / filename
    if not path.exists():
        logging.warning(f"⚠️ Файл модуля не найден: {path}")
        return {}

    try:
        with path.open("r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except Exception as e:
        logging.warning(f"❌ Ошибка загрузки перевода из {path}: {e}")
        return {}

    # raw_data: { category: [ { "en": "...", "ru": "..." }, ... ], ... }
    # Собираем один плоский словарь en→ru
    translations = {}
    for variants in raw_data.values():
        for entry in variants:
            en = entry.get("en")
            ru = entry.get("ru")
            if en and ru:
                translations[en] = ru

    return translations

@lru_cache(maxsize=None)
def get_type_label_by_key(types_dict: dict, key: str) -> str:
    """
    Возвращает ярлык (label) типа оружия по его ключу из заранее загруженного словаря types_dict.
    Если ключ не найден, возвращает сам ключ.
    """
    return types_dict.get(key, key)
