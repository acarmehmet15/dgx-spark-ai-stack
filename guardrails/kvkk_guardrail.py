"""
KVKK Guardrail — LiteLLM Gateway Seviyesinde PII & Secret Maskeleme
───────────────────────────────────────────────────────────────────
Tüm LLM trafiğini gateway seviyesinde filtreler.
Input (pre_call) ve Output (post_call) için çalışır.
KVKK (Kişisel Verilerin Korunması Kanunu) uyumluluğu.
"""

import logging
import re

import litellm
from litellm.integrations.custom_guardrail import CustomGuardrail

logger = logging.getLogger(__name__)

MASK_CHAR = "*"

# ─── Gizli Bilgi Kalıpları ───

SECRET_PATTERNS: list[tuple[str, str]] = [
    (r"sk-ant-[a-zA-Z0-9\-_]{20,}", "ANTHROPIC_API_KEY"),
    (r"sk-[a-zA-Z0-9]{20,}", "OPENAI_API_KEY"),
    (r"ghp_[a-zA-Z0-9]{36,}", "GITHUB_TOKEN"),
    (r"gho_[a-zA-Z0-9]{36,}", "GITHUB_OAUTH_TOKEN"),
    (r"github_pat_[a-zA-Z0-9_]{22,}", "GITHUB_PAT"),
    (r"glpat-[a-zA-Z0-9\-_]{20,}", "GITLAB_TOKEN"),
    (r"xoxb-[a-zA-Z0-9\-]{20,}", "SLACK_BOT_TOKEN"),
    (r"xoxp-[a-zA-Z0-9\-]{20,}", "SLACK_USER_TOKEN"),
    (r"AKIA[0-9A-Z]{16}", "AWS_ACCESS_KEY"),
    (r"AIza[0-9A-Za-z\-_]{35}", "GOOGLE_API_KEY"),
    (r"ya29\.[0-9A-Za-z\-_]+", "GOOGLE_OAUTH_TOKEN"),
    (r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"]?[^\s'\"]{8,}['\"]?", "PASSWORD"),
    (r"(?i)(secret|token|key|apikey|api_key)\s*[:=]\s*['\"]?[^\s'\"]{8,}['\"]?", "SECRET_ASSIGNMENT"),
    (r"(?i)(mongodb|postgres|mysql|redis)://[^\s]+", "DATABASE_URI"),
    (r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----", "PRIVATE_KEY"),
    (r"eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}", "JWT_TOKEN"),
    (r"(?i)bearer\s+[a-zA-Z0-9\-_.~+/]+=*", "BEARER_TOKEN"),
]

# ─── KVK Kalıpları (KVKK) ───

PII_PATTERNS: list[tuple[str, str]] = [
    (r"\b[1-9]\d{10}\b", "TC_KIMLIK_NO"),
    (r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b", "EMAIL"),
    (r"\b(?:\+90|0090|0)\s?[2-5]\d{2}\s?\d{3}\s?\d{2}\s?\d{2}\b", "PHONE_TR"),
    (r"\b\+?\d{1,3}[\s-]?\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}\b", "PHONE"),
    (r"\bTR\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{2}\b", "IBAN_TR"),
    (r"\b[A-Z]{2}\d{2}\s?[\dA-Z]{4}\s?[\dA-Z]{4}\s?[\dA-Z]{4}\s?[\dA-Z]{0,4}\s?[\dA-Z]{0,4}\s?[\dA-Z]{0,2}\b", "IBAN"),
    (r"\b(?:\d{4}[\s-]?){3}\d{4}\b", "CREDIT_CARD"),
    (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "IP_ADDRESS"),
]


def _mask_secret(value: str) -> str:
    """İlk 4 karakteri göster, kalanını maskele."""
    if len(value) <= 4:
        return MASK_CHAR * len(value)
    return value[:4] + MASK_CHAR * (len(value) - 4)


def _mask_pii(value: str) -> str:
    """İlk 2 ve son 2 karakteri göster, arasını maskele."""
    if len(value) <= 6:
        return MASK_CHAR * len(value)
    return value[:2] + MASK_CHAR * (len(value) - 4) + value[-2:]


def sanitize_text(text: str) -> tuple[str, int]:
    """Metindeki secret ve PII kalıplarını maskeler.

    Returns:
        (temizlenmiş_metin, bulunan_hassas_öğe_sayısı)
    """
    findings = 0
    result = text

    for pattern, label in SECRET_PATTERNS:
        def replace_secret(match, lbl=label):
            nonlocal findings
            findings += 1
            logger.warning(f"[KVKK] Secret maskelendi: {lbl}")
            return _mask_secret(match.group())

        result = re.sub(pattern, replace_secret, result)

    for pattern, label in PII_PATTERNS:
        def replace_pii(match, lbl=label):
            nonlocal findings
            if MASK_CHAR * 4 in match.group():
                return match.group()
            findings += 1
            logger.warning(f"[KVKK] PII maskelendi: {lbl}")
            return _mask_pii(match.group())

        result = re.sub(pattern, replace_pii, result)

    return result, findings


def _sanitize_messages(messages: list[dict]) -> int:
    """Mesaj listesindeki tüm content alanlarını temizler."""
    total = 0
    for message in messages:
        content = message.get("content")
        if isinstance(content, str):
            sanitized, count = sanitize_text(content)
            if count > 0:
                message["content"] = sanitized
                total += count
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text = part.get("text", "")
                    sanitized, count = sanitize_text(text)
                    if count > 0:
                        part["text"] = sanitized
                        total += count
    return total


class KVKKGuardrail(CustomGuardrail):
    """LiteLLM gateway seviyesinde KVKK uyumlu PII ve secret maskeleme."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logger.info("[KVKK] Guardrail aktif — tüm trafik filtreleniyor")

    async def async_pre_call_hook(
        self, user_api_key_dict, cache, data: dict, call_type: str
    ):
        """LLM'e göndermeden ÖNCE input'u temizle."""
        messages = data.get("messages", [])
        count = _sanitize_messages(messages)
        if count > 0:
            logger.warning(
                f"[KVKK] INPUT: {count} hassas öğe maskelendi (call_type={call_type})"
            )
        return data

    async def async_post_call_success_hook(
        self, data: dict, user_api_key_dict, response
    ):
        """LLM yanıtını kullanıcıya göndermeden ÖNCE temizle."""
        if isinstance(response, litellm.ModelResponse):
            count = 0
            for choice in response.choices:
                content = getattr(choice.message, "content", None)
                if content and isinstance(content, str):
                    sanitized, c = sanitize_text(content)
                    if c > 0:
                        choice.message.content = sanitized
                        count += c
            if count > 0:
                logger.warning(
                    f"[KVKK] OUTPUT: {count} hassas öğe maskelendi"
                )
