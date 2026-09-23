import pytest
from langgraph.errors import GraphRecursionError

from adventureworks_agent.cli import RECURSION_LIMIT, run


@pytest.mark.asyncio
async def test_run_invokes_agent_and_returns_final_content():
    captured = {}

    class FakeAgent:
        async def ainvoke(self, payload, config=None):
            captured["config"] = config
            return {"messages": [payload["messages"][0], type("Msg", (), {"content": "answer text"})()]}

    result = await run("why is this query slow?", FakeAgent())

    assert result == "answer text"
    assert captured["config"] == {"recursion_limit": RECURSION_LIMIT}


@pytest.mark.asyncio
async def test_run_returns_message_when_recursion_limit_hit():
    class FakeAgent:
        async def ainvoke(self, payload, config=None):
            raise GraphRecursionError("limit")

    result = await run("analyze everything", FakeAgent())

    assert result.startswith("Stopped:")
    assert str(RECURSION_LIMIT) in result
