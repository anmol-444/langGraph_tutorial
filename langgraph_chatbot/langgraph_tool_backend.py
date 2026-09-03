from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from langgraph.graph.message import add_messages
from dotenv import load_dotenv

from langgraph.prebuilt import ToolNode, tools_condition
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool

import requests
import random
import sqlite3
import os

load_dotenv()

model = HuggingFaceEndpoint(
    repo_id="meta-llama/Llama-3.1-8B-Instruct",
    task="conversational"
)

llm = ChatHuggingFace(llm = model)

# Tools
search_tool = DuckDuckGoSearchRun(region="us-en")

@tool
def calculator(first_num: float, second_num: float, operation: str) -> dict:
    """
    Perform a basic arithmetic operation on two numbers.
    Supported operations: add, mul, sub, div
    """
    try:
        if operation == "add":
            result = first_num + second_num
        elif operation == 'sub':
            result = first_num - second_num
        elif operation == "mul":
            result = first_num * second_num
        elif operation == "div":
            if second_num == 0:
                return {"error": "Division by zero is not allowed."}
            result = first_num/second_num
        else:
            return {"error": f"Unsupported operation '{operation}'"}
    except Exception as e:
        return {"error": str(e)}

@tool
def get_stock_price(symbol: str) -> dict:
    """
    Fetch latest stock price for a given symbol (e.g. 'AAPL', 'TESLA')
    using Alpha Vantage with API key in the URL.
    """
    url = f""

    r = requests.get(url=url)
    return r.json()

# @tool
# def list_github_prs(owner: str, repo: str, state: str = "open", per_page: int=5,):
#     """
#     List the latest pull request for a gitHub repository.
#     Args:
#         owner: GitHub org or username (e.g., "langgraph-ai")
#         repo: Repository name (e.g., "langgraph")
#         state: "open", "closed", "all"
#         per_page: Number of PRs to fetch (max 100)

#         Returns:
#             A simplified list of PR info dictionaries.
#     """
#     token = os.getenv("GITHUB_TOKEN")
#     headers = {
#         "Accept": "application/vnd.github+json",
#     }
#     if token:
#         headers["Authorization"] = f"Bearer {token}"

#     url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
#     params = {
#         "state": state,
#         "per_page": per_page,
#     }
#     response = requests.get(url=url, headers=headers, params=params, timeout=10)

#     response.raise_for_status()
#     data = response.json()

#     prs = []
#     for pr in data:
#         prs.append({
#             "number": pr["number"],
#             "title": pr["title"],
#             "author": pr["user"]["login"],
#             "state": pr["state"],
#             "url": pr["html_url"],
#         })

#     return prs

SERVERS = {
    "github": {
        "transport": "stdio",
        "command": "/usr/bin/python3",
        "args": [
            "/path/to/github_mcp_server.py"
        ]
    }
}


tools = [get_stock_price, search_tool, calculator]

llm_with_tools = llm.bind_tools(tools)

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def chat_node(state: ChatState):
    """LLM node that may answer or request a tool call."""

    messages = state['message']
    response = llm_with_tools.invoke(messages)
    return {"messages" : [response]}

tool_node = ToolNode(tools=tools)

conn = sqlite3.connect(database="chatbot.db", check_same_thread=False)
checkpointer = SqliteSaver(conn=conn)

graph = StateGraph(ChatState)

graph.add_node("chat_node", chat_node)
graph.add_node("tools", tool_node)

graph.add_edge(START, "chat_node")

graph.add_conditional_edges("chat_node", tools_condition)

graph.add_edge("tools", "chat_node")


chatbot = graph.compile(checkpointer=checkpointer)


def retrieve_all_threads():
    all_threads = set()
    for checkpoint in checkpointer.list(None):
        all_threads.add(checkpointer.config["configurable"]["thread_id"])

    return list(all_threads)