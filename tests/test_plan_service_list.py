import pytest
from adventureworks_agent.plan_service import PlanService


class FakeConn:
    pass


def test_detect_is_cached_after_first_call(monkeypatch):
    calls = {"count": 0}

    def fake_detect(conn, db_name):
        calls["count"] += 1
        from adventureworks_agent.detect import DetectResult

        return DetectResult(source="DMV", db=db_name, major=15, qs_state=None)

    monkeypatch.setattr("adventureworks_agent.plan_service.detect", fake_detect)

    svc = PlanService(FakeConn(), "AdventureWorks2019")
    svc.detect()
    svc.detect()

    assert calls["count"] == 1


def test_list_routes_to_dmv_builder_when_source_is_dmv(monkeypatch):
    monkeypatch.setattr(
        "adventureworks_agent.plan_service.detect",
        lambda conn, db_name: __import__("adventureworks_agent.detect", fromlist=["DetectResult"]).DetectResult(
            "DMV", db_name, 15, None
        ),
    )
    captured = {}

    def fake_execute(conn, sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return [{"query_key": "dmv:0x01:0:10", "execs": 5}]

    monkeypatch.setattr("adventureworks_agent.plan_service.execute", fake_execute)

    svc = PlanService(FakeConn(), "AdventureWorks2019")
    result = svc.list("TOP_CPU", top=10, min_execs=1)

    assert result == {"rows": [{"query_key": "dmv:0x01:0:10", "execs": 5}]}
    assert "dm_exec_query_stats" in captured["sql"]
    assert captured["params"] == (10, 1, 300)


def test_list_regression_on_dmv_source_is_unsupported(monkeypatch):
    monkeypatch.setattr(
        "adventureworks_agent.plan_service.detect",
        lambda conn, db_name: __import__("adventureworks_agent.detect", fromlist=["DetectResult"]).DetectResult(
            "DMV", db_name, 15, None
        ),
    )

    svc = PlanService(FakeConn(), "AdventureWorks2019")
    result = svc.list("REGRESSION")

    assert result == {"status": "unsupported_on_source", "rows": []}


def test_list_caps_top_at_20(monkeypatch):
    monkeypatch.setattr(
        "adventureworks_agent.plan_service.detect",
        lambda conn, db_name: __import__("adventureworks_agent.detect", fromlist=["DetectResult"]).DetectResult(
            "DMV", db_name, 15, None
        ),
    )
    captured = {}

    def fake_execute(conn, sql, params=()):
        captured["params"] = params
        return []

    monkeypatch.setattr("adventureworks_agent.plan_service.execute", fake_execute)

    svc = PlanService(FakeConn(), "AdventureWorks2019")
    svc.list("TOP_CPU", top=999)

    assert captured["params"][0] == 20
