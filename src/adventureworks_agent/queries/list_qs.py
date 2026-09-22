_TEMPLATE = """
;WITH agg AS (
    SELECT p.query_id, MAX(p.plan_id) AS plan_id, q.query_hash, MAX(p.query_plan_hash) AS query_plan_hash,
           SUM(rs.count_executions)                                                       AS execs,
           SUM(rs.avg_cpu_time * rs.count_executions) / SUM(rs.count_executions)          AS avg_cpu_us,
           SUM(rs.avg_duration * rs.count_executions) / SUM(rs.count_executions)          AS avg_dur_us,
           SUM(rs.avg_logical_io_reads * rs.count_executions) / SUM(rs.count_executions)  AS avg_reads,
           MAX(rs.max_logical_io_reads) AS max_reads, MAX(rs.last_execution_time) AS last_exec,
           {flag_expr} AS flag_value
    FROM sys.query_store_runtime_stats rs
    JOIN sys.query_store_plan  p ON p.plan_id = rs.plan_id
    JOIN sys.query_store_query q ON q.query_id = p.query_id
    JOIN sys.query_store_runtime_stats_interval i ON i.runtime_stats_interval_id = rs.runtime_stats_interval_id
    {extra_join}
    WHERE i.start_time >= ?
    GROUP BY p.query_id, q.query_hash
    HAVING SUM(rs.count_executions) >= ? {kind_having}
)
SELECT TOP (?)
       'qs:' + CAST(a.query_id AS varchar) + ':' + CAST(a.plan_id AS varchar) AS query_key,
       CONVERT(varchar(20), a.query_hash, 1) AS query_hash, CONVERT(varchar(20), a.query_plan_hash, 1) AS plan_hash,
       a.execs, a.avg_cpu_us / 1000.0 AS avg_cpu_ms, a.avg_dur_us / 1000.0 AS avg_elapsed_ms,
       CAST(a.avg_reads AS bigint) AS avg_reads, CAST(a.max_reads AS bigint) AS max_reads,
       CAST(a.last_exec AS datetime2) AS last_exec, a.flag_value,
       LEFT(qt.query_sql_text, ?) AS sql_text, 'QS' AS source
FROM agg a
JOIN sys.query_store_query      q  ON q.query_id = a.query_id
JOIN sys.query_store_query_text qt ON qt.query_text_id = q.query_text_id
ORDER BY {order_expr} DESC
OPTION (RECOMPILE);
"""

_WEIGHTED_AVG_DUR = "(SUM(rs.avg_duration * rs.count_executions) / SUM(rs.count_executions))"
_WEIGHTED_AVG_CPU = "(SUM(rs.avg_cpu_time * rs.count_executions) / SUM(rs.count_executions))"

_KIND_SHAPES = {
    "VARIANCE": {
        "order_expr": "flag_value",
        "kind_having": f"AND MAX(rs.max_duration) > 5 * {_WEIGHTED_AVG_DUR}",
        "flag_expr": f"MAX(rs.max_duration) * 1.0 / {_WEIGHTED_AVG_DUR}",
        "extra_join": "",
    },
    "SNIFFING": {
        "order_expr": "flag_value",
        "kind_having": "AND (SELECT COUNT(*) FROM sys.query_store_plan p2 WHERE p2.query_id = p.query_id) > 1",
        "flag_expr": "(SELECT COUNT(*) FROM sys.query_store_plan p2 WHERE p2.query_id = p.query_id)",
        "extra_join": "",
    },
    "SPILLS_GRANTS": {
        "order_expr": "flag_value",
        "kind_having": "AND MAX(rs.avg_tempdb_space_used) > 0",
        "flag_expr": "MAX(rs.avg_tempdb_space_used)",
        "extra_join": "",
    },
    "COMPILE_HEAVY": {
        "order_expr": "flag_value",
        "kind_having": f"AND MAX(q.avg_compile_duration) > {_WEIGHTED_AVG_CPU}",
        "flag_expr": "MAX(q.avg_compile_duration) / 1000.0",
        "extra_join": "",
    },
    "REGRESSION": {
        "order_expr": "flag_value",
        "kind_having": (
            "AND COUNT(DISTINCT p.plan_id) > 1 "
            f"AND {_WEIGHTED_AVG_CPU} > 2 * MIN(rs.avg_cpu_time)"
        ),
        "flag_expr": f"{_WEIGHTED_AVG_CPU} / NULLIF(MIN(rs.avg_cpu_time), 0)",
        "extra_join": (
            "JOIN (SELECT query_id, MAX(plan_id) plan_id FROM sys.query_store_plan GROUP BY query_id) "
            "latest ON latest.query_id = p.query_id"
        ),
    },
}


def build_qs_list_query(kind: str) -> tuple[str, tuple[str, ...]]:
    if kind not in _KIND_SHAPES:
        raise ValueError(f"Unknown list kind: {kind!r}")
    sql = _TEMPLATE.format(**_KIND_SHAPES[kind])
    return sql, ("min_execs", "since", "top", "max_sql")
