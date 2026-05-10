"""
LangGraph AI Agent — intelligently routes queries to:
  1. Transactions API tool (spending queries)
  2. RAG tool (financial advice queries)
  3. Direct LLM response (general chat)

No hardcoded if/else routing — the LLM decides which tool to call.
"""

import os
import json
import sys
from pathlib import Path
from datetime import date, timedelta
from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, add_messages
from langgraph.prebuilt import ToolNode

# Add parent to path so relative imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.insights import (
    last_week_summary,
    last_month_summary,
    week_over_week_change,
    spending_summary,
    load_transactions,
)
from rag.retriever import query_rag


# ─── Tool Definitions ────────────────────────────────────────────────────────

@tool
def get_spending_summary(period: str = "last_week") -> str:
    """
    Retrieve the user's transaction and spending data.
    Use this for queries about:
    - How much the user spent (total, by category)
    - Transaction history
    - Top spending categories
    - Spending trends and comparisons

    Args:
        period: One of 'last_week', 'last_month', or 'comparison' (week-over-week)
    """
    if period == "last_week":
        data = last_week_summary()
        result = {
            "period": "Last 7 days",
            "total_spent": data["total"],
            "transaction_count": data["count"],
            "by_category": data["by_category"],
            "top_category": data["top_category"],
        }
    elif period == "last_month":
        data = last_month_summary()
        result = {
            "period": "Last 30 days",
            "total_spent": data["total"],
            "transaction_count": data["count"],
            "by_category": data["by_category"],
            "top_category": data["top_category"],
        }
    elif period == "comparison":
        data = week_over_week_change()
        result = {
            "this_week_total": data["this_week_total"],
            "prev_week_total": data["prev_week_total"],
            "percent_change": data["pct_change"],
            "direction": data["direction"],
        }
    else:
        result = {"error": f"Unknown period: {period}. Use 'last_week', 'last_month', or 'comparison'."}

    return json.dumps(result, indent=2)


@tool
def get_all_transactions(limit: int = 10) -> str:
    """
    Fetch the raw list of recent transactions.
    Use this when the user asks to 'show', 'list', or 'categorize' their transactions.

    Args:
        limit: Number of recent transactions to return (default 10, max 25)
    """
    txns = load_transactions()
    # Sort by date descending
    txns = sorted(txns, key=lambda t: t["timestamp"], reverse=True)
    txns = txns[:min(limit, 25)]
    return json.dumps(txns, indent=2)


@tool
def get_financial_advice(question: str) -> str:
    """
    Answer financial advice, budgeting, and savings questions using the RAG knowledge base.
    Use this for queries about:
    - Budgeting strategies and tips
    - How to save money
    - Investment basics
    - Financial literacy concepts (compound interest, debt, net worth, etc.)
    - Questions that ask for advice, suggestions, or strategies

    Args:
        question: The user's financial question
    """
    return query_rag(question)


# ─── Agent State ─────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


# ─── Build LangGraph ─────────────────────────────────────────────────────────

TOOLS = [get_spending_summary, get_all_transactions, get_financial_advice]

SYSTEM_PROMPT = """You are a helpful Personal Finance Assistant. You help users track spending, analyze transactions, and receive financial advice.

You have access to three tools:
1. get_spending_summary — for questions about spending totals, categories, or trends
2. get_all_transactions — for listing or categorizing recent transactions  
3. get_financial_advice — for budgeting tips, saving strategies, and financial literacy questions

Guidelines:
- Always use tools when you need data — do not guess or make up numbers
- For spending questions, always call get_spending_summary or get_all_transactions
- For advice/strategy questions, always call get_financial_advice
- For greetings or meta questions, respond directly without tools
- After receiving tool results, provide a clear, friendly, well-formatted response
- Use PKR as the currency when presenting amounts
- Be concise but thorough"""


def get_llm():
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.2,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    ).bind_tools(TOOLS)


def agent_node(state: AgentState):
    """Main reasoning node — LLM decides whether to call tools or respond."""
    messages = state["messages"]

    # Prepend system message if not already there
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages

    llm = get_llm()
    response = llm.invoke(messages)
    return {"messages": [response]}


def should_continue(state: AgentState) -> str:
    """Route: if last message has tool calls → run tools, else end."""
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return END


def build_agent():
    tool_node = ToolNode(TOOLS)

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)

    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile()


# ─── Public Interface ─────────────────────────────────────────────────────────

_agent = None


def get_agent():
    global _agent
    if _agent is None:
        _agent = build_agent()
    return _agent


def run_agent(user_message: str, history: list[dict] | None = None) -> dict:
    """
    Run the agent with a user message and optional conversation history.

    Args:
        user_message: The latest user query
        history: List of {"role": "user"|"assistant", "content": "..."} dicts

    Returns:
        {"response": str, "tool_used": str | None}
    """
    messages = []

    # Reconstruct conversation history
    if history:
        for turn in history:
            if turn["role"] == "user":
                messages.append(HumanMessage(content=turn["content"]))
            elif turn["role"] == "assistant":
                messages.append(AIMessage(content=turn["content"]))

    messages.append(HumanMessage(content=user_message))

    agent = get_agent()
    result = agent.invoke({"messages": messages})

    final_messages = result["messages"]
    response_text = ""
    tool_used = None

    # Extract tool used (if any) for logging/display
    for msg in final_messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            tool_used = msg.tool_calls[0]["name"]

    # Last message is always the final AI response
    last = final_messages[-1]
    if hasattr(last, "content"):
        response_text = last.content

    return {"response": response_text, "tool_used": tool_used}
