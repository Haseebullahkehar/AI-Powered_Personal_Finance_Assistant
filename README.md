# 💰 AI-Powered Personal Finance Assistant

An intelligent finance assistant that lets users track spending, analyze transactions, and receive financial advice — all through natural language.

Built with **FastAPI**, **LangGraph**, **LangChain**, **ChromaDB**, **n8n**, and **Streamlit**.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interfaces                          │
│           Streamlit Chat UI  ←──────────→  n8n Webhook          │
└────────────────────────┬────────────────────────┬───────────────┘
                         │                        │
                         ▼                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                              │
│   POST /chat     POST /webhook/chat     GET /api/transactions   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   LangGraph AI Agent                            │
│                                                                 │
│   User Query → LLM (GPT-4o-mini) → Decides which tool to use   │
│                                                                 │
│         ┌──────────────┬──────────────┬──────────────┐         │
│         ▼              ▼              ▼              │         │
│  Transactions    Financial Advice   Direct LLM       │         │
│     Tool            (RAG) Tool      Response         │         │
│         │              │                             │         │
│         ▼              ▼                             │         │
│   Mock Banking    ChromaDB Vector                    │         │
│      API           Database                          │         │
│  (JSON dataset)  (Finance Docs)                      │         │
└─────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│               Conversation Memory                               │
│        In-memory session store (multi-turn support)            │
└─────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

| Decision | Rationale |
|---|---|
| **LangGraph over plain LangChain agent** | Explicit state graph gives cleaner control flow and easier debugging |
| **No hardcoded routing** | The LLM reads tool descriptions and decides — more robust to query variations |
| **ChromaDB with persisted store** | Embeddings are built once and reused across restarts |
| **FastAPI + Streamlit** | FastAPI handles all logic; Streamlit is a thin UI layer only |
| **Mock API as JSON + FastAPI routes** | Clean separation of data and API layer; easily swappable with real bank APIs |
| **Session-based memory** | Simple in-memory store avoids Redis dependency while still supporting multi-turn |

---

## 📁 Project Structure

```
finance-ai-assistant/
│
├── backend/
│   ├── main.py                  # FastAPI app, chat + webhook endpoints
│   ├── agent/
│   │   └── graph.py             # LangGraph agent + tool definitions
│   ├── rag/
│   │   └── retriever.py         # ChromaDB ingestion + RetrievalQA chain
│   ├── api/
│   │   └── transactions.py      # Mock banking API routes
│   ├── memory/
│   │   └── store.py             # Session-based conversation memory
│   ├── utils/
│   │   └── insights.py          # Financial calculation functions
│   └── data/
│       ├── transactions.json    # Mock transaction dataset (25 records)
│       ├── budgeting_tips.txt   # RAG document: budgeting strategies
│       ├── saving_strategies.txt# RAG document: saving techniques
│       └── financial_literacy.txt# RAG document: financial concepts
│
├── frontend/
│   └── streamlit_app.py         # Streamlit chat interface
│
├── n8n/
│   └── workflow.json            # Exportable n8n workflow
│
├── docs/
│
├── requirements.txt
├── .env.example
└── README.md
```

---

## ⚙️ Setup Instructions

### 1. Clone and Install

```bash
git clone https://github.com/YOUR_USERNAME/ai-finance-assistant
cd ai-finance-assistant

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set your OpenAI API key:
```
OPENAI_API_KEY=sk-your-key-here
```

### 3. Start the Backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

### 4. Start the Frontend

In a new terminal:
```bash
cd frontend
streamlit run streamlit_app.py
```

Open: http://localhost:8501

### 5. Import n8n Workflow (Optional)

1. Open your n8n instance (http://localhost:5678)
2. Go to **Workflows → Import from File**
3. Select `n8n/workflow.json`
4. Activate the workflow
5. Test via: `POST http://localhost:5678/webhook/finance-chat`

---

## 🤖 Agent Routing Logic

The agent uses **zero hardcoded routing**. The LLM reads tool descriptions and decides:

| User Query | Tool Selected | Why |
|---|---|---|
| "How much did I spend last week?" | `get_spending_summary` | Spending data query |
| "Show me my transactions" | `get_all_transactions` | List/categorize request |
| "What is the 50/30/20 rule?" | `get_financial_advice` | Knowledge/advice query |
| "How can I save more money?" | `get_financial_advice` | Strategy question → RAG |
| "Hello, what can you do?" | Direct LLM | No tool needed |

---

## 🔌 API Reference

### Chat Endpoint
```
POST /chat
{
  "message": "How much did I spend last week?",
  "session_id": "optional-uuid"
}

Response:
{
  "response": "Here's your spending summary...",
  "session_id": "abc-123",
  "tool_used": "get_spending_summary"
}
```

### Transactions API
```
GET /api/transactions                        # All transactions
GET /api/transactions?start=2026-05-01&end=2026-05-07
GET /api/transactions?category=Food
GET /api/transactions/summary
GET /api/transactions/{id}
```

### n8n Webhook
```
POST /webhook/chat
{
  "message": "Give me a budget summary",
  "session_id": "n8n-session-1"
}
```

---

## 💬 Example Queries

**Spending Analysis:**
- "How much did I spend last week?"
- "What's my top spending category?"
- "Show me my last 10 transactions"
- "How does this week compare to last week?"
- "What did I spend on food this month?"

**Financial Advice (RAG):**
- "What is the 50/30/20 budgeting rule?"
- "How can I save more money?"
- "Explain compound interest"
- "How do I build an emergency fund?"
- "What is a sinking fund?"

**Multi-turn (Context-Aware):**
```
User: How much did I spend last week?
Assistant: You spent PKR 1,234 across 8 transactions...

User: What was my top category?
Assistant: [Remembers context] Your top category was Food at PKR 450...
```

---

## 📊 RAG Knowledge Base

Three financial documents are ingested into ChromaDB:

| Document | Content |
|---|---|
| `budgeting_tips.txt` | 50/30/20 rule, zero-based budgeting, envelope method, tracking strategies |
| `saving_strategies.txt` | Emergency fund, automation, sinking funds, windfall management |
| `financial_literacy.txt` | Compound interest, inflation, net worth, good vs bad debt, investment basics |

Documents are chunked (600 chars, 80 overlap), embedded with OpenAI embeddings, and stored in a persisted ChromaDB instance.

---

## 🏆 Bonus Features Implemented

- ✅ **Conversation Memory** — Session-based multi-turn context
- ✅ **Agent Reasoning Logs** — `tool_used` field in every response
- ✅ **n8n Scheduled Workflow** — Weekly spending report every Monday 9AM
- ✅ **Webhook Integration** — `/webhook/chat` endpoint for n8n
- ✅ **Clean UI** — Streamlit with tool badges showing agent decisions
- ✅ **API documentation** — Auto-generated at `/docs`

---

## ⚠️ Assumptions & Limitations

- **No real banking API** — All transaction data is mocked (as per requirements)
- **In-memory sessions** — Conversation history is lost on server restart (upgrade to Redis for persistence)
- **Single user** — `user_id: user_001` is hardcoded in mock data
- **ChromaDB rebuild** — First startup takes ~10s to generate embeddings; subsequent starts load from disk
- **OpenAI dependency** — Requires a valid `OPENAI_API_KEY`; tested with `gpt-4o-mini`

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| Backend | FastAPI + Uvicorn |
| AI Framework | LangChain |
| Agent | LangGraph |
| LLM | OpenAI GPT-4o-mini |
| Vector DB | ChromaDB |
| Embeddings | OpenAI text-embedding-ada-002 |
| Workflow Automation | n8n |
| Frontend | Streamlit |
| Memory | In-memory (session-based) |
