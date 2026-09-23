from collections.abc import Callable

from fastmcp import FastMCP
from mssql_python.exceptions import InterfaceError, OperationalError

from adventureworks_agent.config import load_settings
from adventureworks_agent.db import ServiceError, get_connection
from adventureworks_agent.plan_service import PlanService

mcp = FastMCP("adventureworks-plan-analyzer")

_service: PlanService | None = None

_CONNECTION_ERRORS = (OperationalError, InterfaceError)


def _get_service() -> PlanService:
    global _service
    if _service is None:
        settings = load_settings()
        conn = get_connection(settings)
        _service = PlanService(conn, settings.mssql_database)
    return _service


def _reset_service() -> None:
    global _service
    if _service is not None:
        try:
            _service.conn.close()
        except Exception:
            pass
    _service = None


def _call(op: Callable[[PlanService], dict]) -> dict:
    for attempt in range(2):
        try:
            return op(_get_service())
        except ServiceError as exc:
            if exc.status == "transient" and attempt == 0:
                _reset_service()
                continue
            return {"status": exc.status, "message": str(exc)}
        except _CONNECTION_ERRORS as exc:
            _reset_service()
            if attempt == 0:
                continue
            return {"status": "transient", "message": str(exc)}
        except ValueError as exc:
            return {"status": "invalid_argument", "message": str(exc)}
    raise AssertionError("unreachable")


@mcp.tool
def detect() -> dict:
    """Detect whether this connection routes plan analysis to Query Store or plan-cache DMVs."""
    return _call(lambda s: s.detect())


@mcp.tool
def list_queries(kind: str, metric: str = "CPU", top: int = 10, min_execs: int = 1, since: str = "1900-01-01") -> dict:
    """List candidate queries by kind (TOP, VARIANCE, SNIFFING, SPILLS_GRANTS, COMPILE_HEAVY, REGRESSION)."""
    return _call(lambda s: s.list(kind, metric=metric, top=top, min_execs=min_execs, since=since))


@mcp.tool
def summary(key: str) -> dict:
    """Return a diagnostic summary (warnings, missing indexes, cardinality skew, etc.) for a plan key."""
    return _call(lambda s: s.summary(key))


@mcp.tool
def tree(key: str) -> dict:
    """Return the constrained one-line-per-operator plan tree for a plan key."""
    return _call(lambda s: s.tree(key))


@mcp.tool
def operators(key: str) -> dict:
    """Return all RelOp rows (top 40 by subtree cost) for a plan key."""
    return _call(lambda s: s.operators(key))


@mcp.tool
def subtree(key: str, node_id: int, max_chars: int = 8000) -> dict:
    """Return one RelOp subtree as XML text, bounded by max_chars."""
    return _call(lambda s: s.subtree(key, node_id, max_chars=max_chars))


@mcp.tool
def raw(key: str, max_chars: int = 16000, reason: str = "") -> dict:
    """Return a bounded slice of the raw plan text. Always pass a reason for auditability."""
    return _call(lambda s: s.raw(key, max_chars=max_chars, reason=reason))


if __name__ == "__main__":
    mcp.run()
