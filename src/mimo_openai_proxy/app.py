from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import Settings, settings
from .errors import OpenAIError, message, openai_error_response
from .mimo import MimoClient


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str = Field(min_length=1)
    messages: list[dict[str, Any]] = Field(min_length=1)
    stream: bool = False


def create_app(app_settings: Settings = settings) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = app_settings
        app.state.mimo = MimoClient(app_settings)
        try:
            yield
        finally:
            await app.state.mimo.close()

    api = FastAPI(title=app_settings.app_name, lifespan=lifespan)

    if app_settings.allowed_cors_origins:
        api.add_middleware(
            CORSMiddleware,
            allow_origins=app_settings.allowed_cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @api.exception_handler(OpenAIError)
    async def openai_error_handler(_request: Request, exc: OpenAIError) -> JSONResponse:
        return openai_error_response(
            status_code=exc.status_code,
            code=exc.code,
            message_text=exc.detail or message(exc.code, app_settings.error_language),
            error_type=exc.error_type,
    )

    @api.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return openai_error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="invalid_request_error",
            message_text=str(exc),
        )

    @api.exception_handler(StarletteHTTPException)
    async def http_error_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return openai_error_response(
            status_code=exc.status_code,
            code="invalid_request_error",
            message_text=str(exc.detail),
        )

    api.get("/health")(health)
    api.get("/v1/models")(list_models)
    api.post("/v1/chat/completions")(chat_completions)
    return api


async def require_api_key(request: Request) -> None:
    app_settings: Settings = request.app.state.settings
    api_keys = app_settings.allowed_api_keys
    if not api_keys:
        return

    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or token not in api_keys:
        raise OpenAIError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="invalid_api_key",
            message=message("invalid_api_key", app_settings.error_language),
        )


async def health() -> dict[str, str]:
    return {"status": "ok"}


async def list_models(
    request: Request,
    _auth: None = Depends(require_api_key),
) -> dict[str, Any]:
    app_settings: Settings = request.app.state.settings
    return {
        "object": "list",
        "data": [
            {
                "id": app_settings.model_id,
                "object": "model",
                "created": 0,
                "owned_by": app_settings.model_owner,
            }
        ],
    }


async def chat_completions(
    body: ChatCompletionRequest,
    request: Request,
    _auth: None = Depends(require_api_key),
) -> Response:
    payload = body.model_dump(mode="json", by_alias=True)

    if body.stream:
        stream = request.app.state.mimo.stream_chat(payload)
        response = await stream.__aenter__()

        async def body() -> AsyncIterator[bytes]:
            try:
                async for chunk in response.aiter_bytes():
                    yield chunk
            finally:
                await stream.__aexit__(None, None, None)

        return StreamingResponse(
            body(),
            status_code=response.status_code,
            media_type=response.headers.get("content-type", "text/event-stream"),
        )

    response = await request.app.state.mimo.chat(payload)
    media_type = response.headers.get("content-type")

    return Response(
        content=response.content,
        status_code=response.status_code,
        media_type=media_type,
    )


app = create_app()
