from mssql_python import connect as mssql_connect

from adventureworks_agent.config import Settings

_PERMISSION_ERRORS = {297, 300}
_SOURCE_UNAVAILABLE_ERRORS = {208}
_PLAN_TOO_LARGE_ERRORS = {6335}
_TRANSIENT_ERRORS = {1205, -2, 40613, 40197}


class ServiceError(Exception):
    def __init__(self, status: str, message: str = ""):
        super().__init__(message or status)
        self.status = status


class PermissionError_(ServiceError):
    def __init__(self, message: str = ""):
        super().__init__("permission", message)


class SourceUnavailableError(ServiceError):
    def __init__(self, message: str = ""):
        super().__init__("source_unavailable", message)


class PlanTooLargeError(ServiceError):
    def __init__(self, message: str = ""):
        super().__init__("plan_too_large", message)


def not_found() -> dict:
    return {"status": "not_found"}


def get_connection(settings: Settings):
    conn_str = (
        f"Server={settings.mssql_host},{settings.mssql_port};"
        f"Database={settings.mssql_database};"
        f"Uid={settings.mssql_user};Pwd={settings.mssql_password};"
        "Encrypt=yes;TrustServerCertificate=yes"
    )
    return mssql_connect(conn_str, autocommit=True)


def _error_number(exc: Exception) -> int | None:
    if exc.args and isinstance(exc.args[0], int):
        return exc.args[0]
    return None


def _map_and_raise(exc: Exception):
    number = _error_number(exc)
    if number in _PERMISSION_ERRORS:
        raise PermissionError_(str(exc)) from exc
    if number in _SOURCE_UNAVAILABLE_ERRORS:
        raise SourceUnavailableError(str(exc)) from exc
    if number in _PLAN_TOO_LARGE_ERRORS:
        raise PlanTooLargeError(str(exc)) from exc
    if number in _TRANSIENT_ERRORS:
        raise ServiceError("transient", str(exc)) from exc
    raise


def execute(conn, sql: str, params: tuple = ()) -> list[dict]:
    for attempt in range(2):
        cursor = conn.cursor()
        try:
            cursor.execute(sql, params)
            columns = [d[0] for d in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
        except Exception as exc:
            number = _error_number(exc)
            if number in _TRANSIENT_ERRORS and attempt == 0:
                continue
            _map_and_raise(exc)
        finally:
            cursor.close()
    raise ServiceError("transient", "retry exhausted")
