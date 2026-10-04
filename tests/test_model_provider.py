from harness.config import Settings
import harness.model as model_module


class FakeCompletions:
    def __init__(self):
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return type(
            "Response",
            (),
            {"choices": [type("Choice", (), {"message": "fake-message"})()]},
        )()


class FakeOpenAI:
    last = None

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.chat = type("Chat", (), {"completions": FakeCompletions()})()
        FakeOpenAI.last = self


def test_model_uses_provider_endpoint_and_key(monkeypatch):
    monkeypatch.setattr(model_module, "OpenAI", FakeOpenAI)

    settings = Settings(
        provider="groq",
        model="openai/gpt-oss-20b",
        api_key="groq-test-key",
        base_url="https://api.groq.com/openai/v1",
    )
    model = model_module.Model(settings)

    assert FakeOpenAI.last.kwargs == {
        "api_key": "groq-test-key",
        "base_url": "https://api.groq.com/openai/v1",
    }
    assert model.model == "openai/gpt-oss-20b"


def test_model_sends_openai_compatible_tool_call_request(monkeypatch):
    monkeypatch.setattr(model_module, "OpenAI", FakeOpenAI)

    settings = Settings(
        provider="groq",
        model="openai/gpt-oss-20b",
        api_key="groq-test-key",
        base_url="https://api.groq.com/openai/v1",
    )
    model = model_module.Model(settings)

    tools = [{"type": "function", "function": {"name": "list_files"}}]
    result = model.complete(
        [{"role": "user", "content": "inspect the repository"}],
        tools,
    )

    assert result == "fake-message"
    request = FakeOpenAI.last.chat.completions.kwargs
    assert request["model"] == "openai/gpt-oss-20b"
    assert request["tools"] == tools
    assert request["tool_choice"] == "auto"
    assert request["temperature"] == 0.1


def test_model_error_names_configured_provider(monkeypatch):
    monkeypatch.setattr(model_module, "OpenAI", FakeOpenAI)

    settings = Settings(
        provider="groq",
        model="openai/gpt-oss-20b",
        api_key="",
        base_url="https://api.groq.com/openai/v1",
    )

    try:
        model_module.Model(settings)
    except RuntimeError as exc:
        assert "groq" in str(exc)
    else:
        raise AssertionError("Model should reject an empty API key")
