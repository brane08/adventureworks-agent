from adventureworks_agent.keys import DmvKey, QsKey

_NAMESPACE = (
    ";WITH XMLNAMESPACES (DEFAULT 'http://schemas.microsoft.com/sqlserver/2004/07/showplan')"
)


def build_src_cte(key, as_text: bool = False) -> tuple[str, tuple]:
    alias = "src_text" if as_text else "src"
    select_expr = "query_plan" if as_text else "CONVERT(xml, query_plan) x"
    if isinstance(key, DmvKey):
        cte = (
            f"{_NAMESPACE}, {alias} AS ("
            f"SELECT {select_expr} FROM sys.dm_exec_text_query_plan(CONVERT(varbinary(64), ?, 1),?,?) "
            "WHERE query_plan IS NOT NULL)"
        )
        return cte, (key.plan_handle, key.start_offset, key.end_offset)
    if isinstance(key, QsKey):
        cte = (
            f"{_NAMESPACE}, {alias} AS ("
            f"SELECT {select_expr} FROM sys.query_store_plan "
            "WHERE plan_id = ? AND query_plan IS NOT NULL)"
        )
        return cte, (key.plan_id,)
    raise ValueError(f"Unsupported key type: {type(key)!r}")


SUMMARY_SELECT = """
SELECT
    (SELECT TOP 1 x.value('(//StmtSimple/@StatementOptmEarlyAbortReason)[1]', 'varchar(100)') FROM src) AS abort_reason,
    (SELECT TOP 20 w.value('local-name(.)', 'varchar(100)') AS w FROM src CROSS APPLY x.nodes('//Warnings/*') t(w) FOR JSON PATH) AS warnings,
    (SELECT TOP 10 mig.query('.') AS m FROM src CROSS APPLY x.nodes('//MissingIndexGroup') t(mig) FOR JSON PATH) AS missing_indexes,
    (SELECT TOP 15 r.value('@NodeId', 'int') AS node_id,
            r.value('@EstimateRows', 'float') AS est,
            r.value('sum(RunTimeInformation/RunTimeCountersPerThread/@ActualRows)', 'float') AS act
     FROM src CROSS APPLY x.nodes('//RelOp') t(r) FOR JSON PATH) AS cardinality_skew,
    (SELECT TOP 40 r.value('@NodeId', 'int') AS node_id,
            r.value('@PhysicalOp', 'varchar(50)') AS op,
            r.value('@EstimatedTotalSubtreeCost', 'float') AS cost
     FROM src CROSS APPLY x.nodes('//RelOp') t(r) ORDER BY cost DESC FOR JSON PATH) AS hotspots,
    (SELECT TOP 1 x.value('(//QueryPlan/@CompileTime)[1]', 'int') AS compile_ms FROM src FOR JSON PATH) AS compile,
    (SELECT TOP 20 p.value('@ParameterCompiledValue', 'varchar(100)') AS compiled,
            p.value('@ParameterRuntimeValue', 'varchar(100)') AS runtime
     FROM src CROSS APPLY x.nodes('//ParameterList/ColumnReference') t(p) FOR JSON PATH) AS sniffing,
    (SELECT TOP 1 g.query('.') AS grant_xml FROM src CROSS APPLY x.nodes('//MemoryGrantInfo') t(g) FOR JSON PATH) AS memory,
    (SELECT TOP 10 s.value('@ModificationCount', 'int') AS mods
     FROM src CROSS APPLY x.nodes('//OptimizerStatsUsage/StatisticsInfo') t(s) FOR JSON PATH) AS columnstore
"""

TREE_SELECT = """
SELECT
    (SELECT TOP 1 x.value('(//QueryPlan/@EstimatedTotalSubtreeCost)[1]', 'float') FROM src) AS stmt_cost,
    (SELECT TOP 1 x.value('(//QueryPlan/@DegreeOfParallelism)[1]', 'int') FROM src) AS dop,
    (SELECT TOP 1 x.value('(//StmtSimple/QueryPlan/@NonParallelPlanReason)[1]', 'varchar(50)') FROM src) AS optm_level,
    (SELECT TOP 1 x.value('(//StmtSimple/@QueryHash)[1]', 'varchar(20)') FROM src) AS plan_hash
"""

TREE_ROWS_SELECT = """
SELECT
    nid.node_id,
    d.depth,
    r.value('@PhysicalOp', 'varchar(50)') AS op_code,
    r.value('@EstimatedExecutionMode', 'varchar(10)') AS mode,
    r.value('(*/Object/@Table)[1]', 'varchar(200)') AS table_alias,
    r.value('local-name((IndexScan/SeekPredicates)[1])', 'varchar(20)') AS access_kind,
    r.value('@EstimateRows', 'float') AS est,
    r.value('sum(RunTimeInformation/RunTimeCountersPerThread/@ActualRows)', 'float') AS act,
    CAST(r.value('@EstimatedTotalSubtreeCost', 'float') /
         NULLIF((SELECT TOP 1 x.value('(//QueryPlan/@EstimatedTotalSubtreeCost)[1]', 'float') FROM src), 0) * 100 AS int) AS cost_pct,
    r.value('local-name((Warnings/*)[1])', 'varchar(50)') AS warning,
    r.value('(IndexScan/SeekPredicates//ScalarOperator/@ScalarString)[1]', 'varchar(200)') AS predicate,
    CAST(0 AS bit) AS prunable
FROM src CROSS APPLY x.nodes('//RelOp') t(r)
CROSS APPLY (SELECT r.value('@NodeId', 'int') AS node_id) nid
CROSS APPLY (
    SELECT COUNT(*) AS depth
    FROM src CROSS APPLY x.nodes('//RelOp') t2(r2)
    WHERE r2.exist('.//RelOp[@NodeId=sql:column("nid.node_id")]') = 1
) d
ORDER BY node_id
"""

OPERATORS_SELECT = """
SELECT TOP 40
    r.value('@NodeId', 'int') AS node_id,
    r.value('@PhysicalOp', 'varchar(50)') AS physical_op,
    r.value('@LogicalOp', 'varchar(50)') AS logical_op,
    r.value('@EstimateRows', 'float') AS est_rows,
    r.value('@EstimatedTotalSubtreeCost', 'float') AS subtree_cost,
    r.value('@EstimatedExecutionMode', 'varchar(10)') AS mode
FROM src CROSS APPLY x.nodes('//RelOp') t(r)
ORDER BY subtree_cost DESC
"""

SUBTREE_SELECT_TEMPLATE = """
SELECT LEFT(CONVERT(nvarchar(max), r.query('.')), ?) AS xml
FROM src CROSS APPLY x.nodes('//RelOp[@NodeId=sql:variable("@node_id")]') t(r)
"""

RAW_SELECT = "SELECT LEFT(query_plan, ?) AS plan_text FROM src_text WHERE query_plan IS NOT NULL"
