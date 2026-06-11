from collections.abc import AsyncIterator

from fastapi.testclient import TestClient

from mimo_openai_proxy.app import create_app
from mimo_openai_proxy.config import Settings
from mimo_openai_proxy.errors import available_languages, message
from mimo_openai_proxy.mimo import normalize_expiry_ms, token_expiry_ms

app = create_app(Settings(api_keys=""))


class FakeMimoClient:
    async def close(self) -> None:
        return None

    async def chat(self, payload: dict[str, object]):
        from httpx import Response

        return Response(200, json={"model": payload["model"], "choices": []})

    def stream_chat(self, _payload: dict[str, object]):
        return FakeStream()


class FakeStream:
    async def __aenter__(self):
        return FakeStreamResponse()

    async def __aexit__(self, *_args: object) -> None:
        return None


class FakeStreamResponse:
    status_code = 200
    headers = {"content-type": "text/event-stream"}

    async def aiter_bytes(self) -> AsyncIterator[bytes]:
        yield b"data: {}\n\n"
        yield b"data: [DONE]\n\n"


def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_models() -> None:
    with TestClient(app) as client:
        response = client.get("/v1/models")

    assert response.status_code == 200
    assert response.json()["data"][0]["id"] == "mimo-auto"


def test_models_requires_api_key_when_configured() -> None:
    protected_app = create_app(Settings(api_keys="secret-key"))

    with TestClient(protected_app) as client:
        response = client.get("/v1/models")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_api_key"


def test_models_accepts_configured_api_key() -> None:
    protected_app = create_app(Settings(api_keys="secret-key"))

    with TestClient(protected_app) as client:
        response = client.get("/v1/models", headers={"Authorization": "Bearer secret-key"})

    assert response.status_code == 200


def test_error_messages_load_from_language_files() -> None:
    assert "zh-CN" in available_languages()
    assert message("invalid_api_key", "es") == "Clave de API no valida."
    assert message("invalid_api_key", "unknown") == "Invalid API key."


def test_chat_completion_forwards_request() -> None:
    with TestClient(app) as client:
        client.app.state.mimo = FakeMimoClient()
        response = client.post(
            "/v1/chat/completions",
            json={"model": "mimo-auto", "messages": [{"role": "user", "content": "Hello"}]},
        )

    assert response.status_code == 200
    assert response.json() == {"model": "mimo-auto", "choices": []}


def test_invalid_chat_request_returns_openai_error() -> None:
    with TestClient(app) as client:
        response = client.post("/v1/chat/completions", json={"model": "mimo-auto"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request_error"


def test_stream_chat_completion() -> None:
    with TestClient(app) as client:
        client.app.state.mimo = FakeMimoClient()
        with client.stream(
            "POST",
            "/v1/chat/completions",
            json={
                "model": "mimo-auto",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": True,
            },
        ) as response:
            content = response.read()

    assert response.status_code == 200
    assert b"data: [DONE]" in content


def test_token_expiry_accepts_top_level_milliseconds() -> None:
    assert normalize_expiry_ms(1_781_221_008_000) == 1_781_221_008_000


def test_token_expiry_accepts_jwt_seconds() -> None:
    jwt = "header.eyJleHAiOjE3ODEyMjEwMDh9.signature"

    assert token_expiry_ms(jwt) == 1_781_221_008_000
