import pytest
from adventureworks_agent.config import Settings
from adventureworks_agent.db import (
    PermissionError_,
    PlanTooLargeError,
    ServiceError,
    SourceUnavailableError,
    execute,
    get_connection,
)


class FakeDriverError(Exception):
    def __init__(self, number, message="driver error"):
        super().__init__(message)
        self.args = (number, message)


class FakeCursor:
    def __init__(self, rows=None, columns=None, raise_seq=None):
        self._rows = rows or []
        self._columns = columns or []
        self._raise_seq = list(raise_seq or [])
        self.description = [(c,) for c in self._columns]

    def execute(self, sql, params=()):
        if self._raise_seq:
            exc = self._raise_seq.pop(0)
            if exc is not None:
                raise exc

    def fetchall(self):
        return self._rows

    def close(self):
        pass


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor


def test_get_connection_builds_connection_string(monkeypatch):
    captured = {}

    def fake_connect(conn_str, **kwargs):
        captured["conn_str"] = conn_str
        return FakeConnection(FakeCursor())

    monkeypatch.setattr("adventureworks_agent.db.mssql_connect", fake_connect)
    settings = Settings("localhost", 1433, "AdventureWorks2019", "sa", "secret", "sk-or-test", "anthropic/claude-sonnet-5")

    get_connection(settings)

    assert "Server=localhost,1433" in captured["conn_str"]
    assert "Database=AdventureWorks2019" in captured["conn_str"]
    assert "Encrypt=yes" in captured["conn_str"]
    assert "TrustServerCertificate=yes" in captured["conn_str"]


def test_execute_returns_rows_as_dicts():
    cursor = FakeCursor(rows=[(1, "a"), (2, "b")], columns=["id", "name"])
    conn = FakeConnection(cursor)

    rows = execute(conn, "SELECT id, name FROM t")

    assert rows == [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]


def test_execute_empty_result_returns_empty_list():
    cursor = FakeCursor(rows=[], columns=["id"])
    conn = FakeConnection(cursor)

    assert execute(conn, "SELECT id FROM t WHERE 1=0") == []


@pytest.mark.parametrize(
    "error_number,expected_exc",
    [(297, PermissionError_), (300, PermissionError_), (208, SourceUnavailableError), (6335, PlanTooLargeError)],
)
def test_execute_maps_known_errors(error_number, expected_exc):
    cursor = FakeCursor(raise_seq=[FakeDriverError(error_number)])
    conn = FakeConnection(cursor)

    with pytest.raises(expected_exc):
        execute(conn, "SELECT 1")


@pytest.mark.parametrize("error_number", [1205, -2, 40613, 40197])
def test_execute_retries_transient_once_then_succeeds(error_number):
    cursor = FakeCursor(rows=[(1,)], columns=["id"], raise_seq=[FakeDriverError(error_number), None])
    conn = FakeConnection(cursor)

    rows = execute(conn, "SELECT id FROM t")

    assert rows == [{"id": 1}]


def test_execute_transient_fails_twice_raises_service_error():
    cursor = FakeCursor(raise_seq=[FakeDriverError(1205), FakeDriverError(1205)])
    conn = FakeConnection(cursor)

    with pytest.raises(ServiceError) as excinfo:
        execute(conn, "SELECT 1")
    assert excinfo.value.status == "transient"
