import uvicorn

from .config import settings


def main() -> None:
    uvicorn.run("mimo_openai_proxy.app:app", host=settings.host, port=settings.port)
