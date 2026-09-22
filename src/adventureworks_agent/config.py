import os
from dataclasses import dataclass

from dotenv import load_dotenv

_REQUIRED = (
    "MSSQL_HOST",
    "MSSQL_PORT",
    "MSSQL_DATABASE",
    "MSSQL_USER",
    "MSSQL_PASSWORD",
    "OPENROUTER_API_KEY",
)

_DEFAULT_OPENROUTER_MODEL = "anthropic/claude-sonnet-5"


@dataclass(frozen=True)
class Settings:
    mssql_host: str
    mssql_port: int
    mssql_database: str
    mssql_user: str
    mssql_password: str
    openrouter_api_key: str
    openrouter_model: str


def load_settings() -> Settings:
    load_dotenv()
    missing = [name for name in _REQUIRED if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"Missing required environment variable(s): {', '.join(missing)}")
    return Settings(
        mssql_host=os.environ["MSSQL_HOST"],
        mssql_port=int(os.environ["MSSQL_PORT"]),
        mssql_database=os.environ["MSSQL_DATABASE"],
        mssql_user=os.environ["MSSQL_USER"],
        mssql_password=os.environ["MSSQL_PASSWORD"],
        openrouter_api_key=os.environ["OPENROUTER_API_KEY"],
        openrouter_model=os.environ.get("OPENROUTER_MODEL", _DEFAULT_OPENROUTER_MODEL),
    )
