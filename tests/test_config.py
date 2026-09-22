import pytest
from adventureworks_agent.config import load_settings


def test_load_settings_reads_env(monkeypatch):
    monkeypatch.setenv("MSSQL_HOST", "localhost")
    monkeypatch.setenv("MSSQL_PORT", "1433")
    monkeypatch.setenv("MSSQL_DATABASE", "AdventureWorks2019")
    monkeypatch.setenv("MSSQL_USER", "sa")
    monkeypatch.setenv("MSSQL_PASSWORD", "secret")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setenv("OPENROUTER_MODEL", "openai/gpt-5")

    settings = load_settings()

    assert settings.mssql_host == "localhost"
    assert settings.mssql_port == 1433
    assert settings.mssql_database == "AdventureWorks2019"
    assert settings.mssql_user == "sa"
    assert settings.mssql_password == "secret"
    assert settings.openrouter_api_key == "sk-or-test"
    assert settings.openrouter_model == "openai/gpt-5"


def test_load_settings_defaults_openrouter_model(monkeypatch):
    monkeypatch.setattr("adventureworks_agent.config.load_dotenv", lambda: None)
    monkeypatch.setenv("MSSQL_HOST", "localhost")
    monkeypatch.setenv("MSSQL_PORT", "1433")
    monkeypatch.setenv("MSSQL_DATABASE", "AdventureWorks2019")
    monkeypatch.setenv("MSSQL_USER", "sa")
    monkeypatch.setenv("MSSQL_PASSWORD", "secret")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)

    settings = load_settings()

    assert settings.openrouter_model == "anthropic/claude-sonnet-5"


def test_load_settings_missing_var_raises(monkeypatch):
    monkeypatch.setattr("adventureworks_agent.config.load_dotenv", lambda: None)
    monkeypatch.delenv("MSSQL_HOST", raising=False)
    with pytest.raises(RuntimeError, match="MSSQL_HOST"):
        load_settings()
