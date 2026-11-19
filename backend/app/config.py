"""Environment-backed application settings."""
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    database_url: str = "sqlite:///./arzon.db"
    jwt_secret: str = "arzon-dev-secret-CHANGE-ME"
    jwt_expire_days: int = 30
    google_client_ids: str = ""
    apple_bundle_id: str = "kg.arzon.app"
    super_admin_emails: str = ""
    kuryer_emails: str = ""
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"
    gemini_api_key: str = ""
    komissiya_foizi: int = 1
    code_attempt_limit: int = 5
    code_attempt_window_seconds: int = 60
    yetkazish_baza_narxi: int = 100
    cors_origins: str = "*"
    instagram_verify_token: str = ""
    instagram_page_token: str = ""
    @property
    def google_client_id_list(self) -> List[str]: return [x.strip() for x in self.google_client_ids.split(",") if x.strip()]
    @property
    def super_admin_email_list(self) -> List[str]: return [x.strip().lower() for x in self.super_admin_emails.split(",") if x.strip()]
    @property
    def kuryer_email_list(self) -> List[str]: return [x.strip().lower() for x in self.kuryer_emails.split(",") if x.strip()]
    @property
    def cors_origin_list(self) -> List[str]: return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

@lru_cache
def get_settings(): return Settings()
settings = get_settings()
