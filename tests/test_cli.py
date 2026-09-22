import pytest
from adventureworks_agent.cli import run


@pytest.mark.asyncio
async def test_run_invokes_agent_and_returns_final_content():
    class FakeAgent:
        async def ainvoke(self, payload):
            return {"messages": [payload["messages"][0], type("Msg", (), {"content": "answer text"})()]}

    result = await run("why is this query slow?", FakeAgent())

    assert result == "answer text"
