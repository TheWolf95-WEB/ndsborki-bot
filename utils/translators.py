import json
import os
import logging

def load_translation_dict(weapon_key: str) -> dict:
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

    filename = file_map.get(weapon_key)
    if not filename:
        return {}

    path = f"database/{filename}"
    if not os.path.exists(path):
        logging.warning(f"⚠️ Файл модуля не найден: {path}")
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        return {v['en']: v['ru'] for variants in raw_data.values() for v in variants}
    except Exception as e:
        logging.warning(f"❌ Ошибка загрузки перевода: {e}")
        return {}

def get_type_label_by_key(types_dict: dict, key: str) -> str:
    return types_dict.get(key, key)
