"""
Mock Banking Transactions API
Simulates a real banking API with transactions data.
"""

import json
from datetime import datetime, date
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/transactions", tags=["Transactions"])

# Load mock data once at startup
DATA_PATH = Path(__file__).parent.parent / "data" / "transactions.json"

def load_transactions():
    with open(DATA_PATH) as f:
        return json.load(f)


class Transaction(BaseModel):
    id: int
    user_id: str
    amount: float
    category: str
    merchant: str
    timestamp: str


class TransactionSummary(BaseModel):
    total_spent: float
    transaction_count: int
    top_category: str
    by_category: dict
    period: str


@router.get("/", response_model=list[Transaction])
def get_transactions(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    category: Optional[str] = Query(None, description="Filter by category"),
):
    """Fetch all transactions with optional date and category filters."""
    txns = load_transactions()

    if start:
        txns = [t for t in txns if t["timestamp"] >= start]
    if end:
        txns = [t for t in txns if t["timestamp"] <= end]
    if category:
        txns = [t for t in txns if t["category"].lower() == category.lower()]

    return txns


@router.get("/summary", response_model=TransactionSummary)
def get_summary(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
):
    """Get spending summary with category breakdown."""
    txns = load_transactions()

    if start:
        txns = [t for t in txns if t["timestamp"] >= start]
    if end:
        txns = [t for t in txns if t["timestamp"] <= end]

    if not txns:
        raise HTTPException(status_code=404, detail="No transactions found for the given period.")

    total = round(sum(t["amount"] for t in txns), 2)
    by_category: dict[str, float] = {}
    for t in txns:
        by_category[t["category"]] = round(by_category.get(t["category"], 0) + t["amount"], 2)

    top_category = max(by_category, key=by_category.get)

    period = f"{start or 'all time'} to {end or 'today'}"

    return TransactionSummary(
        total_spent=total,
        transaction_count=len(txns),
        top_category=top_category,
        by_category=by_category,
        period=period,
    )


@router.get("/{transaction_id}", response_model=Transaction)
def get_transaction(transaction_id: int):
    """Get a single transaction by ID."""
    txns = load_transactions()
    for t in txns:
        if t["id"] == transaction_id:
            return t
    raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found.")
