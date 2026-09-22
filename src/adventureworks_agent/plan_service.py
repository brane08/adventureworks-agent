import logging

from adventureworks_agent.db import PlanTooLargeError, execute, not_found
from adventureworks_agent.detect import detect
from adventureworks_agent.json_shape import shape
from adventureworks_agent.keys import key_source, parse_key
from adventureworks_agent.queries.extractors import (
    OPERATORS_SELECT,
    RAW_SELECT,
    SUBTREE_SELECT_TEMPLATE,
    SUMMARY_SELECT,
    TREE_ROWS_SELECT,
    TREE_SELECT,
    build_src_cte,
)
from adventureworks_agent.queries.list_dmv import build_dmv_list_query
from adventureworks_agent.queries.list_qs import build_qs_list_query
from adventureworks_agent.tree_format import render_tree

_MAX_SQL_LEN = 300


class PlanService:
    def __init__(self, conn, db_name: str):
        self.conn = conn
        self.db_name = db_name
        self._detect_cache = None

    def detect(self) -> dict:
        if self._detect_cache is None:
            self._detect_cache = detect(self.conn, self.db_name)
        result = self._detect_cache
        return {"source": result.source, "db": result.db, "major": result.major, "qs_state": result.qs_state}

    def list(self, kind: str, metric: str = "CPU", top: int = 10, min_execs: int = 1, since: str = "1900-01-01") -> dict:
        top = min(top, 20)
        source = self.detect()["source"]

        if source == "DMV":
            if kind == "REGRESSION":
                return {"status": "unsupported_on_source", "rows": []}
            resolved_kind = f"TOP_{metric}" if kind == "TOP" else kind
            sql, param_order = build_dmv_list_query(resolved_kind)
            params = {"top": top, "min_execs": min_execs, "max_sql": _MAX_SQL_LEN}
        else:
            resolved_kind = kind
            sql, param_order = build_qs_list_query(resolved_kind)
            params = {"top": top, "min_execs": min_execs, "max_sql": _MAX_SQL_LEN, "since": since}

        bound_params = tuple(params[name] for name in param_order)
        rows = execute(self.conn, sql, bound_params)
        return {"rows": rows}

    def summary(self, key: str) -> dict:
        parsed = parse_key(key)
        if key_source(key) != self.detect()["source"]:
            return {"status": "source_mismatch"}

        cte, cte_params = build_src_cte(parsed)
        sql = f"{cte} {SUMMARY_SELECT}"
        try:
            rows = execute(self.conn, sql, cte_params)
        except PlanTooLargeError:
            return {"status": "plan_too_large", "hint": "use raw"}
        if not rows:
            return not_found()
        return shape(rows[0])

    def tree(self, key: str) -> dict:
        parsed = parse_key(key)
        if key_source(key) != self.detect()["source"]:
            return {"status": "source_mismatch"}

        cte, cte_params = build_src_cte(parsed)
        try:
            header_rows = execute(self.conn, f"{cte} {TREE_SELECT}", cte_params)
            body_rows = execute(self.conn, f"{cte} {TREE_ROWS_SELECT}", cte_params)
        except PlanTooLargeError:
            return {"status": "plan_too_large", "hint": "use raw"}
        if not header_rows:
            return not_found()
        return {"tree": render_tree(header_rows[0], body_rows)}

    def operators(self, key: str) -> dict:
        parsed = parse_key(key)
        if key_source(key) != self.detect()["source"]:
            return {"status": "source_mismatch"}

        cte, cte_params = build_src_cte(parsed)
        try:
            rows = execute(self.conn, f"{cte} {OPERATORS_SELECT}", cte_params)
        except PlanTooLargeError:
            return {"status": "plan_too_large", "hint": "use raw"}
        if not rows:
            return not_found()
        return {"rows": shape(rows)}

    def subtree(self, key: str, node_id: int, max_chars: int = 8000) -> dict:
        parsed = parse_key(key)
        if key_source(key) != self.detect()["source"]:
            return {"status": "source_mismatch"}

        max_chars = min(max_chars, 8000)
        cte, cte_params = build_src_cte(parsed)
        sql = f"DECLARE @node_id int = {node_id}; {cte} {SUBTREE_SELECT_TEMPLATE}"
        try:
            rows = execute(self.conn, sql, cte_params + (max_chars,))
        except PlanTooLargeError:
            return {"status": "plan_too_large", "hint": "use raw"}
        if not rows:
            return not_found()
        return shape(rows[0])

    def raw(self, key: str, max_chars: int = 16000, reason: str = "") -> dict:
        parsed = parse_key(key)
        if key_source(key) != self.detect()["source"]:
            return {"status": "source_mismatch"}

        logging.getLogger(__name__).info("raw() called for key=%s reason=%s", key, reason)
        max_chars = min(max_chars, 16000)
        cte, cte_params = build_src_cte(parsed, as_text=True)
        sql = f"{cte} {RAW_SELECT}"
        try:
            rows = execute(self.conn, sql, cte_params + (max_chars,))
        except PlanTooLargeError:
            return {"status": "plan_too_large", "hint": "use raw"}
        if not rows:
            return not_found()
        return shape(rows[0])
