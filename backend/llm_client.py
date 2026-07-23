"""
LLM 统一接口：支持 DeepSeek 和火山方舟（豆包）
"""
import json
import time
import urllib.request
import urllib.error
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


def _chat_with_retry(config: LLMConfig, url: str, prompt: str, max_retries: int = 3) -> str:
    """带指数退避重试的 LLM 调用"""
    body = json.dumps({
        "model": config.model,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(
                url, body,
                {"Authorization": f"Bearer {config.api_key}",
                 "Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            last_error = e
            if e.code >= 500 and attempt < max_retries:
                wait = 2 ** attempt
                time.sleep(wait)
                continue
            raise
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_error = e
            if attempt < max_retries:
                wait = 2 ** attempt
                time.sleep(wait)
                continue
            raise

    raise last_error  # type: ignore


def chat(prompt: str) -> str:
    """发送 prompt 到配置的 LLM，返回回复文本"""
    config = _get_config()
    if not config.api_key:
        raise ValueError("API Key 未配置，请在配置页设置")
    if config.provider == "volcengine":
        return _chat_with_retry(config,
            "https://ark.cn-beijing.volces.com/api/v3/chat/completions", prompt)
    return _chat_with_retry(config,
        "https://api.deepseek.com/v1/chat/completions", prompt)
