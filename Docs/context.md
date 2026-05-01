# Project Context: AI Travel Planner

## Overview
An AI-powered multi-agent travel planning system that automatically turns natural language travel requests into structured, day-by-day trip itineraries. Built to demonstrate how multiple specialized AI agents collaborate on a real-world problem.

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
Orchestrator → parallel(Destination, Logistics, Budget) → merge → Review → (optional repair) → FinalItinerary
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
- Budget: $3,000
- Preferences: food, temples
- Avoidances: crowds

### 2. Parallel Agent Execution
```
Orchestrator ─┬─→ Destination: prefs, cities, duration, avoidances
              ├─→ Logistics: cities, duration, rough intent
              └─→ Budget: budget cap, duration, cities
```
All three agents work in parallel to gather information.

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
currency: string
preferences: string[]           # e.g., ["food", "temples"]
avoidances: string[]            # e.g., ["crowds"]
hard_requirements: string[]     # inferred
soft_preferences: string[]       # inferred
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
| FX | Budget | Currency conversion |

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
- No LLM keys or agent logic in browser

---

## Implementation Plan (10 Phases)

| Phase | Goal | Exit Criteria |
|-------|------|---------------|
| **0** | Project skeleton & config | Backend runs; health check passes; stub POST /api/plan |
| **1** | Shared data models | Golden JSON fixtures round-trip through parsers |
| **2** | LLM extraction (Orchestrator A) | NL → TravelConstraints with validation |
| **3** | Tool router (stubs) | Agents can call tools; swap stub → real later |
| **4** | Worker agents v1 | Destination, Logistics, Budget produce valid artifacts |
| **5** | Parallel execution & merge | Concurrent workers → coherent DraftItinerary |
| **6** | Review Agent | Programmatic + LLM checks; known-bad drafts fail |
| **7** | Repair loop & final API | Bounded retries; stable POST /api/plan contract |
| **8** | Hardening & demo polish | Timeouts, observability, README, CORS |
| **9** | Frontend application | Full-stack demo: browser → API → rendered plan |
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
3. **Pipeline**: Orchestrator → parallel(Destination, Logistics, Budget) → merge → Review → (repair) → user
4. **Backend Owns Intelligence**: LLM keys, agents, tools run only on server
5. **Frontend Owns Experience**: Input, loading states, structured rendering; no secrets in browser
6. **Hub-and-Spoke Communication**: Only Orchestrator routes messages
7. **Parallel Execution**: Three LLM calls with shared constraints for efficiency
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
┌─────┐   ┌─────────────┐   ┌───────────┐   ┌─────────┐   ┌───────┐   ┌──────┐
│User │   │ Orchestrator│   │Destination│   │Logistics│   │Budget │   │Review│
└──┬──┘   └──────┬──────┘   └─────┬─────┘   └────┬────┘   └───┬───┘   └──┬───┘
   │              │                │                │            │          │
   │ NL request   │                │                │            │          │
   │─────────────>│                │                │            │          │
   │              │ extract constraints             │            │          │
   │              │───────────────┬────────────────┬──────────────┤          │
   │              │ [par] prefs, cities, etc.      │            │          │
   │              │───────────────>│                │            │          │
   │              │                │ ActivityCatalog│            │          │
   │              │<───────────────│                │            │          │
   │              │──────────────────────────────────────────────>│          │
   │              │                               Lodging+Movement+DaySkeleton
   │              │<─────────────────────────────────────────────│          │
   │              │──────────────────────────────────────────────────────────>│
   │              │                                    BudgetBreakdown+flags
   │              │<──────────────────────────────────────────────────────────│
   │              │ merge → DraftItinerary                              │
   │              │──────────────────────────────────────────────────────────>│
   │              │                                    ReviewReport
   │              │<──────────────────────────────────────────────────────────│
   │              │ [alt: fail/warnings] revise → re-review (bounded)
   │              │──────────────────────────────────────────────────────────>│
   │              │                                    (re-review)
   │              │<──────────────────────────────────────────────────────────│
   │ Final Itinerary
   │<─────────────│
```
