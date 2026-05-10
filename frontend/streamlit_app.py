"""
Finance AI Assistant — Streamlit Frontend
A clean chat UI that communicates with the FastAPI backend.
"""

import streamlit as st
import requests
import uuid
from datetime import datetime

# ─── Config ──────────────────────────────────────────────────────────────────
BACKEND_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Finance AI Assistant",
    page_icon="💰",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .stApp { background-color: #0f1117; }

    .main-header {
        text-align: center;
        padding: 1.5rem 0 0.5rem 0;
        color: #ffffff;
    }
    .main-header h1 { font-size: 1.8rem; font-weight: 700; margin: 0; }
    .main-header p  { color: #8b9ab0; font-size: 0.9rem; margin-top: 0.3rem; }

    .chat-message {
        padding: 0.9rem 1.1rem;
        border-radius: 12px;
        margin: 0.4rem 0;
        max-width: 85%;
        line-height: 1.55;
        font-size: 0.92rem;
    }
    .user-message {
        background: #1e6eff22;
        border: 1px solid #1e6eff44;
        color: #d0e4ff;
        margin-left: auto;
        margin-right: 0;
    }
    .assistant-message {
        background: #1a1d26;
        border: 1px solid #2a2d3a;
        color: #e2e8f0;
        margin-left: 0;
        margin-right: auto;
    }
    .tool-badge {
        display: inline-block;
        font-size: 0.7rem;
        padding: 2px 8px;
        border-radius: 999px;
        margin-bottom: 6px;
        font-weight: 600;
        letter-spacing: 0.03em;
    }
    .tool-transactions { background: #1a4a2e; color: #4ade80; border: 1px solid #4ade8044; }
    .tool-rag          { background: #2a1a4a; color: #c084fc; border: 1px solid #c084fc44; }
    .tool-general      { background: #1a2a4a; color: #60a5fa; border: 1px solid #60a5fa44; }

    .stTextInput > div > div > input {
        background: #1a1d26;
        border: 1px solid #2a2d3a;
        color: #e2e8f0;
        border-radius: 10px;
    }
    .stButton > button {
        background: #1e6eff;
        color: white;
        border: none;
        border-radius: 10px;
        font-weight: 600;
        padding: 0.45rem 1.2rem;
    }
    .stButton > button:hover { background: #1a5fdd; }

    .sidebar-section {
        background: #1a1d26;
        border: 1px solid #2a2d3a;
        border-radius: 10px;
        padding: 0.9rem;
        margin-bottom: 0.8rem;
    }
    .sidebar-section h4 { color: #8b9ab0; font-size: 0.75rem; text-transform: uppercase;
                          letter-spacing: 0.08em; margin: 0 0 0.6rem 0; }
    .example-query {
        color: #a0aec0;
        font-size: 0.82rem;
        padding: 0.35rem 0;
        border-bottom: 1px solid #2a2d3a;
        cursor: pointer;
    }
    .example-query:last-child { border-bottom: none; }

    div[data-testid="stMarkdownContainer"] p { margin: 0; }
</style>
""", unsafe_allow_html=True)


# ─── Session State ────────────────────────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_query" not in st.session_state:
    st.session_state.pending_query = ""


# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 💰 Finance Assistant")
    st.markdown(f"<small style='color:#4a5568'>Session: `{st.session_state.session_id[:8]}...`</small>",
                unsafe_allow_html=True)
    st.divider()

    st.markdown('<div class="sidebar-section"><h4>Try These Queries</h4>', unsafe_allow_html=True)

    example_groups = {
        "📊 Spending": [
            "How much did I spend last week?",
            "What was my top spending category?",
            "Show me my last 10 transactions",
            "How does this week compare to last week?",
            "What did I spend on food this month?",
        ],
        "💡 Financial Advice": [
            "What is the 50/30/20 rule?",
            "How can I save more money?",
            "Give me a budgeting strategy",
            "What is compound interest?",
            "How do I build an emergency fund?",
        ],
    }

    for group, queries in example_groups.items():
        st.markdown(f"**{group}**")
        for q in queries:
            if st.button(q, key=f"btn_{q}", use_container_width=True):
                st.session_state.pending_query = q
        st.markdown("---")

    if st.button("🗑️ Clear Conversation", use_container_width=True):
        try:
            requests.delete(f"{BACKEND_URL}/chat/{st.session_state.session_id}", timeout=3)
        except Exception:
            pass
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

    # Backend status
    st.divider()
    try:
        health = requests.get(f"{BACKEND_URL}/health", timeout=2).json()
        if health.get("status") == "ok":
            st.success("✅ Backend connected")
            if not health.get("openai_configured"):
                st.warning("⚠️ OPENAI_API_KEY not set")
        else:
            st.error("❌ Backend error")
    except Exception:
        st.error("❌ Backend offline\nStart: `uvicorn main:app`")


# ─── Main Header ──────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
  <h1>💰 Personal Finance Assistant</h1>
  <p>Ask about your spending, get financial advice, or analyze your transactions.</p>
</div>
""", unsafe_allow_html=True)

st.divider()


# ─── Chat History ─────────────────────────────────────────────────────────────
def tool_badge(tool_used):
    if not tool_used:
        return '<span class="tool-badge tool-general">💬 General</span>'
    if "transaction" in tool_used or "spending" in tool_used:
        return '<span class="tool-badge tool-transactions">📊 Transactions Tool</span>'
    if "advice" in tool_used or "rag" in tool_used:
        return '<span class="tool-badge tool-rag">📚 RAG Tool</span>'
    return f'<span class="tool-badge tool-general">🔧 {tool_used}</span>'


chat_container = st.container()

with chat_container:
    if not st.session_state.messages:
        st.markdown("""
        <div style="text-align:center; padding: 2rem; color: #4a5568;">
            <div style="font-size: 2.5rem; margin-bottom: 0.5rem">👋</div>
            <p style="font-size:1rem; color:#6b7280;">Ask me anything about your finances!</p>
            <p style="font-size:0.82rem; color:#4a5568;">Try: "How much did I spend last week?" or "Give me saving tips"</p>
        </div>
        """, unsafe_allow_html=True)

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(
                f'<div style="display:flex; justify-content:flex-end">'
                f'<div class="chat-message user-message">🧑 {msg["content"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            badge = tool_badge(msg.get("tool_used"))
            content_html = msg["content"].replace("\n", "<br>")
            st.markdown(
                f'<div class="chat-message assistant-message">'
                f'{badge}<br>'
                f'🤖 {content_html}'
                f'</div>',
                unsafe_allow_html=True,
            )


# ─── Input Area ───────────────────────────────────────────────────────────────
def send_message(user_input: str):
    if not user_input.strip():
        return

    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.spinner("Thinking..."):
        try:
            resp = requests.post(
                f"{BACKEND_URL}/chat",
                json={"message": user_input, "session_id": st.session_state.session_id},
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                st.session_state.session_id = data["session_id"]
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": data["response"],
                    "tool_used": data.get("tool_used"),
                })
            else:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"❌ Error {resp.status_code}: {resp.text}",
                    "tool_used": None,
                })
        except requests.exceptions.ConnectionError:
            st.session_state.messages.append({
                "role": "assistant",
                "content": "❌ Cannot connect to backend. Make sure the FastAPI server is running:\n`cd backend && uvicorn main:app --reload`",
                "tool_used": None,
            })
        except Exception as e:
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"❌ Unexpected error: {str(e)}",
                "tool_used": None,
            })


# Handle sidebar button clicks
if st.session_state.pending_query:
    query = st.session_state.pending_query
    st.session_state.pending_query = ""
    send_message(query)
    st.rerun()

# Bottom input
col1, col2 = st.columns([5, 1])
with col1:
    user_input = st.text_input(
        "Message",
        placeholder="Ask about your finances...",
        label_visibility="collapsed",
        key="chat_input",
    )
with col2:
    send_btn = st.button("Send", use_container_width=True)

if send_btn and user_input:
    send_message(user_input)
    st.rerun()

# Also send on Enter key via form trick
if user_input and user_input != st.session_state.get("_last_input", ""):
    st.session_state._last_input = user_input
