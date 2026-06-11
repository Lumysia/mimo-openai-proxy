# MiMo OpenAI Proxy

OpenAI-compatible proxy for MiMo Auto.

## Run

```powershell
uv sync
uv run mimo-openai-proxy
```

The service listens on `http://127.0.0.1:8000` and exposes:

- `GET /health`
- `GET /v1/models`
- `POST /v1/chat/completions`

```powershell
curl http://127.0.0.1:8000/v1/models
```

With `MIMO_API_KEYS`:

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer <key>" \
  -H "Content-Type: application/json" \
  -d '{"model":"mimo-auto","messages":[{"role":"user","content":"Hello"}]}'
```

## Configuration

- `MIMO_HOST`: bind host, defaults to `127.0.0.1`.
- `MIMO_PORT`: bind port, defaults to `8000`.
- `MIMO_CLIENT_ID`: client identifier used during MiMo bootstrap, defaults to `mimo-openai-proxy`.
- `MIMO_API_KEYS`: optional comma-separated Bearer keys for `/v1/*` routes.
- `MIMO_CORS_ORIGINS`: optional comma-separated CORS origins.
- `MIMO_ERROR_LANGUAGE`: error language, `en` or `zh`, defaults to `en`.
- `MIMO_MODEL_ID`: OpenAI model id shown by `/v1/models`, defaults to `mimo-auto`.
- `MIMO_REQUEST_TIMEOUT`: upstream request timeout in seconds, defaults to `120`.
- `MIMO_MAX_CONNECTIONS`: max upstream HTTP connections, defaults to `100`.
- `MIMO_MAX_KEEPALIVE_CONNECTIONS`: max idle upstream HTTP connections, defaults to `20`.
- `MIMO_BOOTSTRAP_URL`: MiMo bootstrap endpoint.
- `MIMO_CHAT_URL`: MiMo chat endpoint.

Use `.env.example` as a template.

## Docker

```powershell
docker build -t mimo-openai-proxy .
docker run --rm -p 8000:8000 --env-file .env mimo-openai-proxy
docker pull ghcr.io/lumysia/mimo-openai-proxy:latest
```

## Development

```powershell
uv run pytest
uv run ruff check .
uv run python -m compileall src
```
