"""All configuration comes from environment variables (set in the root .env file).

Secrets use SecretStr so they never appear in logs or error messages by accident.
"""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    # NEXUS database (NOT Chatwoot's database).
    # Either one URL (hosting platforms provide this, e.g. Railway's ${{Postgres.DATABASE_URL}})…
    nexus_database_url: SecretStr = SecretStr("")
    # …or the individual parts (used by docker-compose locally).
    nexus_db_host: str = "localhost"
    nexus_db_port: int = 5432
    nexus_db_name: str = "nexus"
    nexus_db_user: str = "nexus"
    nexus_db_password: SecretStr = SecretStr("")

    log_level: str = "info"

    # Chatwoot integration — all four must be set for the integration to be "configured".
    chatwoot_base_url: str = ""
    chatwoot_account_id: str = ""
    chatwoot_api_token: SecretStr = SecretStr("")
    chatwoot_webhook_secret: SecretStr = SecretStr("")
    chatwoot_timeout_seconds: float = 5.0

    def database_url(self, database: str | None = None) -> URL:
        if self.nexus_database_url.get_secret_value():
            url = make_url(self.nexus_database_url.get_secret_value()).set(drivername="postgresql+psycopg")
            return url.set(database=database) if database else url
        return URL.create(
            "postgresql+psycopg",
            username=self.nexus_db_user,
            password=self.nexus_db_password.get_secret_value(),
            host=self.nexus_db_host,
            port=self.nexus_db_port,
            database=database or self.nexus_db_name,
        )

    @property
    def chatwoot_api_configured(self) -> bool:
        """True when we have what we need to CALL Chatwoot's API."""
        return bool(
            self.chatwoot_base_url.strip()
            and self.chatwoot_account_id.strip()
            and self.chatwoot_api_token.get_secret_value().strip()
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
