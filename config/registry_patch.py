"""
Ollama provider desteği — SDLCAgents model registry'sine monkey-patch.
Container başlangıcında yüklenir.
"""

import os
import src.models.registry as registry
from agno.models.openai import OpenAIChat

# Ollama modellerini desteklenen listesine ekle
registry.SUPPORTED_MODELS["ollama"] = [
    "deepseek-r1:70b",
    "gpt-oss:120b",
    "gpt-oss:20b",
    "qwen2.5-coder:32b-instruct-q8_0",
    "qwen2.5-coder:32b",
]

registry.DEFAULT_MODELS["ollama"] = "deepseek-r1:70b"

# Orijinal create_model fonksiyonunu genişlet
_original_create_model = registry.create_model


def _patched_create_model(provider: str, model_id: str | None = None):
    if provider.lower() == "ollama":
        if model_id is None:
            model_id = registry.DEFAULT_MODELS["ollama"]
        ollama_base = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
        return OpenAIChat(
            id=model_id,
            base_url=f"{ollama_base}/v1",
            api_key="ollama",
        )
    return _original_create_model(provider, model_id)


registry.create_model = _patched_create_model
