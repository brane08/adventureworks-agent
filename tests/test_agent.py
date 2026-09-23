import os
import sys
from contextlib import asynccontextmanager

import pytest
from adventureworks_agent import agent as agent_module
from adventureworks_agent.agent import build_agent


@pytest.fixture
def fake_mcp(monkeypatch):
    captured = {"sessions_opened": 0}
    fake_tools = ["tool_a", "tool_b"]

    class FakeMCPClient:
        def __init__(self, servers):
            captured["servers"] = servers

        @asynccontextmanager
        async def session(self, name):
            captured["sessions_opened"] += 1
            captured["session_name"] = name
            yield "fake_session"
            captured["session_closed"] = True

    async def fake_load_mcp_tools(session):
        captured["loaded_from"] = session
        return fake_tools

    def fake_create_react_agent(model, tools):
        captured["tools"] = tools
        return "fake_agent"

    monkeypatch.setattr(agent_module, "MultiServerMCPClient", FakeMCPClient)
    monkeypatch.setattr(agent_module, "load_mcp_tools", fake_load_mcp_tools)
    monkeypatch.setattr(agent_module, "create_react_agent", fake_create_react_agent)
    return captured


@pytest.mark.asyncio
async def test_build_agent_loads_tools_from_one_persistent_session(fake_mcp):
    async with build_agent("sk-or-test", "anthropic/claude-sonnet-5") as agent:
        assert agent == "fake_agent"
        assert fake_mcp["tools"] == ["tool_a", "tool_b"]
        assert fake_mcp["loaded_from"] == "fake_session"
        assert "session_closed" not in fake_mcp

    assert fake_mcp["sessions_opened"] == 1
    assert fake_mcp["session_closed"] is True


@pytest.mark.asyncio
async def test_build_agent_launches_server_with_current_interpreter(fake_mcp):
    async with build_agent("sk-or-test", "anthropic/claude-sonnet-5"):
        pass

    server = fake_mcp["servers"]["plan_analyzer"]
    assert server["command"] == sys.executable


@pytest.mark.asyncio
async def test_build_agent_prepends_src_to_existing_pythonpath(fake_mcp, monkeypatch):
    monkeypatch.setenv("PYTHONPATH", "/opt/extra")

    async with build_agent("sk-or-test", "anthropic/claude-sonnet-5"):
        pass

    parts = fake_mcp["servers"]["plan_analyzer"]["env"]["PYTHONPATH"].split(os.pathsep)
    assert parts == [agent_module._SRC_DIR, "/opt/extra"]
