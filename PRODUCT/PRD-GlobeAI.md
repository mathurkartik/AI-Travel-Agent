# GlobeAI: Product Requirements Document

A multi-agent AI planner that turns a plain-language travel request into a structured, day-by-day itinerary within the traveller's budget and preferences. Before the plan reaches the traveller, an automated quality check catches an off-brief itinerary and repairs it.

| | |
|---|---|
| Product | GlobeAI |
| Type | Consumer travel planning · one problem, end to end |
| Status | Built and deployed. Multi-agent FastAPI backend and React frontend. Demo-stage, no production traffic yet. |
| Surfaces | Web application, JSON API |
| Author | Kartik Mathur |

---

## Problem

Anyone who has planned a multi-day, multi-city trip describes the same slog: four jobs at once across a dozen browser tabs. You research what to see, sequence it into a route that doesn't zig-zag across a country, keep the whole thing inside a budget, and then check that the result matches what you asked for. The work is less hard than it is unreconciled. Each decision affects the others, and no single place holds all four at once, so most people settle for a generic plan or wing it.

The obvious modern fix, asking one AI model for the whole itinerary, doesn't close the gap. A single prompt returns something fluent and plausible that is often over budget, geographically incoherent, or quietly missing a stated constraint, with no step in between to catch the error. The output looks right, which is more dangerous than looking wrong.

Stated as one problem: travellers can't trust an AI-generated itinerary, because nothing verifies the plan against what they asked for before they see it. Why don't they trust it? Because plans break constraints silently. Why silently? Because generation and checking are the same step, so there is no independent reviewer. Take that away and the plan is only as good as one model's first guess. The missing piece is a step that checks the plan against the request and repairs it when it fails. That is what GlobeAI is built around.

There is a reason this matters commercially. AI trip planning is a crowded category now: ChatGPT and Gemini prompts, Mindtrip, Layla, Wonderplan. Almost all of them compete on how good the generated plan looks and stop there. The thing that actually earns trust, and trust is what turns a novelty into a habit, is a plan that has been checked and corrected against the user's own words. That is the gap GlobeAI goes after.

## Target user

A leisure traveller planning a trip of several days, usually across more than one city, who can state what they want in a sentence ("five days in Japan, Tokyo and Kyoto, ₹250k, love food and temples, hate crowds") but doesn't want to build the plan themselves. They want a usable itinerary that fits their money and their taste. They do not want to configure a tool.

This is a single-session, self-serve user. It is not a corporate traveller, a travel manager, or a finance owner, so there is no policy, approval, or duty of care. That is a different user and a different product.

## Goals

- Turn a one-line request into a complete day-by-day itinerary with no further input.
- Keep the delivered plan inside the stated budget, or say clearly when the request can't be met inside it.
- Respect stated preferences, avoidances, and hard requirements, such as both named cities appearing.
- Catch an incoherent or off-brief itinerary automatically and repair it before delivery. This is the core promise.
- Return a plan fast enough to feel interactive rather than batch.

## Scope

### Must have, v1 (all built)

- The Orchestrator extracts a typed constraint set from the free-text request using the LLM (Groq llama-3.3-70b, temperature 0.1 for determinism): region, cities, duration, budget, currency, preferences, avoidances, hard requirements, soft preferences, and an is_road_trip flag.
- When a trip runs longer than 7 days or is a road trip, a Trip Structuring agent splits it into ordered geographic regions, each with a base location and a day allocation, so the itinerary is a real route instead of a flat list.
- Destination, Logistics, and Budget agents run at the same time, per region, to keep latency down. Destination returns an activity catalogue tagged by type, cost band, duration, and crowd level, with a rationale on each activity tied to the request. Logistics returns lodging, inter-city movement, and per-day skeletons. Budget returns a categorised breakdown across stay, food, transport, and activities.
- A Review agent validates the merged draft and returns pass, warnings, or fail, marking each issue blocking or advisory. A failing plan triggers up to 3 automated repair cycles (trim cost, add or remove days, resequence day numbers, fix wrong-city days, fill empty days), re-reviewing after each one. If it still fails, the best-effort plan ships with an explicit warning in the disclaimer.
- Per-agent 30-second timeouts produce partial plans instead of crashes, and a failed agent falls back to a static catalogue. If the LLM is unavailable or the daily token budget is spent, a fully deterministic stub generator returns a coherent itinerary from curated route templates (Iceland, Norway, New Zealand, Thailand, India, Japan, and others).
- An LLM pass adds a strategic summary, a budget reality check, and a few trip-specific cost-saving tips, with a static fallback.
- The user can submit a booking request from the finished itinerary. This is a request, not a transaction: it notifies the operator, and it does not book, hold inventory, or take payment.
- Every request carries a trace ID; agent lifecycle, review outcome, and repair actions are logged; token use is tracked against a 100k/day budget with a 20% safety buffer, and responses are cached to cut repeat spend.

### Nice to have, P1

- A real LLM qualitative review. Today "Layer 2" of Review is a heuristic: it counts preference keywords and composes a summary, but it never asks the model to judge coherence or taste-fit. Model-judged review, with the deterministic checks kept underneath it, is the highest-value next step.
- A single, currency-consistent cost model. Today the within-budget check compares a cost-band sum against the budget in possibly different units, so it passes too easily. Reconcile activity costs and the category budget into one figure the reviewer can trust. (See Risks.)
- Surface the less-crowded alternative already modelled on each activity, for travellers who ask to avoid crowds.

### Future, P2

- Ground places, costs, and opening times against a live source (search, pricing, and geo tools are already stubbed behind feature flags) instead of relying on model knowledge.
- Saved trips, and iteration on a previous plan.

## How it works

The Orchestrator is the central coordinator in a hub-and-spoke pipeline, and only it routes messages; the workers never talk to each other. It extracts constraints, optionally hands them to the Trip Structuring agent to build a regional skeleton, then runs Destination, Logistics, and Budget at the same time (per region when structured). Their outputs are merged into a draft, which the Review agent validates. On a fail it repairs and re-reviews, up to three times. On a pass it delivers the final itinerary with insights and a disclaimer.

The repair loop works because the contract between agents is a fixed, schema-validated data model. Every agent reads and writes typed objects, not free text. Because the constraint set, trip structure, activity catalogue, and review verdict are all typed, the reviewer can point at a specific failed check ("day count is 6, should be 5") and the repair step can act on that exact issue instead of regenerating the whole plan blindly.

The Review agent runs deterministic checks: day count against duration, all required cities present, total against budget, no empty days, no duplicate day numbers, and a couple of geographic and variety heuristics for long trips. Each result is marked blocking or advisory. Blocking failures like a wrong day count or a missing city force a repair cycle; advisory ones like mild overspend or repetitive days ship as warnings. This is the step a single-prompt planner does not have, and it is the reason to trust the output.

## Success metrics

No production traffic exists yet, so every target below is a pre-launch hypothesis to confirm against real usage, and the baselines are still to be measured. The leading indicators are already instrumented in the build; the lagging ones need real users. For the leading indicators, the method is to run the existing instrumentation over a fixed test set of representative requests. For the lagging ones, it is real-session logging plus a lightweight thumbs or edit-distance signal once there are users.

| Metric | Type | What it measures | Instrumented today | Target (hypothesis) |
|---|---|---|---|---|
| First-pass review rate | Leading | Itineraries clearing Review with no blocking issue on attempt 1 | Yes (review_status) | To set, e.g. ≥ 80% |
| Repair recovery rate | Leading | Failing itineraries that reach pass within the 3-cycle budget | Yes (repair count) | To set, e.g. ≥ 90% of fails recovered |
| Within-budget rate | Leading | Delivered plans whose estimated cost sits inside budget | Yes, but weak (see Risks) | To set, e.g. ≥ 95% |
| Generation latency | Leading | Median request to delivered itinerary | Yes (trace timing) | To set, target interactive feel |
| Token cost per plan | Leading | Median tokens per completed plan | Yes (token tracker) | To set, cost ceiling per plan |
| Delivery success rate | Leading | Requests returning a valid itinerary vs. an error | Yes | To set, e.g. ≥ 98% |
| Stub-mode share | Leading | Share of plans served by the deterministic fallback vs. full LLM | Yes (used_stub_mode) | Watch: a high share means the LLM path is not being exercised |
| Usable-plan rate (North Star) | Lagging | Plans a user would use with only minor edits | No, needs real users | To set from usage |
| Booking-request rate | Lagging | Finished itineraries where the user submits a booking request | Partly | To set from usage |

## Non-goals

- Real-time booking, payment, or inventory. GlobeAI produces a plan and a booking request. It does not transact, hold inventory, or take payment.
- Corporate or enterprise travel. No policy compliance, approvals, travel-manager tooling, or duty of care. Different user, different product.
- Guaranteed live accuracy. Prices, availability, and opening times are model-generated estimates, given as cost bands rather than exact figures, and they can be wrong or stale until P2 grounding lands.
- Accounts, saved history, or collaboration. The planner is single-session.
- Personalisation beyond stated preferences. Accessibility routing, dietary constraints, and similar are out of scope for v1.

## Key risks and mitigations

- Model-generated content can be wrong. Place names, addresses, costs, and opening times come from the model, not a live source, so they can be inaccurate or stale. The mitigations are cost bands instead of exact prices, a required rationale on each activity to force justification, and P2 grounding against a real places and pricing source. This is the biggest risk to trust, and it is not fully solved in v1. Say so plainly.
- The budget check is weak today. Review compares a cost-band sum (fixed values of 0, 20, 50, and 100) against the budget, which may be in a different currency unit like ₹80,000, so "within budget" passes almost trivially, while a separate and more realistic category budget goes unchecked by the reviewer. The fix is the P1 unified cost model; until then, treat within-budget rate as a soft signal, not a guarantee.
- The "qualitative" review layer is a heuristic, not judgment. Layer 2 counts keywords rather than asking the model whether the plan is genuinely coherent or on-taste, so it can miss a subtly off-brief plan that passes the deterministic checks. The deterministic layer catches the objective failures reliably; the P1 real-LLM review closes the taste and coherence gap.
- Quality is uneven across destinations. Coverage leans on curated route and activity templates for a handful of regions and on general model knowledge everywhere else, and the deployed demo may serve many plans from the deterministic stub. The mitigations are honest labelling of well-covered regions, a used_stub_mode flag surfaced in the response, and a roadmap to widen coverage.
- No live availability. A suggested hotel or activity may not be bookable at plan time. The product is framed as planning, and booking is an explicit handoff rather than a promise.
- Cost and latency scale with complexity. Multi-region trips and repeated repair cycles cost tokens and time. The mitigations are parallel execution, response caching, per-agent timeouts, token tracking with a daily buffer, and the trip-structure and pace controls that bound how much work each request generates.

## Open questions and decisions taken

- Decided: verify and repair over generate and hope. The Review gate is the product's reason to exist, not an add-on.
- Decided: graceful degradation over hard failure. A static plan beats an error screen for a demo user.
- Open: should used_stub_mode be visible to the user, for honesty, or kept in telemetry only, for polish? Leaning towards showing it.
- Open: unify the cost model (P1) before or after the real-LLM review (P1)? The budget weakness is more visible to users, so probably first.
- Open: how many curated regions are worth hand-authoring before live grounding (P2) makes them redundant?

---

*Feature-complete v1 · Status: In Review · Author: Kartik Mathur*
