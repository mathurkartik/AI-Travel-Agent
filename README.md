# 🌍 GlobeAI — AI Travel Planner

> A multi-agent AI system that transforms natural-language travel requests into structured, day-by-day trip itineraries — powered by specialized AI agents working in parallel.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?style=flat-square&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)
![Vite](https://img.shields.io/badge/Vite-5-646CFF?style=flat-square&logo=vite&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3-F55036?style=flat-square)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white)

---

## 📌 Problem Statement

Planning a trip sounds simple, but quickly becomes overwhelming. A traveler might say:

> *"Plan a 10-day trip to Thailand. ₹80,000 budget. Love temples and street food."*

To fulfill that well, you need to combine **destination research**, **logistics planning**, **budget optimization**, and **quality validation** — all while respecting the traveler's preferences. Doing this manually takes hours.

**GlobeAI solves this** by coordinating five specialized AI agents that work together on the problem, producing a complete itinerary in seconds.

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🤖 **Multi-Agent Architecture** | 5 specialized agents (Orchestrator, Destination, Logistics, Budget, Review) collaborate via a hub-and-spoke pattern |
| 🧠 **Natural Language Understanding** | Describe your trip in plain English — the system extracts constraints automatically |
| 🗺️ **Hierarchical Trip Planning** | Trips > 7 days are intelligently split into geographic regions for realistic itineraries |
| ⚡ **Parallel Execution** | Destination, Logistics, and Budget agents run concurrently for speed |
| ✅ **AI Quality Gate** | A Review Agent validates every itinerary against your constraints before delivery |
| 🔧 **Auto-Repair Loop** | Failed reviews trigger up to 3 automated repair cycles |
| 💰 **Budget Breakdown** | Categorized spending (Stay, Food, Transport, Activities) with within-budget validation |
| 📊 **Strategic Insights** | AI-generated travel tips, budget analysis, and cost optimization suggestions |
| 🌐 **Region-Specific Content** | Curated route templates and activity catalogs for Thailand, India, Vietnam, Japan, Iceland, and more |
| 📧 **Booking Integration** | Submit booking requests directly from the itinerary page |
| 🐳 **Docker Ready** | Dockerfiles and docker-compose for one-command deployment |

---

## 🏗️ Architecture

```
User Request (Natural Language)
        │
        ▼
┌─────────────────────────────────┐
│       Orchestrator Agent        │  ← Extracts TravelConstraints
│   (Central Coordinator)         │  ← Manages pipeline & merge
└─────────┬───────────────────────┘
          │
          ▼
┌─────────────────────────────────┐
│    Trip Structuring Agent       │  ← Splits into regions (if > 7 days)
└─────────┬───────────────────────┘
          │
    ┌─────┼─────┐
    ▼     ▼     ▼
┌──────┐┌──────┐┌──────┐
│Destin││Logis-││Budget│   ← Parallel execution (per region)
│ation ││tics  ││Agent │
└──┬───┘└──┬───┘└──┬───┘
   └───────┼───────┘
           ▼
┌─────────────────────────────────┐
│     Merge → DraftItinerary      │
└─────────┬───────────────────────┘
          ▼
┌─────────────────────────────────┐
│       Review Agent              │  ← Quality validation
│   (pass / fail + repair hints)  │
└─────────┬───────────────────────┘
          │
    [fail] → Repair → Re-review (max 3x)
          │
    [pass] ▼
┌─────────────────────────────────┐
│       FinalItinerary            │  → Delivered to user
└─────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- [Groq API Key](https://console.groq.com) (free tier available)

### Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env → add your GROQ_API_KEY

# Start server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 📂 Project Structure

```
GlobeAI/
├── backend/                     # FastAPI application
│   ├── app/
│   │   ├── agents/              # Multi-agent system
│   │   │   ├── orchestrator.py  # Central coordinator (pipeline, merge, repair)
│   │   │   ├── destination.py   # Activity & attraction research
│   │   │   ├── logistics.py     # Lodging, transport & day sequencing
│   │   │   ├── budget.py        # Cost analysis & optimization
│   │   │   ├── review.py        # Quality validation gate
│   │   │   └── trip_structuring.py  # Regional decomposition
│   │   ├── models/schemas.py    # All Pydantic data contracts
│   │   ├── tools/router.py      # Unified tool access layer
│   │   ├── llm/                 # Groq client, token tracking, caching
│   │   ├── api/routes.py        # HTTP endpoints
│   │   ├── utils/observability.py  # Structured logging
│   │   ├── config.py            # Settings & environment
│   │   └── main.py              # FastAPI application entry
│   ├── tests/                   # Comprehensive test suite
│   ├── Dockerfile               # Production container
│   └── requirements.txt
├── frontend/                    # React + Vite + TypeScript
│   ├── src/
│   │   ├── App.tsx              # Main application (home + itinerary views)
│   │   ├── hooks/               # API integration hooks
│   │   ├── types/               # Shared TypeScript types
│   │   └── App.css              # Design system
│   ├── Dockerfile               # Multi-stage build (Node → Nginx)
│   └── package.json
├── Docs/                        # Architecture, plans, and session logs
├── docker-compose.yml           # One-command full-stack deployment
└── README.md
```

---

## 🔌 API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check with token budget status |
| `/api/plan` | POST | Generate a full travel itinerary |
| `/api/book` | POST | Submit a booking request (Name, Email, Comment + Itinerary) |
| `/api/tokens/status` | GET | Current Groq token usage |
| `/api/plan/{id}` | GET | Retrieve saved plan *(Phase 10 — future)* |

### Example Request

```bash
curl -X POST http://localhost:8000/api/plan \
  -H "Content-Type: application/json" \
  -d '{"request": "Plan a 7-day trip to Thailand. ₹80,000 budget. Love temples, street food, and beaches."}'
```

---

## 🧪 Testing

```bash
cd backend

# Run all tests
pytest

# Run specific test suites
pytest tests/test_phase5.py -v    # Orchestration tests
pytest tests/test_phase6.py -v    # Review agent tests
pytest tests/test_edge_cases.py   # Edge case handling
```

---

## 🐳 Deployment

### Option 1: PaaS (Recommended)

| Component | Platform | Root Directory |
|-----------|----------|----------------|
| Backend   | [Render](https://render.com) or [Railway](https://railway.app) | `backend` |
| Frontend  | [Vercel](https://vercel.com) or [Netlify](https://netlify.com) | `frontend` |

### Option 2: Docker

```bash
# Set environment variables
echo "GROQ_API_KEY=your_key" > .env
echo "VITE_API_URL=http://localhost:8000/api" >> .env

# Deploy
docker compose up -d --build
```

See [Docs/DEPLOYMENT.md](Docs/DEPLOYMENT.md) for detailed step-by-step instructions.

---

## ⚙️ Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | — | **Required.** Your Groq API key |
| `AGENT_TIMEOUT_SECONDS` | `30` | Per-agent execution timeout |
| `MAX_REVIEW_RETRIES` | `3` | Max repair cycles before returning best-effort |
| `CORS_ORIGINS` | `localhost:5173` | Allowed frontend origins |
| `ENABLE_TOKEN_TRACKING` | `true` | Track daily token consumption |
| `TOKEN_BUFFER_PERCENT` | `20` | Reserve buffer before hitting Groq daily limit |

---

## 🎯 Design Principles

1. **Constraints First** — One extraction pass; workers never re-parse natural language
2. **Typed Artifacts** — Pydantic schemas shared across all agent boundaries
3. **Hub-and-Spoke** — Only the Orchestrator routes messages; no agent-to-agent chatter
4. **Bounded Retries** — Max 3 repair cycles to prevent infinite loops
5. **Graceful Degradation** — Agent timeouts produce partial plans, not crashes
6. **Static Fallbacks** — Curated activity catalogs ensure quality even without LLM access

---

## 📄 Documentation

| Document | Purpose |
|----------|---------|
| [ProblemStatement.md](Docs/ProblemStatement.md) | Original requirements and agent definitions |
| [Architecture.md](Docs/Architecture.md) | System design, data flow, and deployment views |
| [ImplementationPlan.md](Docs/ImplementationPlan.md) | 10-phase roadmap with exit criteria |
| [DEPLOYMENT.md](Docs/DEPLOYMENT.md) | Hosting guide (Render, Vercel, Docker) |
| [context.md](Docs/context.md) | Current project status and technical context |

---

## 🛠️ Built With

- **Backend**: Python 3.11, FastAPI, Pydantic v2, asyncio
- **Frontend**: React 18, TypeScript, Vite 5
- **LLM**: Groq Cloud (LLaMA 3.3 70B Versatile)
- **Deployment**: Docker, Nginx, docker-compose

---

## 📜 License

This project was built as part of a Product Management challenge to demonstrate multi-agent AI system design and implementation.

---

<p align="center">
  <b>Built with ❤️ by Kartik Mathur</b>
</p>
