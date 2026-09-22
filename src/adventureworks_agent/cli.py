import asyncio
import sys

from langchain_core.messages import HumanMessage

from adventureworks_agent.agent import build_agent
from adventureworks_agent.config import load_settings


async def run(question: str, agent) -> str:
    result = await agent.ainvoke({"messages": [HumanMessage(content=question)]})
    return result["messages"][-1].content


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m adventureworks_agent.cli \"<question>\"")
        sys.exit(1)
    question = sys.argv[1]
    settings = load_settings()

    async def _run():
        agent = await build_agent(settings.openrouter_api_key, settings.openrouter_model)
        return await run(question, agent)

    print(asyncio.run(_run()))


if __name__ == "__main__":
    main()
