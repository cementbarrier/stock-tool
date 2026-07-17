"""
LLM 统一接口：支持 DeepSeek 和火山方舟（豆包）
"""
import json
import urllib.request
from dataclasses import dataclass


@dataclass
class LLMConfig:
    provider: str   # "deepseek" | "volcengine"
    api_key: str
    model: str


def _get_config() -> LLMConfig:
    try:
        from backend.config_manager import get_setting
        return LLMConfig(
            provider=get_setting("llm_provider") or "deepseek",
            api_key=get_setting("llm_api_key") or "",
            model=get_setting("llm_model") or "deepseek-chat",
        )
    except Exception:
        return LLMConfig(provider="deepseek", api_key="", model="deepseek-chat")


def chat(prompt: str) -> str:
    """发送 prompt 到配置的 LLM，返回回复文本"""
    config = _get_config()
    if not config.api_key:
        raise ValueError("API Key 未配置，请在配置页设置")
    if config.provider == "volcengine":
        return _volcengine_chat(config, prompt)
    return _deepseek_chat(config, prompt)


def _deepseek_chat(config: LLMConfig, prompt: str) -> str:
    body = json.dumps({
        "model": config.model,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.deepseek.com/v1/chat/completions",
        body,
        {"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"]


def _volcengine_chat(config: LLMConfig, prompt: str) -> str:
    body = json.dumps({
        "model": config.model,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
        body,
        {"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"]
