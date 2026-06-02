from app.ai.fake_client import FakeLLMClient
from app.ai.openai_compatible import OpenAICompatibleClient
from app.config import Settings, get_settings
from app.errors import ConfigurationError


def get_llm_client(settings: Settings | None = None):
    settings = settings or get_settings()
    if settings.llm_provider == "fake":
        return FakeLLMClient()
    if settings.llm_provider in {"openai", "openai-compatible"}:
        if not settings.openai_base_url or not settings.openai_api_key or not settings.model:
            raise ConfigurationError("OpenAI-compatible provider requires base URL, API key, and model")
        return OpenAICompatibleClient(settings.openai_base_url, settings.openai_api_key, settings.model)
    raise ConfigurationError(f"Unsupported LLM provider: {settings.llm_provider}")
