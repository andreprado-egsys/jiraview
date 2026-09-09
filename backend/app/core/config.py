# egSYS JiraView — Configuração centralizada
import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "dev"
    app_port: int = 8090
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Jira (backend-only)
    jira_url: str = "https://egsys.atlassian.net"
    jira_user: str = ""
    jira_token: str = ""
    jira_projects: str = "HDPMSC,SCPMH"

    # Dify (opcional)
    dify_api_url: str = ""
    dify_api_key: str = ""
    dify_dataset_id: str = ""

    # Resource limits (espelho Docker)
    max_mem: str = "512m"
    max_cpu: str = "1.0"
    max_pids: int = 150

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def jira_scopes(self) -> list[str]:
        return [p.strip() for p in self.jira_projects.split(",") if p.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
