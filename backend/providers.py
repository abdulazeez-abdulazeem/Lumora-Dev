"""
Lumora Dev – AI Provider Registry
Defines all supported AI providers, their connection parameters, and model-fetching logic.
"""

from pydantic import BaseModel, Field
from typing import Optional

# ── Provider definitions ────────────────────────────────────────────────────
class ProviderDef(BaseModel):
    """Static metadata for a provider — never contains secrets."""
    id: str
    name: str
    base_url: str = ""
    docs_url: str = ""
    key_env_var: str = ""          # e.g. "OPENAI_API_KEY"
    key_help_url: str = ""          # where the user can get a key
    supports_model_list: bool = False
    model_list_url: str = ""        # API endpoint to fetch available models
    model_list_key_header: str = "Authorization"
    model_list_key_prefix: str = "Bearer"
    icon: str = ""                  # emoji or SVG path
    models_fixed: list[str] = []    # fallback if model_list_url is empty


# ── All providers ───────────────────────────────────────────────────────────
PROVIDERS: dict[str, ProviderDef] = {
    "openrouter": ProviderDef(
        id="openrouter",
        name="OpenRouter",
        base_url="https://openrouter.ai/api/v1",
        docs_url="https://openrouter.ai/docs",
        key_env_var="OPENROUTER_API_KEY",
        key_help_url="https://openrouter.ai/keys",
        supports_model_list=True,
        model_list_url="https://openrouter.ai/api/v1/models",
        model_list_key_prefix="Bearer",
        icon="🔀",
    ),
    "openai": ProviderDef(
        id="openai",
        name="OpenAI",
        base_url="https://api.openai.com/v1",
        docs_url="https://platform.openai.com/docs",
        key_env_var="OPENAI_API_KEY",
        key_help_url="https://platform.openai.com/api-keys",
        supports_model_list=True,
        model_list_url="https://api.openai.com/v1/models",
        model_list_key_prefix="Bearer",
        icon="🧠",
    ),
    "google": ProviderDef(
        id="google",
        name="Google AI Studio",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        docs_url="https://ai.google.dev/docs",
        key_env_var="GOOGLE_API_KEY",
        key_help_url="https://aistudio.google.com/app/apikey",
        supports_model_list=False,
        models_fixed=[
            "gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash",
            "gemini-2.0-flash-lite", "gemini-1.5-flash", "gemini-1.5-pro",
        ],
        icon="🌐",
    ),
    "anthropic": ProviderDef(
        id="anthropic",
        name="Anthropic",
        base_url="https://api.anthropic.com/v1",
        docs_url="https://docs.anthropic.com",
        key_env_var="ANTHROPIC_API_KEY",
        key_help_url="https://console.anthropic.com/settings/keys",
        supports_model_list=False,
        models_fixed=[
            "claude-4-sonnet-20250514", "claude-4-opus-20250514",
            "claude-3.5-sonnet", "claude-3.5-haiku", "claude-3-opus",
        ],
        icon="🏔️",
    ),
    "groq": ProviderDef(
        id="groq",
        name="Groq",
        base_url="https://api.groq.com/openai/v1",
        docs_url="https://console.groq.com/docs",
        key_env_var="GROQ_API_KEY",
        key_help_url="https://console.groq.com/keys",
        supports_model_list=True,
        model_list_url="https://api.groq.com/openai/v1/models",
        model_list_key_prefix="Bearer",
        icon="⚡",
    ),
    "deepseek": ProviderDef(
        id="deepseek",
        name="DeepSeek",
        base_url="https://api.deepseek.com/v1",
        docs_url="https://platform.deepseek.com/docs",
        key_env_var="DEEPSEEK_API_KEY",
        key_help_url="https://platform.deepseek.com/api-keys",
        supports_model_list=False,
        models_fixed=["deepseek-chat", "deepseek-coder", "deepseek-reasoner"],
        icon="🔍",
    ),
    "mistral": ProviderDef(
        id="mistral",
        name="Mistral",
        base_url="https://api.mistral.ai/v1",
        docs_url="https://docs.mistral.ai",
        key_env_var="MISTRAL_API_KEY",
        key_help_url="https://console.mistral.ai/api-keys",
        supports_model_list=True,
        model_list_url="https://api.mistral.ai/v1/models",
        model_list_key_prefix="Bearer",
        icon="🌪️",
    ),
    "cohere": ProviderDef(
        id="cohere",
        name="Cohere",
        base_url="https://api.cohere.ai/v1",
        docs_url="https://docs.cohere.com",
        key_env_var="COHERE_API_KEY",
        key_help_url="https://dashboard.cohere.com/api-keys",
        supports_model_list=False,
        models_fixed=["command-r-plus", "command-r", "command", "command-light"],
        icon="🔗",
    ),
    "together": ProviderDef(
        id="together",
        name="Together AI",
        base_url="https://api.together.xyz/v1",
        docs_url="https://docs.together.ai",
        key_env_var="TOGETHER_API_KEY",
        key_help_url="https://api.together.xyz/settings/api-keys",
        supports_model_list=True,
        model_list_url="https://api.together.xyz/v1/models",
        model_list_key_prefix="Bearer",
        icon="🤝",
    ),
    "fireworks": ProviderDef(
        id="fireworks",
        name="Fireworks AI",
        base_url="https://api.fireworks.ai/inference/v1",
        docs_url="https://docs.fireworks.ai",
        key_env_var="FIREWORKS_API_KEY",
        key_help_url="https://fireworks.ai/account/api-keys",
        supports_model_list=True,
        model_list_url="https://api.fireworks.ai/inference/v1/models",
        model_list_key_prefix="Bearer",
        icon="🎆",
    ),
    "ollama": ProviderDef(
        id="ollama",
        name="Ollama (Local)",
        base_url="http://localhost:11434/v1",
        docs_url="https://ollama.com",
        key_env_var="OLLAMA_API_KEY",
        key_help_url="",
        supports_model_list=True,
        model_list_url="http://localhost:11434/api/tags",
        model_list_key_header="",
        model_list_key_prefix="",
        icon="🦙",
    ),
    "lmstudio": ProviderDef(
        id="lmstudio",
        name="LM Studio (Local)",
        base_url="http://localhost:1234/v1",
        docs_url="https://lmstudio.ai",
        key_env_var="LMSTUDIO_API_KEY",
        key_help_url="",
        supports_model_list=False,
        models_fixed=["local-model"],
        icon="💻",
    ),
}


# ── Helpers ─────────────────────────────────────────────────────────────────
def get_provider(provider_id: str) -> Optional[ProviderDef]:
    """Return a provider definition by ID, or None."""
    return PROVIDERS.get(provider_id)


def list_providers() -> list[ProviderDef]:
    """Return all provider definitions as a list."""
    return list(PROVIDERS.values())
