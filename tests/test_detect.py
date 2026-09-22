from adventureworks_agent.detect import DetectResult, detect


class FakeConn:
    pass


def test_detect_routes_to_qs_when_fully_enabled(monkeypatch):
    def fake_execute(conn, sql, params=()):
        if "database_query_store_options" in sql:
            return [{"actual_state": "READ_WRITE", "readonly_reason": 0, "query_capture_mode": "AUTO"}]
        return [{"major": 15}]

    monkeypatch.setattr("adventureworks_agent.detect.execute", fake_execute)

    result = detect(FakeConn(), "AdventureWorks2019")

    assert result == DetectResult(source="QS", db="AdventureWorks2019", major=15, qs_state="READ_WRITE")


def test_detect_falls_back_to_dmv_when_readonly(monkeypatch):
    def fake_execute(conn, sql, params=()):
        if "database_query_store_options" in sql:
            return [{"actual_state": "READ_ONLY", "readonly_reason": 1, "query_capture_mode": "AUTO"}]
        return [{"major": 15}]

    monkeypatch.setattr("adventureworks_agent.detect.execute", fake_execute)

    result = detect(FakeConn(), "AdventureWorks2019")

    assert result.source == "DMV"


def test_detect_falls_back_to_dmv_when_capture_mode_none(monkeypatch):
    def fake_execute(conn, sql, params=()):
        if "database_query_store_options" in sql:
            return [{"actual_state": "READ_WRITE", "readonly_reason": 0, "query_capture_mode": "NONE"}]
        return [{"major": 15}]

    monkeypatch.setattr("adventureworks_agent.detect.execute", fake_execute)

    assert detect(FakeConn(), "AdventureWorks2019").source == "DMV"


def test_detect_falls_back_to_dmv_when_qs_not_configured(monkeypatch):
    def fake_execute(conn, sql, params=()):
        if "database_query_store_options" in sql:
            return []
        return [{"major": 15}]

    monkeypatch.setattr("adventureworks_agent.detect.execute", fake_execute)

    result = detect(FakeConn(), "AdventureWorks2019")

    assert result.source == "DMV"
    assert result.qs_state is None
