import pytest

from harness.config import _api_key, _base_url, _default_model, _provider, Settings


def test_groq_is_selected_when_groq_key_exists(monkeypatch):
    monkeypatch.delenv("FORGE_PROVIDER", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert _provider() == "groq"
    assert _api_key("groq") == "groq-test-key"
    assert _base_url("groq") == "https://api.groq.com/openai/v1"
    assert _default_model("groq") == "openai/gpt-oss-20b"


def test_explicit_provider_wins_over_auto_detection(monkeypatch):
    monkeypatch.setenv("FORGE_PROVIDER", "openrouter")
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "router-test-key")

    assert _provider() == "openrouter"
    assert _api_key("openrouter") == "router-test-key"
    assert _base_url("openrouter") == "https://openrouter.ai/api/v1"


def test_openai_provider_defaults_are_available():
    assert _base_url("openai") == "https://api.openai.com/v1"
    assert _default_model("openai") == "gpt-4o-mini"


def test_invalid_provider_is_rejected():
    with pytest.raises(ValueError, match="Unsupported FORGE_PROVIDER"):
        Settings(
            provider="not-a-provider",
            model="test-model",
            api_key="test-key",
            base_url="https://example.com/v1",
        )
