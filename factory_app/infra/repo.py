
import os, json
from typing import Optional, Dict, Any, Tuple, List
from .logging_conf import get_logger

LOGGER = get_logger(__name__)

SETTINGS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "settings.json")

def load_settings() -> Dict[str, Any]:
    if not os.path.exists(SETTINGS_PATH):
        return {}
    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {}

def save_settings(settings: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

def monthly_state_path(type_name: str, year: int, month: int, machine: str) -> str:
    safe_type = type_name.replace("/", "_")
    safe_machine = machine.replace("/", "_")
    root = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage")
    os.makedirs(root, exist_ok=True)
    fname = f"{safe_type}_{year}-{month:02d}_{safe_machine}.json"
    return os.path.join(root, fname)

def load_monthly_state(type_name: str, year: int, month: int, machine: str) -> Optional[Dict[str, Any]]:
    path = monthly_state_path(type_name, year, month, machine)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)

def save_monthly_state(type_name: str, year: int, month: int, machine: str, data: Dict[str, Any]) -> str:
    path = monthly_state_path(type_name, year, month, machine)
    with open(path, "w", encoding="utf-8-sig") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    LOGGER.info(f"Saved monthly state -> {path}")
    return path

def peek_excel_path_for_month(type_name: str, year: int, month: int) -> Optional[str]:
    """参照時に使用：未設定なら None を返す"""
    settings = load_settings()
    key = f"{type_name}_{year}_{month}"
    return settings.get(key)

def set_excel_path_for_month(type_name: str, year: int, month: int, path: str) -> None:
    settings = load_settings()
    key = f"{type_name}_{year}_{month}"
    settings[key] = path
    save_settings(settings)
    LOGGER.info(f"Excel path set: {key} -> {path}")

def default_items(type_name: str) -> List[str]:
    # 実運用に合わせて更新可。ここは最低限のデフォルト。
    if "保全" in type_name:
        return ["電源ランプ確認", "異音チェック", "清掃状態", "安全ガード", "油漏れ"]
    # 始業前点検など
    return ["非常停止スイッチ", "ローラー異物", "周囲安全", "表示警告", "動作試運転"]
