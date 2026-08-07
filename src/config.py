"""Configuration for the AutoDrive Chatbot integration mock host."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven settings.

    Everything the browser is allowed to know is exposed to the page template.
    ``autodrive_auth_client_id`` / ``autodrive_auth_client_secret`` are used
    server-side only and are never rendered into the HTML.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Credentials (server-side only, provided by Dadosfera per environment) ---
    autodrive_auth_client_id: str = ""
    autodrive_auth_client_secret: str = ""

    # --- AutoDrive Assistant API ---
    # Public base URL of the Dadosfera Assistant API, NOT this app's host.
    # The widget builds {autodrive_url}/datasets/{dataset_id}/ai-question from it.
    autodrive_url: str = "https://autodrive-assistant-api-verticity.stg.dadosfera.ai"
    # Host that serves the widget bundle: {host}/chatbot/autodrive-chatbot.umd.cjs
    autodrive_widget_host: str = "https://autodrive-verticity.stg.dadosfera.ai"

    # --- Widget wiring ---
    autodrive_client: str = "verticity"
    autodrive_dataset_id: str = ""
    autodrive_assistant_id: str = ""
    autodrive_api_profile: Literal["assistant", "embed"] = "assistant"
    autodrive_environment: str = "stg"
    autodrive_locale: Literal["pt-BR", "en-US", "es-ES"] = "pt-BR"

    # Path on THIS backend that the widget calls to obtain a temporary token.
    autodrive_token_endpoint: str = "/api/autodrive/chat-token"

    # --- Widget appearance ---
    autodrive_title: str = "AutoDrive Assistant"
    autodrive_placeholder: str = "Type your question..."
    autodrive_position: Literal["bottom-right", "bottom-left", "inline"] = (
        "bottom-right"
    )
    autodrive_primary_color: str = "#111827"
    autodrive_accent_color: str = "#2563EB"
    autodrive_launcher_label: str = "Open assistant"

    # --- Mock host behavior ---
    # When true, the widget talks to {this host}/autodrive-api/* and this
    # backend forwards the calls to autodrive_url. Use it when this page's
    # origin (e.g. http://localhost:8080) is not in the Assistant API's
    # ASSISTANT_API_CORS_ALLOW_ORIGINS. A real customer site whose origin IS
    # allow-listed (like https://build.verticity.com:8004) does not need it.
    autodrive_dev_proxy: bool = False
    # Origin the dev proxy presents to the Assistant API. Its middleware
    # requires an allow-listed Origin/Referer on /ai-question even for
    # server-side calls, so simulate the customer's allow-listed origin here.
    autodrive_dev_proxy_origin: str = ""
    # When true, /api/autodrive/chat-token returns a synthetic token instead of
    # calling the Assistant API. Lets the page be demoed without credentials.
    autodrive_mock_token: bool = False
    # Simulated identity of the "logged-in user" of this mock host, forwarded as
    # externalUserId so conversations are isolated per user.
    mock_external_user_id: str = "demo-user-1"

    host: str = "0.0.0.0"
    port: int = 8000

    @property
    def widget_script_url(self) -> str:
        return f"{self.autodrive_widget_host.rstrip('/')}/chatbot/autodrive-chatbot.umd.cjs"

    @property
    def token_url(self) -> str:
        return f"{self.autodrive_url.rstrip('/')}/auth/token"

    @property
    def has_credentials(self) -> bool:
        return bool(self.autodrive_auth_client_id and self.autodrive_auth_client_secret)


@lru_cache
def get_settings() -> Settings:
    return Settings()
