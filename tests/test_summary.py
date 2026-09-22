import pytest
from adventureworks_agent.db import PlanTooLargeError
from adventureworks_agent.plan_service import PlanService
from adventureworks_agent.keys import encode_dmv_key, encode_qs_key


class FakeConn:
    pass


def _stub_detect(monkeypatch, source):
    monkeypatch.setattr(
        "adventureworks_agent.plan_service.detect",
        lambda conn, db_name: __import__("adventureworks_agent.detect", fromlist=["DetectResult"]).DetectResult(
            source, db_name, 15, None
        ),
    )


def test_summary_dmv_key_on_dmv_source_shreds_plan(monkeypatch):
    _stub_detect(monkeypatch, "DMV")
    captured = {}

    def fake_execute(conn, sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return [{"abort_reason": None, "warnings": [], "missing_indexes": []}]

    monkeypatch.setattr("adventureworks_agent.plan_service.execute", fake_execute)

    svc = PlanService(FakeConn(), "AdventureWorks2019")
    key = encode_dmv_key("0x0500070068C1", 0, 120)

    result = svc.summary(key)

    assert "dm_exec_text_query_plan" in captured["sql"]
    assert "XMLNAMESPACES" in captured["sql"]
    assert result == {"warnings": [], "missing_indexes": []}


def test_summary_qs_key_on_dmv_source_is_source_mismatch(monkeypatch):
    _stub_detect(monkeypatch, "DMV")

    svc = PlanService(FakeConn(), "AdventureWorks2019")
    key = encode_qs_key(1, 1)

    assert svc.summary(key) == {"status": "source_mismatch"}


def test_summary_empty_result_is_not_found(monkeypatch):
    _stub_detect(monkeypatch, "DMV")
    monkeypatch.setattr("adventureworks_agent.plan_service.execute", lambda conn, sql, params=(): [])

    svc = PlanService(FakeConn(), "AdventureWorks2019")
    result = svc.summary(encode_dmv_key("0x01", 0, 10))

    assert result == {"status": "not_found"}


def test_summary_plan_too_large_returns_hint(monkeypatch):
    _stub_detect(monkeypatch, "DMV")

    def raise_too_large(conn, sql, params=()):
        raise PlanTooLargeError("nesting > 128")

    monkeypatch.setattr("adventureworks_agent.plan_service.execute", raise_too_large)

    svc = PlanService(FakeConn(), "AdventureWorks2019")
    result = svc.summary(encode_dmv_key("0x01", 0, 10))

    assert result == {"status": "plan_too_large", "hint": "use raw"}
