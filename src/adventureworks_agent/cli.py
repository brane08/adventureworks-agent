import asyncio
import sys

from langchain_core.messages import HumanMessage
from langgraph.errors import GraphRecursionError

from adventureworks_agent.agent import build_agent
from adventureworks_agent.config import load_settings

RECURSION_LIMIT = 60


async def run(question: str, agent) -> str:
    try:
        result = await agent.ainvoke(
            {"messages": [HumanMessage(content=question)]},
            config={"recursion_limit": RECURSION_LIMIT},
        )
    except GraphRecursionError:
        return (
            f"Stopped: the investigation exceeded {RECURSION_LIMIT} agent steps without a final answer. "
            "Try a narrower question (e.g. a specific query or metric)."
        )
    return result["messages"][-1].content


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m adventureworks_agent.cli \"<question>\"")
        sys.exit(1)
    question = sys.argv[1]
    settings = load_settings()

    async def _run():
        async with build_agent(settings.openrouter_api_key, settings.openrouter_model) as agent:
            return await run(question, agent)

    print(asyncio.run(_run()))


if __name__ == "__main__":
    main()
