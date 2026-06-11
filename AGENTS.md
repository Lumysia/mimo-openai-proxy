# AGENTS.md

- Respond in the user's language unless code, logs, commands, or external text require otherwise.
- Use `uv` for dependency management and project commands.
- Keep the service as a small FastAPI proxy for MiMo Auto.
- Keep OpenAI-compatible routes under `/v1/*`; upstream MiMo endpoints stay isolated in `src/mimo_openai_proxy/mimo.py`.
- Prefer existing libraries such as FastAPI, httpx, and pydantic-settings over custom protocol or HTTP plumbing.
- Keep runtime message text in `src/mimo_openai_proxy/locales/<language>.json`; `errors.py` only loads and formats messages.
- Run `uv run pytest`, `uv run ruff check .`, and `uv run python -m compileall src` before claiming code works.
- Do not commit changes unless explicitly asked.
