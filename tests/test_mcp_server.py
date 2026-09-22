import pytest
from adventureworks_agent import mcp_server


class FakeService:
    def __init__(self):
        self.calls = []

    def detect(self):
        self.calls.append(("detect",))
        return {"source": "DMV", "db": "AdventureWorks2019", "major": 15, "qs_state": None}

    def list(self, kind, metric="CPU", top=10, min_execs=1, since="1900-01-01"):
        self.calls.append(("list", kind, metric, top, min_execs, since))
        return {"rows": []}

    def summary(self, key):
        self.calls.append(("summary", key))
        return {"warnings": []}

    def tree(self, key):
        self.calls.append(("tree", key))
        return {"tree": "#hdr"}

    def operators(self, key):
        self.calls.append(("operators", key))
        return {"rows": []}

    def subtree(self, key, node_id, max_chars=8000):
        self.calls.append(("subtree", key, node_id, max_chars))
        return {"xml": "<RelOp/>"}

    def raw(self, key, max_chars=16000, reason=""):
        self.calls.append(("raw", key, max_chars, reason))
        return {"plan_text": "<QueryPlan/>"}


@pytest.fixture(autouse=True)
def fake_service(monkeypatch):
    svc = FakeService()
    monkeypatch.setattr(mcp_server, "_get_service", lambda: svc)
    return svc


def test_detect_tool_delegates(fake_service):
    result = mcp_server.detect()
    assert result["source"] == "DMV"
    assert fake_service.calls == [("detect",)]


def test_list_queries_tool_delegates(fake_service):
    mcp_server.list_queries(kind="TOP_CPU", top=5)
    assert fake_service.calls[0][0] == "list"
    assert fake_service.calls[0][1] == "TOP_CPU"


def test_summary_tool_delegates(fake_service):
    mcp_server.summary(key="dmv:0x01:0:10")
    assert fake_service.calls == [("summary", "dmv:0x01:0:10")]


def test_tree_tool_delegates(fake_service):
    mcp_server.tree(key="dmv:0x01:0:10")
    assert fake_service.calls == [("tree", "dmv:0x01:0:10")]


def test_operators_tool_delegates(fake_service):
    mcp_server.operators(key="dmv:0x01:0:10")
    assert fake_service.calls == [("operators", "dmv:0x01:0:10")]


def test_subtree_tool_delegates(fake_service):
    mcp_server.subtree(key="dmv:0x01:0:10", node_id=3)
    assert fake_service.calls == [("subtree", "dmv:0x01:0:10", 3, 8000)]


def test_raw_tool_delegates(fake_service):
    mcp_server.raw(key="dmv:0x01:0:10", reason="debug")
    assert fake_service.calls == [("raw", "dmv:0x01:0:10", 16000, "debug")]
