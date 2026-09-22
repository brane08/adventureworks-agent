import pytest
from adventureworks_agent.agent import build_agent


@pytest.mark.asyncio
async def test_build_agent_wires_mcp_tools_into_react_agent(monkeypatch):
    fake_tools = ["tool_a", "tool_b"]

    class FakeMCPClient:
        def __init__(self, servers):
            self.servers = servers

        async def get_tools(self):
            return fake_tools

    captured = {}

    def fake_create_react_agent(model, tools):
        captured["model"] = model
        captured["tools"] = tools
        return "fake_agent"

    monkeypatch.setattr("adventureworks_agent.agent.MultiServerMCPClient", FakeMCPClient)
    monkeypatch.setattr("adventureworks_agent.agent.create_react_agent", fake_create_react_agent)

    agent = await build_agent("sk-or-test", "anthropic/claude-sonnet-5")

    assert agent == "fake_agent"
    assert captured["tools"] == fake_tools
