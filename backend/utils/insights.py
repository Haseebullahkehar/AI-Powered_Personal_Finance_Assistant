"""
Financial insights calculations — spending summaries, trends, category analysis.
.
"""

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

DATA_PATH = Path(__file__).parent.parent / "data" / "transactions.json"


def load_transactions():
    with open(DATA_PATH) as f:
        return json.load(f)


def filter_by_period(txns: list, start: str, end: str) -> list:
    return [t for t in txns if start <= t["timestamp"] <= end]


def spending_summary(start: str, end: str) -> dict:
    txns = load_transactions()
    period_txns = filter_by_period(txns, start, end)

    if not period_txns:
        return {"total": 0, "count": 0, "by_category": {}, "top_category": None}

    total = round(sum(t["amount"] for t in period_txns), 2)
    by_category: dict[str, float] = {}
    for t in period_txns:
        by_category[t["category"]] = round(by_category.get(t["category"], 0) + t["amount"], 2)

    top_category = max(by_category, key=by_category.get) if by_category else None

    return {
        "total": total,
        "count": len(period_txns),
        "by_category": by_category,
        "top_category": top_category,
        "transactions": period_txns,
    }


def last_week_summary() -> dict:
    today = date.today()
    end = today.isoformat()
    start = (today - timedelta(days=7)).isoformat()
    return {**spending_summary(start, end), "period": "last 7 days", "start": start, "end": end}


def last_month_summary() -> dict:
    today = date.today()
    end = today.isoformat()
    start = (today - timedelta(days=30)).isoformat()
    return {**spending_summary(start, end), "period": "last 30 days", "start": start, "end": end}


def week_over_week_change() -> dict:
    today = date.today()
    this_week_end = today.isoformat()
    this_week_start = (today - timedelta(days=7)).isoformat()
    last_week_end = (today - timedelta(days=8)).isoformat()
    last_week_start = (today - timedelta(days=14)).isoformat()

    this_week = spending_summary(this_week_start, this_week_end)
    prev_week = spending_summary(last_week_start, last_week_end)

    this_total = this_week["total"]
    prev_total = prev_week["total"]

    if prev_total == 0:
        pct_change = None
    else:
        pct_change = round(((this_total - prev_total) / prev_total) * 100, 1)

    return {
        "this_week_total": this_total,
        "prev_week_total": prev_total,
        "pct_change": pct_change,
        "direction": "increased" if (pct_change or 0) > 0 else "decreased",
    }


def format_insights_response(query_type: str) -> str:
    """
    Returns a natural-language financial insights string based on query type.
    Called by the agent tool.
    """
    if query_type == "last_week":
        data = last_week_summary()
        lines = [
            f"Here's your spending summary for the last 7 days:",
            f"- Total spent: PKR {data['total']:,.2f} across {data['count']} transactions",
        ]
        if data["top_category"]:
            lines.append(f"- Top category: {data['top_category']} (PKR {data['by_category'][data['top_category']]:,.2f})")
        for cat, amt in sorted(data["by_category"].items(), key=lambda x: -x[1]):
            lines.append(f"  • {cat}: PKR {amt:,.2f}")
        return "\n".join(lines)

    elif query_type == "last_month":
        data = last_month_summary()
        lines = [
            f"Here's your spending summary for the last 30 days:",
            f"- Total spent: PKR {data['total']:,.2f} across {data['count']} transactions",
        ]
        if data["top_category"]:
            lines.append(f"- Top category: {data['top_category']} (PKR {data['by_category'][data['top_category']]:,.2f})")
        for cat, amt in sorted(data["by_category"].items(), key=lambda x: -x[1]):
            lines.append(f"  • {cat}: PKR {amt:,.2f}")
        return "\n".join(lines)

    elif query_type == "comparison":
        data = week_over_week_change()
        lines = [
            f"Week-over-week spending comparison:",
            f"- This week: PKR {data['this_week_total']:,.2f}",
            f"- Last week: PKR {data['prev_week_total']:,.2f}",
        ]
        if data["pct_change"] is not None:
            lines.append(f"- Your spending {data['direction']} by {abs(data['pct_change'])}% compared to last week.")
        return "\n".join(lines)

    return "I could not compute that insight."
