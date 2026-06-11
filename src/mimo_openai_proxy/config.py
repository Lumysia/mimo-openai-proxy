from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MiMo OpenAI Proxy"
    host: str = "127.0.0.1"
    port: int = 8000
    client_id: str = "mimo-openai-proxy"
    api_keys: str = ""
    cors_origins: str = ""
    error_language: str = "en"
    model_id: str = "mimo-auto"
    model_owner: str = "xiaomi-mimo"
    source_header: str = "mimocode-cli-free"
    bootstrap_url: str = "https://api.xiaomimimo.com/api/free-ai/bootstrap"
    chat_url: str = "https://api.xiaomimimo.com/api/free-ai/openai/chat"
    request_timeout: float = 120.0
    max_connections: int = 100
    max_keepalive_connections: int = 20
    token_refresh_margin_ms: int = 60_000

    model_config = SettingsConfigDict(env_prefix="MIMO_", env_file=".env", extra="ignore")

    @property
    def allowed_api_keys(self) -> set[str]:
        return {key.strip() for key in self.api_keys.split(",") if key.strip()}

    @property
    def allowed_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
