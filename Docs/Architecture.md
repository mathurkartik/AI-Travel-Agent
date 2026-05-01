Architecture
AI Travel Planner — System Architecture
This document describes the architecture for the multi-agent travel planning system defined in problemStatement.md.
1. Purpose and scope
The system turns a natural-language travel request into a structured trip plan by coordinating specialized agents. Success is measured by constraint satisfaction (duration, cities, budget, preferences) and plausibility (logistics, pacing), not by booking real inventory.
The product is delivered as a full-stack application: a backend service that runs the multi-agent pipeline and exposes a stable HTTP API, and a frontend that collects the user request and presents the final itinerary (and intermediate status when desired).
Application architecture: backend and frontend
Backend
The backend is the only component that holds API keys, calls the LLM, runs agents, and invokes the tool router. Responsibilities:
HTTP API — Validate inbound requests (body size, required request or equivalent field), attach trace ID, return JSON (and optional streamed tokens if you add streaming later).
Orchestration runtime — Implements the pipeline in §4: constraint extraction, parallel workers, merge, Review, repair loop.
Configuration and secrets — Model names, timeouts, tool endpoints; never expose secrets to the browser.
Cross-origin and transport — CORS policy restricted to the frontend origin(s); HTTPS in deployed environments.
Operational concerns — Rate limiting or simple auth for public demos, request timeouts aligned with §9, structured error responses (validation vs upstream LLM vs timeout).
Suggested API surface (conceptual):
Operation
Purpose
GET /health
Liveness for load balancers and the frontend preflight.
POST /api/plan
Body: natural-language request string (and optional flags). Response: FinalItinerary payload (structured fields + markdown or HTML snippet), extracted TravelConstraints summary if useful for UI, review summary, and trace_id.
GET /api/plan/{id} (optional)
If you persist plans: fetch a prior result by id.

Long-running plans: prefer single request with server-side timeout for the educational scope; optional SSE or job id + polling if UX requires partial progress without changing agent design.
Frontend
The frontend is a thin client: no LLM keys, no direct agent logic. Responsibilities:
Capture input — Text area (or guided form) for the travel request; optional examples from the problem statement.
Call backend — POST /api/plan with loading state; display disclaimer that the plan is illustrative (§9).
Render output — Sections aligned with product goals: day-by-day outline, neighborhoods / stay areas, inter-city logistics, budget breakdown, review status (pass / warnings / blocking issues).
Resilience — Handle network errors, HTTP 4xx/5xx, and timeout messaging; optional retry for idempotent plan requests if the API supports deduplication keys later.
Developer experience — Shared types or OpenAPI-generated client from the same contract as the backend schemas (§5) where practical.

Deployment sketch: frontend as static assets (e.g. CDN or object storage behind a CDN); backend as container or PaaS function with outbound access to LLM and tools. Environment-specific base URL for the API is configured in the frontend build.
2. System context
External dependencies (conceptual): LLM(s) for each agent role; optional web search; static or sample hotel/transit/price data where real APIs are unavailable; currency conversion for budget checks.
3. Logical architecture — agents and responsibilities
Component
Responsibility
Primary outputs
Orchestrator
Parse request → structured constraints; decompose work; merge partial plans; resolve conflicts; final narrative itinerary
TravelConstraints, task graph, merged DraftItinerary, user-facing plan
Destination Research
Places, food, temples, experiences; crowd-aware options; must-do vs nice-to-have
ActivityCatalog, neighborhood notes, preference-aligned suggestions
Logistics
Stays per city, inter-city transport, daily ordering, travel-time sanity, backtracking reduction
LodgingPlan, MovementPlan, DaySkeleton[]
Budget
Category split (stay / transport / food / activities); totals vs cap; cheaper alternatives
BudgetBreakdown, flags, BudgetAdjustments
Review
Validate against constraints + realism gate
ReviewReport (pass / fail + issues), optional RepairHints

Pipeline (from problem statement):
Orchestrator → parallel(Destination, Logistics, Budget) → Review
The orchestrator produces a shared constraint object early; synthesis happens after parallel agents return (possibly with a second orchestrator pass if Review fails).
4. Orchestration flow
How agents “talk”: there is no Destination ↔ Logistics ↔ Budget messaging. Each specialist receives the same read-only TravelConstraints from the Orchestrator, returns one typed artifact to the Orchestrator, and only after that does the Orchestrator merge into DraftItinerary and send that (plus constraints) to Review. Review returns ReviewReport (and optional RepairHints) to the Orchestrator; repair is orchestrator-driven, not worker-to-Review.
Communication topology (hub-and-spoke)
Only the Orchestrator routes messages; Review never invokes workers directly—only the Orchestrator does, after interpreting ReviewReport / RepairHints.
Design notes
Parallel agents share the same read-only TravelConstraints; they should not each re-parse the raw user string differently (avoids inconsistent duration/cities/budget).
Merge point is orchestrator-owned: Destination suggests what; Logistics sequences when and where; Budget may trim or substitute items—conflicts resolved in one place.
Review is a hard gate before user delivery; optional repair loop (orchestrator adjusts, re-runs Review) keeps quality without infinite loops (e.g. max 2–3 cycles).
5. Core data model (shared artifacts)
Contracts between agents; implementation can use JSON Schema, Pydantic, or equivalent.
TravelConstraints (orchestrator output, input to all workers)
destination_region, cities[], duration_days
budget_total, currency
preferences[], avoidances[] (e.g. crowds)
hard_requirements vs soft_preferences (if inferred)
ActivityCatalog (Destination)
Per city: activities[] with type (temple, food, etc.), estimated_duration, crowd_level (ordinal or tag), cost_band, must_do flag, rationale
LodgingPlan + MovementPlan (Logistics)
Nights per city / area; suggested neighborhoods (align with Destination)
Inter-city mode (e.g. Shinkansen), rough frequency/cost band
DaySkeleton[]: ordered slots with travel time estimates between slots
BudgetBreakdown (Budget)
Per category totals and per-day optional rollup
within_budget: bool, violations[], suggested_swaps[] (e.g. cheaper Tokyo area)
DraftItinerary (Orchestrator merge)
Day-by-day narrative + structured slots linking to catalog IDs
Embedded or referenced budget summary
ReviewReport (Review)
Boolean checklist: days match, cities included, budget, prefs, crowd avoidance effort, logistics realism
severity per issue; blocking vs advisory
Stable IDs on activities and lodging suggestions make merge and re-review deterministic.
6. Agent interfaces (minimal API shape)
Each agent is a function or service with:
Input: TravelConstraints + role-specific brief (e.g. Budget may use skeleton + catalog cost bands on first pass; second pass may consume full DraftItinerary).
Output: one primary artifact (above) + optional confidence / assumptions[].
Orchestrator additionally exposes:
plan(request) -> FinalItinerary
Internal: merge(catalog, logistics, budget) -> DraftItinerary
Review optionally returns RepairHints (e.g. “remove one full-day Kyoto block” / “increase Shinkansen buffer”) for the orchestrator to apply programmatically or via LLM.
7. Tooling layer (capabilities, not agents)
Keep tools separate from agent personas so implementations can swap.
Tool category
Used by
Examples
Search / retrieval
Destination (mainly)
Web search, curated snippets
Geo / routing
Logistics
Distances, rough transit times
Pricing
Budget (+ Logistics for transport bands)
Hotel/food/activity ranges or static tables
FX
Budget
Currency conversion to a single reporting currency

Agents call tools through a single tool router with logging, timeouts, and caching (same query → same snippet) to control cost and variance.
8. Execution and deployment views
Full stack
Backend process (or serverless bundle) hosts the API and MAS; scales on CPU/LLM wait time and concurrent requests.
Frontend is static or edge-hosted; scales cheaply via CDN. Build pipeline produces assets that point at the correct API base URL per environment (dev/stage/prod).
Logical deployment
Monolith acceptable: one process runs orchestration + agent prompts in sequence/parallel (async tasks).
Scalable variant: orchestrator as workflow engine (e.g. step functions / queue); each agent as stateless worker reading/writing a versioned PlanState document in a store.
Concurrency
Parallel phase: three LLM calls (or three subgraphs) with shared constraints and idempotency keys on persisted state.
State
Ephemeral: in-memory for demos.
Durable: store TravelConstraints, each agent output, each DraftItinerary version, and ReviewReport for audit and debugging.
9. Non-functional architecture
Concern
Approach
Latency
Parallelize Destination / Logistics / Budget; cap tool calls per agent; stream orchestrator narrative if UX needs it
Cost
Smaller models for Review checklist + structured extraction; larger model for merge/narrative only
Determinism
Structured outputs (JSON schema); temperature low for Review and constraint extraction
Safety
No real PII required; disclaimers that plans are illustrative; no guaranteed prices
Observability
Trace ID per request; log prompts, tool calls, parsed artifacts, Review outcome
Failure
Per-agent timeout → partial plan with explicit “missing logistics” section; or retry single agent

10. Review agent — internal design
Treat Review as two layers:
Programmatic checks (cheap, reliable): duration_days == len(days), cities ⊆ plan, numeric budget ≤ cap (using Budget’s numbers).
LLM qualitative checks (prefs, crowd avoidance, narrative coherence): structured rubric → ReviewReport.
If programmatic checks fail, you can skip or shorten the LLM pass and still return actionable errors.
11. Optional extensions (out of minimal scope)
Human-in-the-loop after Review fail.
Specialist sub-agents (e.g. “temples only”) behind Destination for modularity.
RAG over internal travel guides instead of open web.
Separate “Presenter” agent that only formats markdown for UI, keeping policy logic out of prose generation.
12. Summary
The architecture centers on a constraint-first orchestrator, three parallel specialists (experiences, logistics, money), a merge step into a draft itinerary, and a Review gate with optional repair loops. Shared typed artifacts between steps keep agents aligned and make validation and debugging straightforward for a PM-friendly demo of multi-agent collaboration.
The backend encapsulates all agent and tool execution behind a small HTTP API; the frontend provides request entry and structured presentation of the plan, staying free of secrets and heavy business logic.
