import os

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

_SRC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "src")
_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


async def build_agent(openrouter_api_key: str, openrouter_model: str):
    client = MultiServerMCPClient(
        {
            "plan_analyzer": {
                "command": "python",
                "args": ["-m", "adventureworks_agent.mcp_server"],
                "transport": "stdio",
                "env": {**os.environ, "PYTHONPATH": _SRC_DIR},
            }
        }
    )
    tools = await client.get_tools()
    model = ChatOpenAI(model=openrouter_model, api_key=openrouter_api_key, base_url=_OPENROUTER_BASE_URL)
    return create_react_agent(model, tools)
