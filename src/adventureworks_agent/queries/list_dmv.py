_TEMPLATE = """
;WITH cand AS (
    SELECT TOP (?)
           plan_handle, sql_handle, statement_start_offset, statement_end_offset,
           query_hash, query_plan_hash, execution_count,
           total_worker_time, total_elapsed_time, total_logical_reads, max_logical_reads,
           max_elapsed_time, total_spills, max_grant_kb, max_used_grant_kb,
           last_execution_time,
           {flag_expr} AS flag_value
    FROM sys.dm_exec_query_stats
    WHERE execution_count >= ?
      {kind_filter}
    ORDER BY {order_expr} DESC
)
SELECT 'dmv:' + CONVERT(varchar(130), c.plan_handle, 1) + ':' + CAST(c.statement_start_offset AS varchar)
             + ':' + CAST(c.statement_end_offset AS varchar)       AS query_key,
       CONVERT(varchar(20), c.query_hash, 1)                       AS query_hash,
       CONVERT(varchar(20), c.query_plan_hash, 1)                  AS plan_hash,
       c.execution_count                                           AS execs,
       c.total_worker_time  / c.execution_count / 1000.0           AS avg_cpu_ms,
       c.total_elapsed_time / c.execution_count / 1000.0           AS avg_elapsed_ms,
       c.total_logical_reads / c.execution_count                   AS avg_reads,
       c.max_logical_reads                                         AS max_reads,
       c.last_execution_time                                       AS last_exec,
       c.flag_value,
       LEFT(SUBSTRING(st.text, (c.statement_start_offset/2)+1,
            ((CASE c.statement_end_offset WHEN -1 THEN DATALENGTH(st.text)
               ELSE c.statement_end_offset END - c.statement_start_offset)/2)+1), ?) AS sql_text,
       'DMV' AS source
FROM cand c
CROSS APPLY sys.dm_exec_sql_text(c.sql_handle) st
OPTION (RECOMPILE);
"""

_KIND_SHAPES = {
    "TOP_CPU": {"order_expr": "total_worker_time / execution_count", "kind_filter": "", "flag_expr": "NULL"},
    "TOP_ELAPSED": {"order_expr": "total_elapsed_time / execution_count", "kind_filter": "", "flag_expr": "NULL"},
    "TOP_READS": {"order_expr": "total_logical_reads / execution_count", "kind_filter": "", "flag_expr": "NULL"},
    "VARIANCE": {
        "order_expr": "max_elapsed_time * 1.0 / (total_elapsed_time / execution_count)",
        "kind_filter": "AND max_elapsed_time > 5 * (total_elapsed_time / execution_count)",
        "flag_expr": "max_elapsed_time * 1.0 / (total_elapsed_time / execution_count)",
    },
    "SNIFFING": {
        "order_expr": "(SELECT COUNT(DISTINCT query_plan_hash) FROM sys.dm_exec_query_stats q2 WHERE q2.query_hash = dm_exec_query_stats.query_hash)",
        "kind_filter": (
            "AND query_hash IN (SELECT query_hash FROM sys.dm_exec_query_stats "
            "GROUP BY query_hash HAVING COUNT(DISTINCT query_plan_hash) > 1)"
        ),
        "flag_expr": "(SELECT COUNT(DISTINCT query_plan_hash) FROM sys.dm_exec_query_stats q2 WHERE q2.query_hash = dm_exec_query_stats.query_hash)",
    },
    "SPILLS_GRANTS": {
        "order_expr": "total_spills DESC, max_grant_kb",
        "kind_filter": "AND (total_spills > 0 OR max_grant_kb > 4 * NULLIF(max_used_grant_kb,0))",
        "flag_expr": "total_spills",
    },
    "COMPILE_HEAVY": {
        "order_expr": "total_compile_time",
        "kind_filter": "AND total_compile_time > total_worker_time",
        "flag_expr": "total_compile_time / 1000.0",
    },
}


def build_dmv_list_query(kind: str) -> tuple[str, tuple[str, ...]]:
    if kind == "REGRESSION":
        raise ValueError("REGRESSION is QS-only; unsupported on DMV source")
    if kind not in _KIND_SHAPES:
        raise ValueError(f"Unknown list kind: {kind!r}")
    sql = _TEMPLATE.format(**_KIND_SHAPES[kind])
    return sql, ("top", "min_execs", "max_sql")
