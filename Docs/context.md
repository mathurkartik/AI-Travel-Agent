# Project Context: AI Travel Planner

## Overview
An AI-powered multi-agent travel planning system that automatically turns natural language travel requests into structured, day-by-day trip itineraries. Built to demonstrate how multiple specialized AI agents collaborate on a real-world problem.

**Current Status**: Fully implemented (Phases 0-9), stable, and production-ready. Recently hardened for **high-quality global itineraries** (Thailand, India, Vietnam) with robust duplicate day numbering resolution and LLM output coercion. Passes all programmatic test validations and features a responsive React frontend paired with an asyncio FastAPI backend.

---

## Problem Statement

### Background
Planning a trip becomes overwhelming quickly. A simple request like:
> *"Plan a 5-day trip to Japan. Tokyo + Kyoto. $3,000 budget. Love food and temples, hate crowds."*

Requires combining many kinds of work:
- Understanding traveler goals
- Researching destinations and attractions
- Comparing hotels and transport options
- Staying within budget
- Verifying the final itinerary matches the request

### Objective
Design a simple Travel Planning Multi-Agent System that transforms a short travel request into a useful trip plan. Not meant to be a perfect travel product, but a demonstration of multi-agent collaboration that product managers can understand.

### System Outputs
- Day-by-day trip outline
- Suggested neighborhoods / areas to stay
- Travel logistics between cities
- Budget-friendly recommendations
- Final itinerary respecting user's preferences and constraints

---

## System Architecture

### Components

| Component | Responsibility | Primary Output |
|-----------|---------------|----------------|
| **Orchestrator** | Parse request → structured constraints; decompose work; merge partial plans; resolve conflicts; final narrative itinerary | TravelConstraints, DraftItinerary, FinalItinerary |
| **Trip Structuring** | (For trips > 7 days) Pre-processes constraints, segments trip geographically, defines route and pacing | TripStructure, Region[] |
| **Destination Research** | Places, food, temples, experiences; crowd-aware options; must-do vs nice-to-have | ActivityCatalog, neighborhood notes |
| **Logistics** | Stays per city, inter-city transport, daily ordering, travel-time sanity, backtracking reduction | LodgingPlan, MovementPlan, DaySkeleton[] |
| **Budget** | Category split (stay/transport/food/activities); totals vs cap; cheaper alternatives | BudgetBreakdown, flags, suggested_swaps[] |
| **Review** | Validate against constraints + realism gate | ReviewReport (pass/fail + issues), RepairHints |

### Communication Topology (Hub-and-Spoke)
- **Only the Orchestrator routes messages**
- No direct Destination ↔ Logistics ↔ Budget messaging
- Each specialist receives the same read-only TravelConstraints from Orchestrator
- Review never invokes workers directly — only Orchestrator does after interpreting ReviewReport

### Pipeline Flow
```
Orchestrator → TripStructuringAgent → parallel per-region(Destination, Logistics, Budget) → merge → Review → (optional repair) → FinalItinerary
```

---

## Workflow Flow

### 1. Request Intake
```
User → Orchestrator: NL travel request
```
Orchestrator extracts key constraints:
- Destination: Japan
- Duration: 5 days
- Cities: Tokyo + Kyoto
- Budget: 250,000 INR
- Currency: INR (Default)
- Preferences: food, temples
- Avoidances: crowds

### 2. Trip Structuring & Parallel Execution
```
Orchestrator → TripStructuringAgent: >7 days trips are broken into regions

Orchestrator ─┬─→ Destination (per region): prefs, cities, duration, avoidances
              ├─→ Logistics (per region): cities, duration, rough intent
              └─→ Budget (per region): budget cap, duration, cities
```
All three agents work in parallel for each region to gather information.

### 3. Agent Outputs
| Agent | Output |
|-------|--------|
| Destination | `ActivityCatalog` - neighborhoods, temples, food streets, local experiences, less-crowded options |
| Logistics | `LodgingPlan + MovementPlan + DaySkeleton` - nights per city, Shinkansen, day plans reducing backtracking |
| Budget | `BudgetBreakdown + flags` - estimated total spend, category breakdown, flags for high costs |

### 4. Merge & Draft
```
Orchestrator: Merge into DraftItinerary
```
- Resolves conflicts (what vs when vs cost)
- Attaches budget summary
- Links slots to catalog IDs

### 5. Review Cycle
```
Orchestrator → Review: Draft + constraints
Review → Orchestrator: ReviewReport
```

**Checks performed:**
- Duration: Does day count match?
- Cities: Are all required cities included?
- Budget: Is total within $3,000?
- Preferences: Does it align with "food + temples"?
- Crowd avoidance: Does it avoid crowded experiences?
- Logistics realism: Is the plan realistic travel-time wise?

**Alt Path (Fail or warnings):**
```
Orchestrator: Revise (swap items, rebalance days, trim cost)
Orchestrator → Review: Re-review (bounded retries: max 2-3 cycles)
```

### 6. Final Delivery
```
Orchestrator → User: Final Itinerary
```
With disclaimer that plans are illustrative, not guaranteed prices.

---

## Core Data Models (Shared Artifacts)

### TravelConstraints (Orchestrator output, input to all workers)
```
destination_region: string
cities: string[]
duration_days: number
budget_total: number
currency: string              # default: "INR"
preferences: string[]           # e.g., ["food", "temples"]
avoidances: string[]            # e.g., ["crowds"]
hard_requirements: string[]     # inferred
soft_preferences: string[]       # inferred
```

### TripStructure (TripStructuringAgent)
```
trip_type: "city_trip" | "road_trip" | "multi_region"
regions: Region[]               # name, base_location, allocated_days
route: string[]                 # ordered sequence of locations
```

### ActivityCatalog (Destination)
```
Per city:
  activities[]:
    - type: "temple" | "food" | etc.
    - estimated_duration: number
    - crowd_level: ordinal | tag
    - cost_band: string
    - must_do: boolean
    - rationale: string
```

### LodgingPlan + MovementPlan (Logistics)
```
LodgingPlan:
  - nights_per_city / area
  - suggested_neighborhoods

MovementPlan:
  - inter-city_mode (e.g., Shinkansen)
  - rough frequency/cost band
  
DaySkeleton[]:
  - ordered slots
  - travel_time estimates between slots
```

### BudgetBreakdown (Budget)
```
Per category totals: stay, transport, food, activities
Per-day optional rollup
within_budget: boolean
violations: string[]
suggested_swaps: string[]        # e.g., "cheaper Tokyo area"
```

### DraftItinerary (Orchestrator merge)
```
Day-by-day narrative
Structured slots linking to catalog IDs
Embedded or referenced budget summary
```

### ReviewReport (Review)
```
Boolean checklist:
  - days match duration_days
  - cities ⊆ plan
  - budget ≤ budget_total
  - prefs aligned
  - crowd avoidance effort
  - logistics realism
severity per issue: blocking | advisory
RepairHints (optional): specific actions to fix issues
```

---

## Tooling Layer

Agents call tools through a single **ToolRouter** with logging, timeouts, and caching.

| Tool Category | Used By | Examples |
|---------------|---------|----------|
| Search / retrieval | Destination | Web search, curated snippets |
| Geo / routing | Logistics | Distances, rough transit times |
| Pricing | Budget (+ Logistics) | Hotel/food/activity ranges, static tables |
| FX | Budget | Currency conversion (USD -> Local) |

---

## API Surface

### Backend Endpoints
| Operation | Purpose |
|-----------|---------|
| `GET /health` | Liveness check |
| `POST /api/plan` | Submit NL request → FinalItinerary |
| `GET /api/plan/{id}` | (Optional) Fetch prior result |

**POST /api/plan Request:**
```json
{
  "request": "Plan a 5-day trip to Japan...",
  "flags": {} // optional
}
```

**POST /api/plan Response:**
```json
{
  "final_itinerary": { ... },
  "constraints": { ... },
  "review_summary": "pass | warnings | issues",
  "trace_id": "uuid-for-debugging",
  "disclaimer": "string"
}
```

### Frontend Responsibilities
- Capture input via textarea or guided form
- Call backend with loading state
- Render output: day-by-day outline, neighborhoods, logistics, budget breakdown, review status
- Handle errors: network, 4xx/5xx, timeout with trace_id for support
- **Global Support**: Dynamic currency formatting (₹, $, kr, €) with INR-optimized suffixes (L/k)
- **Scale**: Supports both Country and City level requests with dynamic region rendering
- **Sidebar**: Dynamic "Trip Summary" rendering constraints and user preferences

---

## Implementation Plan (10 Phases)

| Phase | Goal | Exit Criteria |
|-------|------|---------------|
| **0** | Project skeleton & config | Backend runs; health check passes; stub POST /api/plan |
| **1** | Shared data models | Golden JSON fixtures round-trip through parsers |
| **2** | LLM extraction (Orchestrator A) | NL → TravelConstraints with validation |
| **3** | Tool router (stubs) | Agents can call tools; swap stub → real later |
| **4** | Worker agents v1 | Destination, Logistics, Budget produce valid artifacts |
| **5** | Hierarchical Structuring & Merge | TripStructuringAgent → parallel workers → DraftItinerary |
| **6** | Review Agent | Programmatic + LLM checks; known-bad drafts fail |
| **7** | Repair loop & final API | Bounded retries; stable POST /api/plan contract |
| **8** | Hardening & demo polish | Timeouts, observability, README, CORS |
| **9** | Frontend application | Full-stack global demo: browser → API → rendered plan |
| **10** | (Optional) Extensions | Human-in-the-loop, RAG, durable PlanState store |

### Milestones
| Milestone | Phases | Demo Capability |
|-----------|--------|-----------------|
| M1 | 0-2 | "Constraints from text" |
| M2 | 0-4 | "Three specialist JSON outputs" |
| M3 | 0-5 | "One merged draft itinerary" |
| M4 | 0-7 | "Validated/repaired final plan" (API) |
| M5 | 0-8 | "Stable PM-ready demo" (API + docs) |
| M6 | 0-9 | "Full-stack demo" (browser UI + backend) |

---

## Key Design Patterns

1. **Constraints First**: One orchestrator pass extracts TravelConstraints; worker agents never re-parse the raw user string
2. **Typed Artifacts**: Pydantic/JSON Schema shared between backend and frontend (OpenAPI codegen)
3. **Pipeline**: Orchestrator → TripStructuringAgent → parallel per-region(Destination, Logistics, Budget) → merge → Review
4. **Backend Owns Intelligence**: LLM keys, agents, tools run only on server
5. **Frontend Owns Experience**: Input, loading states, structured rendering; no secrets in browser
6. **Hub-and-Spoke Communication**: Only Orchestrator routes messages
7. **Parallel Execution**: Three LLM calls per region with shared constraints for efficiency
8. **Iterative Refinement**: Review → Revise → Re-review with bounded retries (max 2-3)
9. **Two-Layer Review**: Programmatic checks (cheap, reliable) + LLM qualitative checks
10. **Stable IDs**: On activities and lodging for deterministic merge and re-review

---

## Non-Functional Requirements

| Concern | Approach |
|---------|----------|
| **Latency** | Parallelize agents; cap tool calls per agent |
| **Cost** | Smaller models for Review + extraction; larger model only for merge/narrative |
| **Determinism** | Structured outputs (JSON schema); low temperature for Review and extraction |
| **Safety** | No real PII required; disclaimers that plans are illustrative |
| **Observability** | Trace ID per request; log prompts, tool calls, artifacts, Review outcome |
| **Failure** | Per-agent timeout → partial plan with explicit "missing X" section |

---

## Scope & Constraints

- **Educational / PM-demo quality**: Illustrative pricing and logistics, not production booking
- **No real inventory**: Success measured by constraint satisfaction and plausibility
- **Full-stack application**: Backend (HTTP API + multi-agent runtime) + Frontend (request UI + itinerary presentation)
- **Optional extensions out of scope**: Human-in-the-loop, RAG over guides, durable PlanState store, Presenter-only agent

---

## Sequence Diagram Summary

```
┌─────┐   ┌─────────────┐   ┌────────────────┐   ┌───────────┐   ┌─────────┐   ┌───────┐   ┌──────┐
│User │   │ Orchestrator│   │TripStructuring │   │Destination│   │Logistics│   │Budget │   │Review│
└──┬──┘   └──────┬──────┘   └───────┬────────┘   └─────┬─────┘   └────┬────┘   └───┬───┘   └──┬───┘
   │              │                 │                  │              │            │          │
   │ NL request   │                 │                  │              │            │          │
   │─────────────>│                 │                  │              │            │          │
   │              │ extract         │                  │              │            │          │
   │              │────────────────>│                  │              │            │          │
   │              │                 │ define regions   │              │            │          │
   │              │<────────────────│                  │              │            │          │
   │              │────────────────────────────────────┬──────────────┬────────────┤          │
   │              │ [par per region] constraints       │              │            │          │
   │              │───────────────────────────────────>│              │            │          │
   │              │                 │                  │ActivityCat.  │            │          │
   │              │<───────────────────────────────────│              │            │          │
   │              │───────────────────────────────────────────────────>│           │          │
   │              │                                 Lodging+Move+DaySkel           │          │
   │              │<───────────────────────────────────────────────────│           │          │
   │              │────────────────────────────────────────────────────────────────>│         │
   │              │                                              BudgetBreakdown    │         │
   │              │<────────────────────────────────────────────────────────────────│         │
   │              │ merge → DraftItinerary                                                    │
   │              │──────────────────────────────────────────────────────────────────────────>│
   │              │                                              ReviewReport                 │
   │              │<──────────────────────────────────────────────────────────────────────────│
   │              │ [alt: fail] revise → re-review (bounded)                                  │
   │ Final Plan   │──────────────────────────────────────────────────────────────────────────>│
   │<─────────────│                                                                           │
```

---

## Complete File Structure

```
M4/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI entry point, CORS, middleware
│   │   ├── config.py                  # Pydantic settings, environment variables
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── routes.py              # POST /api/plan, GET /health
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── schemas.py             # 25+ Pydantic models (TravelConstraints, ActivityCatalog, etc.)
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py        # Central coordinator, repair loop, timeouts
│   │   │   ├── destination.py         # Activity research, LLM generation, static fallback
│   │   │   ├── logistics.py           # Lodging, transport, day skeletons
│   │   │   ├── budget.py              # Cost analysis, swap suggestions
│   │   │   └── review.py              # Quality validation, programmatic + LLM checks
│   │   ├── llm/
│   │   │   ├── __init__.py
│   │   │   ├── groq_client.py         # Groq LLM integration, constraint extraction
│   │   │   ├── token_tracker.py       # 100k tokens/day budget management
│   │   │   └── cache.py               # Response caching
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   └── router.py              # ToolRouter stubs (search, geo, price, fx)
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── observability.py       # Structured logging, agent lifecycle tracking
│   ├── tests/
│   │   ├── test_schemas.py            # Data model validation tests
│   │   ├── test_edge_cases.py         # 56+ edge case tests
│   │   ├── test_agents.py             # Agent unit tests
│   │   ├── test_groq_integration.py   # LLM integration tests (~15k tokens)
│   │   ├── test_token_tracker.py      # Token budget tests
│   │   ├── test_phase2_extraction.py  # Constraint extraction tests
│   │   ├── test_phase5.py             # Orchestration tests
│   │   ├── test_phase6.py             # Review agent tests
│   │   └── test_tool_router.py        # Tool routing tests
│   ├── .env                           # Environment variables (git-ignored)
│   ├── .env.example                   # Template for environment setup
│   └── requirements.txt               # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── PlanForm.tsx           # Travel request input form
│   │   │   ├── ItineraryDisplay.tsx   # Full itinerary rendering
│   │   │   ├── ErrorDisplay.tsx       # Error messages with trace ID
│   │   │   └── index.ts               # Component exports
│   │   ├── hooks/
│   │   │   ├── usePlan.ts             # Plan state management, API calls
│   │   │   └── index.ts               # Hook exports
│   │   ├── services/
│   │   │   ├── api.ts                 # API client (health, createPlan)
│   │   │   └── index.ts               # Service exports
│   │   ├── types/
│   │   │   └── index.ts               # TypeScript types matching backend schemas
│   │   ├── App.tsx                    # Main app (Home + Result views)
│   │   ├── App.css                    # Design system (650+ lines)
│   │   ├── main.tsx                   # React entry point
│   │   └── vite-env.d.ts              # Vite type declarations
│   ├── index.html                     # HTML template
│   ├── vite.config.ts                 # Vite configuration + proxy
│   ├── tsconfig.json                  # TypeScript config
│   ├── package.json                   # Node dependencies
│   └── .env.example                   # Frontend environment template
├── Docs/
│   ├── context.md                     # This comprehensive context file
│   ├── session_summary.md             # Per-session outcomes
│   ├── execution_summary.md           # Detailed task logs
│   ├── ImplementationPlan.md          # 10-phase development plan
│   ├── Architecture.md                # System architecture diagrams
│   ├── ProblemStatement.md            # Original problem description
│   └── test_plan.md                 # Testing strategy
├── .gitignore                         # Git exclusions (Python, Node, secrets)
└── README.md                          # Project overview, setup instructions
```

---

## API Contracts

### POST /api/plan
Create a travel plan from natural language request.

**Request:**
```json
{
  "request": "Plan a 5-day trip to Japan. Tokyo + Kyoto. $3000 budget. Love food and temples."
}
```

**Success Response (200):**
```json
{
  "success": true,
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "final_itinerary": {
    "destination_region": "Japan",
    "cities": ["Tokyo", "Kyoto"],
    "duration_days": 5,
    "budget": { "total": 3000, "currency": "USD" },
    "days": [
      {
        "day_number": 1,
        "city": "Tokyo",
        "slots": [
          {
            "slot_index": 0,
            "start_time": "09:00",
            "end_time": "12:00",
            "title": "Senso-ji Temple",
            "rationale": "Tokyo's oldest temple, aligns with temple preference"
          }
        ],
        "day_cost": 150.0
      }
    ],
    "neighborhoods": ["Asakusa", "Shibuya", "Gion"],
    "logistics_summary": "Shinkansen between Tokyo and Kyoto",
    "review_status": "pass",
    "disclaimer": "AI-generated plan. Verify bookings and prices independently."
  },
  "constraints": { /* TravelConstraints object */ },
  "review_summary": "pass",
  "tokens_used": 8500,
  "used_stub_mode": false
}
```

**Error Response (500):**
```json
{
  "detail": "Failed to create plan: Activity ID cannot contain spaces or slashes",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### GET /health
Health check with LLM availability status.

**Response:**
```json
{
  "status": "healthy",
  "llm_provider": "groq",
  "llm_available": true,
  "tokens": {
    "daily_total": 8500,
    "daily_limit": 100000,
    "remaining": 91500,
    "percent_used": 8.5
  }
}
```

---

## Environment Variables

### Backend (.env)
```bash
# LLM Configuration (Groq)
GROQ_API_KEY=gsk_...                    # Required for LLM features
GROQ_MODEL=llama-3.3-70b-versatile      # LLM model
GROQ_MAX_TOKENS_PER_REQUEST=4000        # Max tokens per call
GROQ_TEMPERATURE=0.1                    # Low temp for deterministic extraction

# Token Budget Management
ENABLE_TOKEN_TRACKING=true              # Enable 100k/day tracking
MAX_TOKENS_PER_PLAN_REQUEST=15000       # Per-request limit
TOKEN_BUFFER_PERCENT=20                 # 20% safety buffer

# Response Caching
ENABLE_RESPONSE_CACHE=true              # Cache LLM responses
CACHE_TTL_SECONDS=3600                  # 1 hour cache TTL

# Agent Timeouts
AGENT_TIMEOUT_SECONDS=30                # Per-agent timeout

# CORS Origins
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# App Settings
APP_NAME=AI Travel Planner
DEBUG=false
```

### Frontend (.env)
```bash
VITE_API_URL=http://localhost:8000      # Backend API URL
```

---

## Key Code Patterns

### 1. Agent Implementation Pattern
```python
class DestinationAgent:
    def __init__(self, tool_router=None, llm_client=None):
        self.tool_router = tool_router
        self.llm_client = llm_client
    
    async def research(self, constraints: TravelConstraints) -> ActivityCatalog:
        # Try LLM first
        if self.llm_client:
            try:
                activities = await self._llm_generate_activities(city, constraints)
                if activities:
                    return activities
            except Exception as e:
                print(f"LLM failed: {e}")
        
        # Fallback to static data
        return self._get_static_activities_for_city(city, constraints)
```

### 2. Constraint Extraction Pattern
```python
# System prompt with strict rules
system_prompt = """Extract structured constraints from user request.
CRITICAL: Extract cities EXACTLY as mentioned. NEVER substitute defaults."""

# LLM call with structured output
response = self._client.chat.completions.create(
    model=self.model,
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": natural_language_request}
    ],
    response_format={"type": "json_object"}
)

# Parse and validate
constraints = TravelConstraints.model_validate(json.loads(response))
```

### 3. Observability Pattern
```python
from app.utils.observability import ObservabilityLogger

# Log agent lifecycle
ObservabilityLogger.log_agent_start("destination", trace_id)
result = await agent.research(constraints)
ObservabilityLogger.log_agent_complete("destination", trace_id, duration_ms)

# Log partial failures
ObservabilityLogger.log_partial_failure(
    trace_id, "destination_agent", "use_static_catalog", "LLM rate limited"
)
```

### 4. Repair Loop Pattern
```python
async def create_plan(self, request: str) -> FinalItinerary:
    # Extract constraints
    constraints = await self.extract_constraints(request)
    
    # Parallel agent execution
    catalog, logistics, budget = await asyncio.gather(
        self.destination_agent.research(constraints),
        self.logistics_agent.plan(constraints),
        self.budget_agent.analyze(constraints)
    )
    
    # Merge
    draft = self._merge(catalog, logistics, budget, constraints)
    
    # Review with bounded retries
    for cycle in range(max_repair_cycles):
        review = await self.review_agent.validate(draft, constraints)
        if review.overall_status == "pass":
            break
        draft = await self._repair(draft, review.repair_hints)
    
    return self._draft_to_final(draft, review, constraints)
```

---

## Testing Strategy

### Test Categories

| Category | Command | Tokens | When to Run |
|----------|---------|--------|-------------|
| **Unit** | `pytest tests/test_schemas.py tests/test_edge_cases.py` | 0 | Every commit |
| **Integration** | `pytest tests/test_groq_integration.py` | ~15k | Daily |
| **E2E** | Manual or Playwright | ~40k | Weekly |

### Running Tests
```bash
# Unit tests (fast, no tokens)
cd backend
pytest tests/test_schemas.py tests/test_edge_cases.py -v

# Integration tests (requires GROQ_API_KEY)
export GROQ_API_KEY=gsk_...
pytest tests/test_groq_integration.py -v

# All tests
pytest -v
```

### Test Markers
- `@pytest.mark.unit` - Fast tests, no LLM calls
- `@pytest.mark.expensive` - Tests using LLM tokens
- `@pytest.mark.integration` - End-to-end tests

---

## Troubleshooting Guide

### Common Issues

**1. Backend won't start**
```bash
# Check Python version (requires 3.11+)
python --version

# Install dependencies
cd backend
pip install -r requirements.txt

# Check for port conflicts
curl http://localhost:8000/health
```

**2. LLM returns "New York" when I asked for "Norway"**
- Fix: Improved prompt and extraction regex to handle Countries (e.g. Norway, Sweden) and better city detection.
- Stub logic: Robust regex skips instructional noise and identifies destinations and bare numbers (INR/USD) accurately.
- Default: Now defaults to "World" and "INR" if extraction fails completely.

**3. ActivityCatalog validation error (empty activities)**
- Cause: LLM rate-limited, fallback returned empty list
- Fix: Static fallback with generic activities implemented
- Check: `destination.py` `_generate_generic_activities()`

**4. CORS error in browser**
- Cause: Backend not allowing frontend origin
- Fix: Add `http://localhost:5173` to `CORS_ORIGINS` in `.env`

**5. Token budget exceeded**
- Check status: `curl http://localhost:8000/api/tokens/status`
- Reset at midnight UTC
- Reduce `TOKEN_BUFFER_PERCENT` temporarily

**6. Frontend build errors**
```bash
cd frontend
npm install
npm run build
```

---

## Development Workflow

### Starting Development
```bash
# Terminal 1: Backend
cd backend
py -m uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev

# Access frontend at http://localhost:5173
```

### Making Changes
1. Edit code in `backend/app/` or `frontend/src/`
2. Backend auto-reloads on file changes
3. Frontend hot-reloads via Vite
4. Test changes via frontend UI or curl

### Before Committing
```bash
# Run unit tests
cd backend
pytest tests/test_schemas.py tests/test_edge_cases.py -v

# Verify syntax
py -c "from app.main import app"

# Check git status
git status
git add .
git commit -m "Description of changes"
git push origin main
```

---

## GitHub Repository

**URL:** `https://github.com/mathurkartik/AI-Travel-Agent`

**Repository Structure:**
- Public repository with complete codebase
- `.gitignore` excludes: `.env`, `__pycache__/`, `node_modules/`, IDE files
- 81 files tracked in initial commit
- Ready for collaboration and deployment

**Setup for New Contributors:**
```bash
git clone https://github.com/mathurkartik/AI-Travel-Agent.git
cd AI-Travel-Agent

# Backend setup
cd backend
cp .env.example .env
# Edit .env with your GROQ_API_KEY
pip install -r requirements.txt

# Frontend setup
cd ../frontend
npm install
cp .env.example .env
```

---

## Technology Stack Summary

| Layer | Technology | Purpose |
|-------|------------|---------|
| Backend Framework | FastAPI | HTTP API, auto OpenAPI docs |
| Data Validation | Pydantic v2 | Schema validation, serialization |
| LLM Provider | Groq (llama-3.3-70b) | Constraint extraction, narrative |
| Async Runtime | asyncio | Parallel agent execution |
| Frontend Framework | React 18 | UI components |
| Frontend Build | Vite | Fast dev server, bundling |
| Styling | CSS Modules | Design system, responsive |
| Testing | pytest | Unit and integration tests |
| Language | Python 3.11+ | Backend, agents |
| Language | TypeScript 5+ | Frontend |

---

## Project Completion Status

All 9 core phases complete:

✅ **Phase 0** - Project skeleton & config
✅ **Phase 1** - Shared data models  
✅ **Phase 2** - LLM constraint extraction
✅ **Phase 3** - Tool Router stubs
✅ **Phase 4** - Worker agents v1
✅ **Phase 5** - Parallel execution & merge
✅ **Phase 6** - Review Agent
✅ **Phase 7** - Repair loop & final API
✅ **Phase 8** - Hardening & demo polish
✅ **Phase 9** - Frontend application

⏳ **Phase 10** - Extensions (optional, out of scope)

---

## Quick Reference Card

**Start Backend:** `cd backend && py -m uvicorn app.main:app --reload`
**Start Frontend:** `cd frontend && npm run dev`
**API Health:** `curl http://localhost:8000/health`
**Create Plan:** `curl -X POST http://localhost:8000/api/plan -H "Content-Type: application/json" -d '{"request":"5 days in Japan"}'`
**Run Tests:** `cd backend && pytest tests/test_schemas.py -v`
**Check Tokens:** `curl http://localhost:8000/api/tokens/status`
**Git Push:** `git add . && git commit -m "message" && git push origin main`

---

*Last Updated: 2026-05-01 | Session 14 Complete*
