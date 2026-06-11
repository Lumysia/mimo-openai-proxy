import json
from functools import lru_cache
from importlib import resources
from typing import Literal

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse

ErrorCode = Literal[
    "invalid_api_key",
    "invalid_request_error",
    "upstream_error",
]

DEFAULT_LANGUAGE = "en"


class OpenAIError(HTTPException):
    def __init__(
        self,
        status_code: int,
        code: ErrorCode,
        message: str | None = None,
        error_type: str = "invalid_request_error",
    ) -> None:
        super().__init__(status_code=status_code, detail=message)
        self.code = code
        self.error_type = error_type


def message(code: ErrorCode, language: str) -> str:
    messages = locale_registry(language)["errors"]
    return messages.get(code, locale_registry(DEFAULT_LANGUAGE)["errors"][code])


@lru_cache
def locale_registry(language: str) -> dict[str, dict[str, str]]:
    normalized_language = language.replace("_", "-")
    if normalized_language not in available_languages():
        normalized_language = DEFAULT_LANGUAGE

    registry = resources.files("mimo_openai_proxy.locales").joinpath(f"{normalized_language}.json")
    return json.loads(registry.read_text(encoding="utf-8"))


@lru_cache
def available_languages() -> frozenset[str]:
    registry = resources.files("mimo_openai_proxy.locales")
    return frozenset(
        path.name.removesuffix(".json")
        for path in registry.iterdir()
        if path.name.endswith(".json")
    )


def openai_error_response(
    status_code: int,
    code: ErrorCode,
    message_text: str,
    error_type: str = "invalid_request_error",
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "message": message_text,
                "type": error_type,
                "param": None,
                "code": code,
            }
        },
    )


def upstream_error(detail: str | None = None) -> OpenAIError:
    return OpenAIError(
        status_code=status.HTTP_502_BAD_GATEWAY,
        code="upstream_error",
        message=detail,
        error_type="server_error",
    )
