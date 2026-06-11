import base64
import json
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx

from .config import Settings
from .errors import upstream_error


class MimoClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = httpx.AsyncClient(
            limits=httpx.Limits(
                max_connections=settings.max_connections,
                max_keepalive_connections=settings.max_keepalive_connections,
            ),
            timeout=settings.request_timeout,
        )
        self._jwt: str | None = None
        self._expires_at_ms = 0

    async def close(self) -> None:
        await self._client.aclose()

    async def chat(self, payload: dict[str, Any]) -> httpx.Response:
        try:
            return await self._client.post(
                self._settings.chat_url,
                headers=await self._headers(),
                json=payload,
            )
        except httpx.HTTPError as exc:
            raise upstream_error(f"MiMo chat request failed: {exc}") from exc

    @asynccontextmanager
    async def stream_chat(self, payload: dict[str, Any]) -> AsyncIterator[httpx.Response]:
        try:
            async with self._client.stream(
                "POST",
                self._settings.chat_url,
                headers=await self._headers(),
                json=payload,
            ) as response:
                yield response
        except httpx.HTTPError as exc:
            raise upstream_error(f"MiMo chat stream failed: {exc}") from exc

    async def _headers(self) -> dict[str, str]:
        token = await self._get_token()
        return {
            "Authorization": f"Bearer {token}",
            "X-Mimo-Source": self._settings.source_header,
        }

    async def _get_token(self) -> str:
        now_ms = int(time.time() * 1000)
        if self._jwt and now_ms < self._expires_at_ms - self._settings.token_refresh_margin_ms:
            return self._jwt

        try:
            response = await self._client.post(
                self._settings.bootstrap_url,
                json={"client": self._settings.client_id},
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise upstream_error(f"MiMo bootstrap failed: {exc}") from exc

        jwt = data.get("jwt")
        if not isinstance(jwt, str):
            raise upstream_error("MiMo bootstrap returned an invalid token payload")

        expires_at_ms = token_expiry_ms(jwt, data.get("exp"))
        self._jwt = jwt
        self._expires_at_ms = expires_at_ms
        return jwt


def token_expiry_ms(jwt: str, expires_at: object = None) -> int:
    if expires_at is not None:
        return normalize_expiry_ms(expires_at)

    try:
        _, payload, _ = jwt.split(".", 2)
        padded_payload = payload + "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded_payload))
        return normalize_expiry_ms(data["exp"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise upstream_error("MiMo bootstrap token does not include a valid exp claim") from exc


def normalize_expiry_ms(expires_at: object) -> int:
    try:
        value = int(expires_at)
    except (TypeError, ValueError) as exc:
        raise upstream_error("MiMo bootstrap returned an invalid exp value") from exc

    if value < 10_000_000_000:
        return value * 1000
    return value
