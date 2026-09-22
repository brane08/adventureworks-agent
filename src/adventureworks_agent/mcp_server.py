from fastmcp import FastMCP

from adventureworks_agent.config import load_settings
from adventureworks_agent.db import get_connection
from adventureworks_agent.plan_service import PlanService

mcp = FastMCP("adventureworks-plan-analyzer")

_service: PlanService | None = None


def _get_service() -> PlanService:
    global _service
    if _service is None:
        settings = load_settings()
        conn = get_connection(settings)
        _service = PlanService(conn, settings.mssql_database)
    return _service


@mcp.tool
def detect() -> dict:
    """Detect whether this connection routes plan analysis to Query Store or plan-cache DMVs."""
    return _get_service().detect()


@mcp.tool
def list_queries(kind: str, metric: str = "CPU", top: int = 10, min_execs: int = 1, since: str = "1900-01-01") -> dict:
    """List candidate queries by kind (TOP, VARIANCE, SNIFFING, SPILLS_GRANTS, COMPILE_HEAVY, REGRESSION)."""
    return _get_service().list(kind, metric=metric, top=top, min_execs=min_execs, since=since)


@mcp.tool
def summary(key: str) -> dict:
    """Return a diagnostic summary (warnings, missing indexes, cardinality skew, etc.) for a plan key."""
    return _get_service().summary(key)


@mcp.tool
def tree(key: str) -> dict:
    """Return the constrained one-line-per-operator plan tree for a plan key."""
    return _get_service().tree(key)


@mcp.tool
def operators(key: str) -> dict:
    """Return all RelOp rows (top 40 by subtree cost) for a plan key."""
    return _get_service().operators(key)


@mcp.tool
def subtree(key: str, node_id: int, max_chars: int = 8000) -> dict:
    """Return one RelOp subtree as XML text, bounded by max_chars."""
    return _get_service().subtree(key, node_id, max_chars=max_chars)


@mcp.tool
def raw(key: str, max_chars: int = 16000, reason: str = "") -> dict:
    """Return a bounded slice of the raw plan text. Always pass a reason for auditability."""
    return _get_service().raw(key, max_chars=max_chars, reason=reason)


if __name__ == "__main__":
    mcp.run()
