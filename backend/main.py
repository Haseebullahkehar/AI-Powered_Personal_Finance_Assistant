"""
Finance AI Assistant — FastAPI Backend
Main application entry point.
"""

import os
import sys
import uuid
import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
import httpx
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Load environment variables
load_dotenv()

# Ensure backend modules are importable
sys.path.insert(0, str(Path(__file__).parent))

from api.transactions import router as transactions_router
from agent.graph import run_agent
from memory.store import add_message, get_history, clear_history

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Finance AI Assistant",
    description="AI-powered personal finance assistant with RAG, agent reasoning, and transaction analysis.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook-test/finance-chat")

# ─── Mount Routers ────────────────────────────────────────────────────────────
app.include_router(transactions_router)


# ─── Chat Endpoint ────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    tool_used: str | None


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Main chat endpoint. Routes user message through the LangGraph agent.
    Supports multi-turn conversation via session_id.
    """
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured.")

    session_id = req.session_id or str(uuid.uuid4())
    history = get_history(session_id)

    logger.info(f"[{session_id}] User: {req.message[:80]}")

    try:
        result = run_agent(user_message=req.message, history=history)
    except Exception as e:
        logger.error(f"Agent error: {e}")
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    # Persist conversation
    add_message(session_id, "user", req.message)
    add_message(session_id, "assistant", result["response"])

    tool_log = f" [Tool: {result['tool_used']}]" if result["tool_used"] else ""
    logger.info(f"[{session_id}] Assistant{tool_log}: {result['response'][:80]}")

    return ChatResponse(
        response=result["response"],
        session_id=session_id,
        tool_used=result["tool_used"],
    )


@app.delete("/chat/{session_id}")
async def clear_chat(session_id: str):
    """Clear conversation history for a session."""
    clear_history(session_id)
    return {"message": f"Session {session_id} cleared."}


# ─── n8n Webhook Endpoint ──────────────────────────────────────────────────────

class WebhookRequest(BaseModel):
    message: str
    session_id: str | None = None


@app.post("/webhook/chat")
async def n8n_webhook(req: WebhookRequest):
    """
    Webhook endpoint for n8n workflow integration.
    Forwards the request to the n8n test webhook URL.
    """
    payload = {"message": req.message, "session_id": req.session_id}

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(N8N_WEBHOOK_URL, json=payload)
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"n8n webhook error: {str(exc)}")

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    # Pass through n8n response payload
    try:
        return resp.json()
    except ValueError:
        return {"raw_response": resp.text}


# ─── Health Check ─────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
    }


@app.get("/")
def root():
    return {
        "name": "Finance AI Assistant",
        "version": "1.0.0",
        "docs": "/docs",
    }


# ─── Run ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("APP_PORT", 8000)), reload=True)
