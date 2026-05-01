Implementation Plan 
AI Travel Planner — Phase-Wise Implementation Plan
This plan implements the system described in problemStatement.md according to architecture.md. Phases are ordered so each builds on stable contracts and ends with a demo-ready vertical slice.
The deliverable includes a backend (HTTP API + multi-agent runtime) and a frontend (request UI + itinerary presentation), per application architecture: backend and frontend.
Guiding principles
Constraints first: One orchestrator pass extracts TravelConstraints; worker agents never re-parse the raw user string as the source of truth for duration, cities, or budget.
Typed artifacts: Implement shared schemas (e.g. Pydantic / JSON Schema) before wiring LLM prompts; share the same contract with the frontend (OpenAPI codegen, shared package, or duplicated types checked in CI).
Pipeline: Orchestrator → parallel(Destination, Logistics, Budget) → merge → Review → (optional repair) → user.
Backend owns intelligence: LLM keys, agents, and tools run only on the server.
Frontend owns experience: Input, loading and error states, structured rendering of the plan and disclaimer; no secrets in the browser.
Scope: Educational / PM-demo quality (problem statement); illustrative pricing and logistics, not production booking.
Mapping to user-visible outputs
Problem statement output
Primary phases
Day-by-day trip outline
Phase 4 (Logistics skeleton), Phase 5 (merge), Phase 7 (narrative)
Neighborhoods / areas to stay
Phase 3–4 (Destination + Logistics)
Travel logistics between cities
Phase 4 (MovementPlan), Phase 6 (Review time realism)
Budget-friendly recommendations
Phase 5 (Budget), Phase 5 merge / Phase 8 (swaps)
Final itinerary respecting prefs + constraints
Phase 5–8 (merge, Review, repair)
Web UI for request + plan display
Phase 9 (frontend); depends on stable POST /api/plan from Phase 0 / 7


Phase 0 — Project skeleton and configuration (backend)
Goal: Runnable backend with config, secrets, and a single “hello plan” path without full agents (architecture: backend).
Tasks
Choose backend stack (e.g. Python + FastAPI, or Node + Express/Fastify); add dependency management and .env.example (API keys, model names, CORS allowlist for later frontend URL).
Add minimal HTTP surface: GET /health, POST /api/plan with body { "request": "..." } returning stub JSON matching the eventual response shape where possible.
Central trace ID per request (per architecture §9); return trace_id in JSON for support and demos.
Optionally scaffold an empty frontend repo folder or monorepo apps/web with placeholder page (no API wiring until Phase 9).
Exit criteria
One command starts the backend; health check passes; POST /api/plan returns stub JSON with trace_id in logs.

Phase 1 — Shared data model and validation
Goal: All agent boundaries compile and validate against the same types (architecture §5).
Tasks
Define schemas for: TravelConstraints, ActivityCatalog, LodgingPlan, MovementPlan, DaySkeleton, BudgetBreakdown, DraftItinerary, ReviewReport, optional RepairHints.
Enforce stable IDs on catalog activities and lodging suggestions for merge and re-review.
Unit tests: valid fixtures deserialize; invalid payloads fail with clear errors.
Exit criteria
Golden JSON fixtures for a “Japan 5d Tokyo Kyoto $3000” example round-trip through parsers without LLM calls.

Phase 2 — LLM client and structured extraction (Orchestrator — part A)
Goal: Natural language → TravelConstraints only (problem statement extraction: destination, duration, cities, budget, prefs, avoidances).
Tasks
Integrate chosen LLM SDK; support structured output (JSON schema / tool output) with low temperature for extraction (architecture §9).
Prompt + schema for: destination_region, cities[], duration_days, budget_total, currency, preferences[], avoidances[], optional hard_requirements / soft_preferences.
Fallback or repair prompt when JSON fails validation (single retry).
Exit criteria
Sample strings from the problem statement produce constraints that match expected fields in automated or manual checks.

Phase 3 — Tool router (stubs first)
Goal: Single place for search, geo, pricing, FX with timeouts, logging, and cache keys (architecture §7).
Tasks
Implement ToolRouter interface: search, geo_estimate, price_band, fx_convert (initially stub or static JSON files).
Per-call timeout, trace propagation, simple in-memory cache for identical queries.
Exit criteria
Agents can call tools through the router without knowing implementation; swapping stub → real search is a router change only.

Phase 4 — Worker agents (v1, sequential OK for debugging)
Goal: Each agent returns its primary artifact given TravelConstraints + stubs (architecture §3).
4a — Destination Research Agent
Inputs: constraints + optional ToolRouter.search.
Output: ActivityCatalog — neighborhoods, temples, food, experiences; crowd_level; must-do vs nice-to-have; less-crowded options where possible (problem statement §2).
4b — Logistics Agent
Inputs: constraints + optional geo/transit stubs.
Output: LodgingPlan, MovementPlan, DaySkeleton[] — nights per city, inter-city mode (e.g. Shinkansen), ordered days with travel-time estimates, reduced backtracking (problem statement §3).
4c — Budget Agent
Inputs: constraints + static price bands (hotels, food, transport, activities) + FX stub.
Output: BudgetBreakdown — stay / transport / food / activities; within_budget; violations[]; suggested_swaps[] (problem statement §4).
Tasks (phase 4)
One module per agent; shared system prompt patterns; role-specific prompts returning only validated JSON matching Phase 1 schemas.
Tests with mocked LLM returning canned JSON to keep CI deterministic.
Exit criteria
For a fixed TravelConstraints fixture, all three agents produce valid artifacts (integration test with mocks).

Phase 5 — Orchestrator merge and parallel execution
Goal: Implement the core pipeline segment: parallel workers → DraftItinerary (architecture §4, §6).
Tasks
Run Destination, Logistics, Budget concurrently (async or thread pool) with the same read-only TravelConstraints.
Implement merge(catalog, logistics, budget) -> DraftItinerary: resolve conflicts (what vs when vs cost); attach budget summary; link slots to catalog IDs.
Optional: second Budget pass on full draft if architecture calls for tighter numbers.
Exit criteria
End-to-end (real LLM in dev only): one NL request produces a coherent DraftItinerary JSON with day-by-day structure, neighborhoods, and category spend.

Phase 6 — Review Agent (programmatic + LLM)
Goal: Quality gate before user delivery (problem statement §5, architecture §10).
Tasks
Layer 1 — Programmatic: duration_days matches day count; all required cities appear; total estimated spend ≤ budget_total (using Budget numbers); basic structural checks.
Layer 2 — LLM: Rubric for food/temple alignment, crowd avoidance effort, narrative coherence, logistics realism; output ReviewReport with blocking vs advisory severity.
If Layer 1 fails, still return structured errors; optionally skip or shorten Layer 2.
Exit criteria
Known-bad drafts (wrong city, over budget, wrong day count) fail programmatic checks; good demo draft passes with documented checklist in ReviewReport.

Phase 7 — Repair loop and final user-facing plan
Goal: Bounded revision when Review fails (architecture §4 alt block).
Tasks
Max 2–3 repair cycles: orchestrator consumes ReviewReport + optional RepairHints (trim activities, swap lodging area, rebalance days).
After pass or max retries, expose plan(request) -> FinalItinerary with disclaimer text (architecture §9 safety).
Format API response for PM demo and frontend consumption: structured fields (days, cities, budget rollup) plus optional markdown or html snippet; include disclaimer string (architecture §9).
Document POST /api/plan request/response in OpenAPI or equivalent so Phase 9 can bind types.
Exit criteria
Intentionally over-budget or logistics-broken merged draft is corrected or clearly reported within retry budget.
API contract is stable enough for the frontend to integrate without guessing field names.

Phase 8 — Hardening and demo polish
Goal: Non-functional behaviors and optional real tools (architecture §8–9).
Tasks
Per-agent timeouts; partial failure messaging (“logistics unavailable”) per architecture §9.
Observability: log prompts summaries, tool calls, artifact versions, Review outcome (avoid logging full secrets).
Replace one stub with a real integration if desired (e.g. web search for Destination only); cap calls per request.
README: how to run backend (and frontend after Phase 9), example curl / JSON, architecture pointer.
CORS: confirm production and dev origins allowed for POST /api/plan.
Exit criteria
Repeatable demo script; failure modes are graceful; latency acceptable for live walkthrough.

Phase 9 — Frontend application
Goal: Web UI that talks only to the backend API and presents the trip plan (architecture: frontend).
Tasks
Choose frontend stack (e.g. Vite + React, or Next.js static export if no server-side secrets in FE).
Config: environment variable for API base URL (VITE_API_URL / NEXT_PUBLIC_API_URL etc.); no API keys in client code.
Screens / components
Request form (textarea + submit); optional preset example matching problem statement.
Loading state for long POST /api/plan calls; cancel is optional (AbortController).
Results layout: day-by-day outline, neighborhoods / stay suggestions, logistics (inter-city + pacing), budget breakdown, review status (pass / warnings / issues), disclaimer prominently.
Error UI for validation errors, 5xx, and timeout with suggestion to retry and trace_id if returned.
Types: generate or hand-maintain TypeScript types from OpenAPI / JSON Schema exported by backend (Phase 7–8); keep field names aligned with FinalItinerary response.
Polish: basic responsive layout and accessible labels for demo recordings.
Exit criteria
From the browser: submit sample request → see full itinerary sections populated from real API (dev backend).
Production build serves static assets; README documents npm run dev + proxy or env for API.

Phase 10 (optional) — Extensions
Per architecture §11:
Presenter-only agent for UI formatting (or richer markdown pipeline on backend for the frontend to render).
RAG over curated guides.
Human-in-the-loop when Review remains red.
Durable PlanState store and versioned drafts for audit; optional GET /api/plan/{id} for the frontend history view.

Suggested milestone checklist
Milestone
Phases complete
Demo capability
M1
0–2
“Constraints from text” (API or CLI)
M2
0–4
“Three specialist JSON outputs”
M3
0–5
“One merged draft itinerary”
M4
0–7
“Validated / repaired final plan” (API)
M5
0–8
“Stable PM-ready demo” (API + docs)
M6
0–9
“Full-stack demo” (browser UI + backend)


Dependency graph (summary)
Phase 0 (backend) → Phase 1 → Phase 2 → Phase 3 → Phase 4 (4a–4c)
                                        ↘
Phase 5 (parallel + merge) → Phase 6 → Phase 7 → Phase 8
                                                  ↘
                                            Phase 9 (frontend)
                                                  ↘
                                         Phase 10 (optional)

This order keeps schemas ahead of agents, agents ahead of merge, Review + repair after a real DraftItinerary exists, and the frontend after a stable POST /api/plan contract (Phases 7–8).
