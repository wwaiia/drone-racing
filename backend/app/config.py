from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    database_url: str = f"sqlite:///{BASE_DIR / 'data' / 'drone_events.db'}"
    admin_token: str = "change-me-admin-token"
    vk_service_token: str = ""
    telegram_api_id: str = ""
    telegram_api_hash: str = ""
    telegram_session: str = "drone_aggregator"
    telegram_proxy: str = ""
    collect_channels: str = ""
    collect_vk_groups: str = ""
    collect_limit: int = 40
    seed_demo: bool = False
    llm_api_key: str = ""
    llm_model: str = "gpt-4.1-mini"

    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = "utf-8"


settings = Settings()
