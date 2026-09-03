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
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

model = HuggingFaceEndpoint(
    repo_id="meta-llama/Llama-3.1-8B-Instruct",
    task="conversational"
)

llm = ChatHuggingFace(llm = model)

client = MultiServerMCPClient(
    {
        "arith": {
            "transport": "stdio",
            "command": "python3",
            "args": ["/langgraph/main.py"],
        }
    }
)


class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


async def build_graph():
    tools = await client.get_tools()

    llm_with_tools = llm.bind_tools(tools)

    async def chat_node(state: ChatState):
        """LLM node that may answer or request a tool call."""

        messages = state['message']
        response = await llm_with_tools.invoke(messages)
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


    chatbot = graph.compile()
    return chatbot

async def main():
    chatbot = await build_graph()
    result = await chatbot.invoke({"messages": [HumanMessage(content="Find the modulus of 132354 and 23 and give answer like a cricket commentater.")]})
    print(result['messages'][-1].content)

if __name__ == '__main__':
    asyncio.run(main())