"""
配置管理：bili2text路径、Cookie、调试日志等
"""
import json
import sys
import os
from pathlib import Path

if getattr(sys, 'frozen', False):
    CONFIG_DIR = Path(sys.executable).parent.parent / "config"
else:
    CONFIG_DIR = Path(__file__).parent.parent / "config"

SETTINGS_FILE = CONFIG_DIR / "settings.json"
KEY_FILE = CONFIG_DIR / ".fernet_key"

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
    # ── 飞书通知 ──
    "feishu_enabled": "false",
    "feishu_webhook": "https://open.feishu.cn/open-apis/bot/v2/hook/43afc324-86c7-41f7-b82c-4c9a5a2a0426",
    # ── 高峰弹窗不再提醒 ──
    "peak_skip_today": "",
}

# ── 加密敏感字段 ──
_SENSITIVE_KEYS = {"llm_api_key", "email_auth_code"}

def _get_cipher():
    """获取 Fernet 加密器，密钥持久化到 config/.fernet_key"""
    from cryptography.fernet import Fernet
    if KEY_FILE.exists():
        key = KEY_FILE.read_bytes()
    else:
        key = Fernet.generate_key()
        KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        KEY_FILE.write_bytes(key)
        # 限制权限（仅 Windows）
        try:
            import stat
            os.chmod(str(KEY_FILE), stat.S_IRUSR | stat.S_IWUSR)
        except Exception:
            pass
    return Fernet(key)


def _try_migrate_plaintext(data: dict) -> dict:
    """检测并迁移明文敏感字段 → Fernet 加密"""
    # 快速退出：无明文敏感字段
    has_plain = any(
        k in data and data[k] and not data[k].startswith("gAAAAA")
        for k in _SENSITIVE_KEYS
    )
    if not has_plain:
        return data

    cipher = _get_cipher()
    for k in _SENSITIVE_KEYS:
        val = data.get(k)
        if val and not val.startswith("gAAAAA"):
            data[k] = cipher.encrypt(val.encode("utf-8")).decode("utf-8")
    # 回写加密后的配置
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return data


# ── 缓存（#1：get_setting 加缓存）──
_settings_cache: dict | None = None


def load_settings():
    """加载配置，缺失键回退到默认值。自动迁移明文敏感字段。"""
    global _settings_cache
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

    # 自动迁移明文敏感字段
    data = _try_migrate_plaintext(data)

    merged = {}
    for key in DEFAULTS:
        val = data.get(key)
        merged[key] = val if val is not None else DEFAULTS[key]

    _settings_cache = merged
    return merged


def save_settings(settings: dict):
    """保存配置，同时失效缓存"""
    global _settings_cache
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
    _settings_cache = settings.copy()


def get_setting(key: str):
    """获取配置项（优先从缓存读取，加密字段自动解密）"""
    global _settings_cache
    if _settings_cache is None:
        load_settings()
    val = _settings_cache.get(key, DEFAULTS.get(key, ""))

    # 加密字段自动解密
    if key in _SENSITIVE_KEYS and val and val.startswith("gAAAAA"):
        try:
            return _get_cipher().decrypt(val.encode("utf-8")).decode("utf-8")
        except Exception:
            return val  # 解密失败返回密文（兼容异常）
    return val


def get_raw_setting(key: str):
    """获取配置项原始值（不解密），供 GUI 回显 """
    global _settings_cache
    if _settings_cache is None:
        load_settings()
    return _settings_cache.get(key, DEFAULTS.get(key, ""))


def set_setting(key: str, value: str):
    """写入配置项。敏感字段自动加密。"""
    global _settings_cache
    if _settings_cache is None:
        load_settings()

    store_value = value
    if key in _SENSITIVE_KEYS and value and not value.startswith("gAAAAA"):
        store_value = _get_cipher().encrypt(value.encode("utf-8")).decode("utf-8")

    _settings_cache[key] = store_value
    save_settings(_settings_cache)


def get_bili2text_path():
    return Path(get_setting("bili2text_dir"))


def get_debug_log_path():
    p = get_setting("debug_log")
    if p:
        return Path(p)
    return CONFIG_DIR / "debug.log"


def get_cookie_path():
    return get_setting("cookie_file")
