"""
配置管理：bili2text路径、Cookie、调试日志等
"""
import json
import sys
from pathlib import Path

if getattr(sys, 'frozen', False):
    # EXE 在 dist/ 下，上溯一级即项目根目录
    CONFIG_DIR = Path(sys.executable).parent.parent / "config"
else:
    CONFIG_DIR = Path(__file__).parent.parent / "config"

SETTINGS_FILE = CONFIG_DIR / "settings.json"

DEFAULTS = {
    "bili2text_dir": "D:\\bili2text",
    "cookie_file": "D:\\bili2text\\.b2t\\cookies.txt",
    "debug_log": "",
    "llm_provider": "deepseek",
    "llm_api_key": "",
    "llm_model": "deepseek-chat",
    "valley_scheduler_enabled": "true",
    "batch_save_path": "",
    # ── 邮件通知 ──
    "email_enabled": "false",
    "email_smtp_server": "smtp.qq.com",
    "email_smtp_port": "465",
    "email_sender": "",
    "email_auth_code": "",
    "email_receiver": "",
}


def load_settings():
    """加载配置，缺失键回退到默认值"""
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)
    except Exception as e:
        import traceback
        err_log = CONFIG_DIR / "_load_error.log"
        try:
            with open(err_log, 'w', encoding='utf-8') as ef:
                ef.write(f"SETTINGS_FILE={SETTINGS_FILE}\nERROR={e}\n")
                traceback.print_exc(file=ef)
        except Exception:
            pass
        data = {}
    merged = {}
    for key in DEFAULTS:
        val = data.get(key)
        merged[key] = val if val is not None else DEFAULTS[key]
    return merged


def save_settings(settings: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


def get_setting(key: str):
    return load_settings().get(key, DEFAULTS.get(key, ""))


def set_setting(key: str, value: str):
    settings = load_settings()
    settings[key] = value
    save_settings(settings)


def get_bili2text_path():
    return Path(get_setting("bili2text_dir"))


def get_debug_log_path():
    p = get_setting("debug_log")
    if p:
        return Path(p)
    return CONFIG_DIR / "debug.log"


def get_cookie_path():
    return get_setting("cookie_file")
