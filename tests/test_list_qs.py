import pytest
from adventureworks_agent.queries.list_qs import build_qs_list_query


@pytest.mark.parametrize(
    "kind", ["VARIANCE", "SNIFFING", "SPILLS_GRANTS", "COMPILE_HEAVY", "REGRESSION"]
)
def test_build_qs_list_query_known_kinds(kind):
    sql, param_order = build_qs_list_query(kind)
    assert "query_store_runtime_stats" in sql
    assert param_order == ("min_execs", "since", "top", "max_sql")
    assert "<kind_having>" not in sql
    assert "<flag_expr>" not in sql
    assert "<extra_join>" not in sql


def test_build_qs_list_query_rejects_unknown_kind():
    with pytest.raises(ValueError):
        build_qs_list_query("NOT_A_KIND")


def test_regression_kind_has_extra_join_and_multi_plan_filter():
    sql, _ = build_qs_list_query("REGRESSION")
    assert "GROUP BY query_id" in sql
    assert "COUNT(DISTINCT p.plan_id) > 1" in sql


def test_averages_are_execution_weighted():
    sql, _ = build_qs_list_query("VARIANCE")
    assert "SUM(rs.avg_cpu_time * rs.count_executions) / SUM(rs.count_executions)" in sql
