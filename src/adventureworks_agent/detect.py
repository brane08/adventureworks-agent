from typing import Literal, NamedTuple

from adventureworks_agent.db import execute


class DetectResult(NamedTuple):
    source: Literal["DMV", "QS"]
    db: str
    major: int
    qs_state: str | None


_QS_OPTIONS_SQL = "SELECT actual_state, readonly_reason, query_capture_mode FROM sys.database_query_store_options"
_VERSION_SQL = "SELECT CAST(SERVERPROPERTY('ProductMajorVersion') AS int) AS major"


def detect(conn, db_name: str) -> DetectResult:
    version_rows = execute(conn, _VERSION_SQL)
    major = version_rows[0]["major"] if version_rows else 0

    qs_rows = execute(conn, _QS_OPTIONS_SQL)
    if not qs_rows:
        return DetectResult(source="DMV", db=db_name, major=major, qs_state=None)

    row = qs_rows[0]
    qs_state = row["actual_state"]
    qs_ready = qs_state == "READ_WRITE" and row["readonly_reason"] == 0 and row["query_capture_mode"] != "NONE"
    return DetectResult(source="QS" if qs_ready else "DMV", db=db_name, major=major, qs_state=qs_state)
