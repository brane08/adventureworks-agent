import pytest
from adventureworks_agent.queries.list_dmv import build_dmv_list_query


@pytest.mark.parametrize(
    "kind", ["TOP_CPU", "TOP_ELAPSED", "TOP_READS", "VARIANCE", "SNIFFING", "SPILLS_GRANTS", "COMPILE_HEAVY"]
)
def test_build_dmv_list_query_known_kinds(kind):
    sql, param_order = build_dmv_list_query(kind)
    assert "dm_exec_query_stats" in sql
    assert "OPTION (RECOMPILE)" in sql
    assert param_order == ("top", "min_execs", "max_sql")
    assert "<order_expr>" not in sql
    assert "<kind_filter>" not in sql
    assert "<flag_expr>" not in sql


def test_build_dmv_list_query_rejects_regression():
    with pytest.raises(ValueError, match="REGRESSION"):
        build_dmv_list_query("REGRESSION")


def test_build_dmv_list_query_rejects_unknown_kind():
    with pytest.raises(ValueError):
        build_dmv_list_query("NOT_A_KIND")


def test_variance_kind_includes_max_elapsed_filter():
    sql, _ = build_dmv_list_query("VARIANCE")
    assert "max_elapsed_time > 5 *" in sql


def test_spills_grants_kind_filters_spills_or_grant_ratio():
    sql, _ = build_dmv_list_query("SPILLS_GRANTS")
    assert "total_spills > 0" in sql
    assert "max_grant_kb > 4 * NULLIF(max_used_grant_kb,0)" in sql
