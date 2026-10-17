from contextlib import contextmanager
from pathlib import Path
from uuid import UUID

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[2]
DEMO_ORG = UUID("214ab2f4-5555-4333-8999-000000000001")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT / ".env", ROOT / ".env.llm"), extra="ignore"
    )
    database_url: str
    migration_database_url: str
    session_secret: str
    app_origin: str = "http://127.0.0.1:3010"
    demo_mode: bool = True
    public_demo_mode: bool = False
    private_analyst_enabled: bool = False
    private_access_key: str = ""
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-flash"
    llm_provider: str = "deepseek"
    llm_tier: str = "paid"
    oidc_issuer: str = ""
    oidc_audience: str = ""
    temporal_address: str = "localhost:7233"


settings = Settings()
engine = create_engine(
    settings.database_url,
    pool_size=5,
    max_overflow=5,
    pool_pre_ping=True,
    connect_args={"options": "-c client_encoding=UTF8"},
)


@contextmanager
def session(org: UUID | None = None):
    if org is None:
        from .auth import tenant

        org = tenant.get()
    with engine.begin() as conn:
        conn.execute(
            text("SELECT set_config('app.org_id', :org, true)"), {"org": str(org)}
        )
        yield conn


def rows(conn, query: str, parameters=None):
    return [dict(row) for row in conn.execute(text(query), parameters or {}).mappings()]
