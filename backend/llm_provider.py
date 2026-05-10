from __future__ import annotations
import os
from typing import Optional

PROVIDER_CATALOG: dict = {
    "groq": {
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "models": [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
        ],
        "default_model": "llama-3.3-70b-versatile",
        "env_key": "GROQ_API_KEY",
        "json_mode": True,
    },
    "gemini": {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "models": ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
        "default_model": "gemini-2.0-flash",
        "env_key": "GEMINI_API_KEY",
        "json_mode": True,
    },
    "openai": {
        "name": "OpenAI",
        "base_url": None,
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
        "default_model": "gpt-4o",
        "env_key": "OPENAI_API_KEY",
        "json_mode": True,
    },
    "anthropic": {
        "name": "Anthropic",
        "base_url": None,
        "models": [
            "claude-opus-4-7",
            "claude-sonnet-4-6",
            "claude-haiku-4-5-20251001",
        ],
        "default_model": "claude-sonnet-4-6",
        "env_key": "ANTHROPIC_API_KEY",
        "json_mode": False,
    },
    "ollama": {
        "name": "Ollama (Local)",
        "base_url": "http://localhost:11434/v1",
        "models": ["llama3", "llama3.1", "mistral", "codellama", "phi3"],
        "default_model": "llama3",
        "env_key": None,
        "json_mode": True,
    },
}


def resolve_api_key(provider: str, provided_key: Optional[str]) -> str:
    if provided_key:
        return provided_key
    info = PROVIDER_CATALOG[provider]
    if info["env_key"] is None:
        return "ollama"
    key = os.getenv(info["env_key"], "")
    if not key:
        raise ValueError(
            f"No API key for {provider}. "
            f"Set {info['env_key']} in .env or provide it via the UI."
        )
    return key


def make_completion(
    provider: str,
    model: str,
    api_key: str,
    messages: list[dict],
    temperature: float = 0.5,
) -> str:
    """Unified chat completion. Returns raw text content."""
    if provider == "anthropic":
        return _anthropic_complete(model, api_key, messages, temperature)
    return _openai_compat_complete(provider, model, api_key, messages, temperature)


def _openai_compat_complete(
    provider: str,
    model: str,
    api_key: str,
    messages: list[dict],
    temperature: float,
) -> str:
    import time
    import logging
    from openai import OpenAI

    log = logging.getLogger("llm_provider")
    info = PROVIDER_CATALOG[provider]
    kwargs: dict = {"api_key": api_key}
    if info["base_url"]:
        kwargs["base_url"] = info["base_url"]
    client = OpenAI(**kwargs)

    extra: dict = {}
    if info["json_mode"]:
        extra["response_format"] = {"type": "json_object"}

    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                **extra,
            )
            return resp.choices[0].message.content
        except Exception as exc:
            last_exc = exc
            err = str(exc).lower()
            if any(k in err for k in ("rate", "429", "limit", "quota", "too many")):
                wait = (attempt + 1) * 10
                log.warning("Rate limit — retrying in %ds (attempt %d/3)", wait, attempt + 1)
                time.sleep(wait)
            else:
                raise
    raise last_exc


def _anthropic_complete(
    model: str,
    api_key: str,
    messages: list[dict],
    temperature: float,
) -> str:
    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)
    system_parts = [m["content"] for m in messages if m["role"] == "system"]
    user_messages = [m for m in messages if m["role"] != "system"]
    system = "\n\n".join(system_parts) if system_parts else "You are a helpful assistant."

    resp = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system,
        messages=user_messages,
        temperature=temperature,
    )
    return resp.content[0].text


def providers_status() -> list[dict]:
    """Return catalog entries enriched with whether an env key is present."""
    result = []
    for pid, info in PROVIDER_CATALOG.items():
        env_key = info["env_key"]
        has_env_key = bool(os.getenv(env_key, "")) if env_key else True
        result.append({
            "id": pid,
            "name": info["name"],
            "has_env_key": has_env_key,
            "models": info["models"],
            "default_model": info["default_model"],
        })
    return result
