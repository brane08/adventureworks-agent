import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

_SRC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "src")
_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_SERVER_NAME = "plan_analyzer"


def _server_env() -> dict[str, str]:
    existing = os.environ.get("PYTHONPATH")
    pythonpath = os.pathsep.join([_SRC_DIR, existing]) if existing else _SRC_DIR
    return {**os.environ, "PYTHONPATH": pythonpath}


@asynccontextmanager
async def build_agent(openrouter_api_key: str, openrouter_model: str) -> AsyncIterator:
    client = MultiServerMCPClient(
        {
            _SERVER_NAME: {
                "command": sys.executable,
                "args": ["-m", "adventureworks_agent.mcp_server"],
                "transport": "stdio",
                "env": _server_env(),
            }
        }
    )
    # One session for the whole run; get_tools() would spawn a new server process per tool call.
    async with client.session(_SERVER_NAME) as session:
        tools = await load_mcp_tools(session)
        model = ChatOpenAI(model=openrouter_model, api_key=openrouter_api_key, base_url=_OPENROUTER_BASE_URL)
        yield create_react_agent(model, tools)
