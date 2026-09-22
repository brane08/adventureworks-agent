import pytest
from adventureworks_agent.plan_service import PlanService
from adventureworks_agent.keys import encode_dmv_key


class FakeConn:
    pass


def _stub_detect(monkeypatch, source="DMV"):
    monkeypatch.setattr(
        "adventureworks_agent.plan_service.detect",
        lambda conn, db_name: __import__("adventureworks_agent.detect", fromlist=["DetectResult"]).DetectResult(
            source, db_name, 15, None
        ),
    )


def test_operators_returns_rows(monkeypatch):
    _stub_detect(monkeypatch)
    monkeypatch.setattr(
        "adventureworks_agent.plan_service.execute",
        lambda conn, sql, params=(): [{"node_id": 1, "op": "NL"}],
    )

    svc = PlanService(FakeConn(), "AdventureWorks2019")
    result = svc.operators(encode_dmv_key("0x01", 0, 10))

    assert result == {"rows": [{"node_id": 1, "op": "NL"}]}


def test_subtree_caps_max_chars_at_8000(monkeypatch):
    _stub_detect(monkeypatch)
    captured = {}

    def fake_execute(conn, sql, params=()):
        captured["params"] = params
        return [{"xml": "<RelOp/>"}]

    monkeypatch.setattr("adventureworks_agent.plan_service.execute", fake_execute)

    svc = PlanService(FakeConn(), "AdventureWorks2019")
    svc.subtree(encode_dmv_key("0x01", 0, 10), node_id=3, max_chars=99999)

    assert captured["params"][-1] == 8000


def test_subtree_not_found_when_node_missing(monkeypatch):
    _stub_detect(monkeypatch)
    monkeypatch.setattr("adventureworks_agent.plan_service.execute", lambda conn, sql, params=(): [])

    svc = PlanService(FakeConn(), "AdventureWorks2019")
    result = svc.subtree(encode_dmv_key("0x01", 0, 10), node_id=999)

    assert result == {"status": "not_found"}


def test_raw_caps_max_chars_at_16000_and_logs_reason(monkeypatch, caplog):
    _stub_detect(monkeypatch)
    captured = {}

    def fake_execute(conn, sql, params=()):
        captured["params"] = params
        return [{"plan_text": "<QueryPlan/>"}]

    monkeypatch.setattr("adventureworks_agent.plan_service.execute", fake_execute)

    svc = PlanService(FakeConn(), "AdventureWorks2019")
    with caplog.at_level("INFO"):
        result = svc.raw(encode_dmv_key("0x01", 0, 10), max_chars=99999, reason="investigating spill")

    assert captured["params"][-1] == 16000
    assert result == {"plan_text": "<QueryPlan/>"}
    assert "investigating spill" in caplog.text


def test_raw_source_mismatch(monkeypatch):
    _stub_detect(monkeypatch, source="QS")

    svc = PlanService(FakeConn(), "AdventureWorks2019")
    result = svc.raw(encode_dmv_key("0x01", 0, 10))

    assert result == {"status": "source_mismatch"}
