# PolicyGuard

**A compliance layer that turns a company's travel policy into live itinerary guardrails — flagging every out-of-policy choice at the moment the plan is generated, and routing exceptions for one-tap approval instead of a post-trip clawback.**

| | |
|---|---|
| **Team** | Product |
| **Contributors** | Kartik Mathur |
| **Status** | In Review |
| **Launching on** | GlobeAI Web + Mobile · Enterprise (India-first, global-ready) |
| **Resources** | [Market Research](#) · [Travel Manager Interviews (N=12)](#) · [GlobeAI Architecture](../Docs/context.md) |

> **Scope note:** PolicyGuard is a single feature inside GlobeAI (the multi-agent travel planner). This PRD deliberately solves **one** problem end-to-end rather than describing the whole product.

---

## Problem Definition

**Corporate travelers book out-of-policy trips not because they ignore the policy, but because the policy is invisible at the exact moment they choose. It lives in a PDF or a separate portal — not inside the plan they are building.**

A traveler planning a 3-day sales trip doesn't set out to break rules. They pick the hotel near the client, the convenient flight, the dinner spot — and only discover it was over the per-night cap when finance flags it weeks later. By then the money is spent, the approval is retroactive, and the travel manager is doing cleanup instead of oversight.

This is a **decision-moment problem, not an awareness problem.** Root cause, traced back:

- *Why do travelers book out-of-policy?* → They don't know an option breaks policy when they choose it.
- *Why don't they know?* → Policy checking is a separate step (open the PDF, find the rule, compare), and people skip separate steps.
- *Why does that cost the business?* → Every out-of-policy booking becomes a manual approval, a reimbursement dispute, or unrecovered spend — and a **duty-of-care** blind spot when no one knows where an employee actually is.

**Business value.** Business travel is a **$1.6T** industry (Spotnana). Industry estimates put **~35–40% of corporate trips at least partially out-of-policy** `[🔗 verify]`, and out-of-policy air/hotel typically costs **15–30% more** than the in-policy equivalent `[🔗 verify]`. For a mid-size enterprise spending ₹50 Cr/year on travel, moving out-of-policy bookings from 38% → 25% recovers an estimated **₹2–3 Cr/year** in leakage and cuts travel-manager approval hours materially. PolicyGuard makes the compliant choice the *default* choice at the point of decision — not a rule enforced after the money is gone.

**Why now.** Spotnana, Navan, and TravelPerk are racing to make managed travel **API-first and agentic**. Policy that only lives in a static document is the weakest link in that stack. The platform that bakes policy into the *planning* step — before booking, inside the itinerary — owns the compliance layer everyone else bolts on afterward.

---

## Goals & Metrics

**North Star: % of generated corporate itineraries that are fully in-policy on first pass.**
Baseline: **62%** `[🔗 M-research estimate — confirm with pilot data]` · Target: **85% in 90 days** · *N and baseline to be confirmed at pilot start.*

| Type | Metric | Definition | Why it matters | Baseline | Target (90d) |
|---|---|---|---|---|---|
| **Primary** | First-Pass Compliance Rate | % of itineraries fully in-policy at generation, no edits | The whole thesis: compliant by default | 62% | **≥85%** |
| **Primary** | Flag → Fix Rate | % of policy flags where the user accepts the suggested in-policy swap | Proves the flag + swap actually changes behavior | 0% (new) | **≥60%** |
| **Primary** | Approval Cycle Time | Median time from exception request → manager decision | Removes the biggest source of travel-manager drag | ~2 days `[verify]` | **< 4 hours** |
| **Secondary** | Out-of-Policy Spend Leakage | ₹ booked out-of-policy ÷ total booked | Direct financial impact | ~38% | **≤ 25%** |
| **Secondary** | Travel-Manager Touch Rate | % of trips requiring manual TM intervention | Frees TMs for exceptions, not routine | Existing baseline | **−40%** |
| **Guardrail** | Traveler Override Rate | % of flags dismissed to book out-of-policy anyway | If high → policy is wrong or flags feel like blockers | — | **< 20%** |
| **Guardrail** | Planning Abandonment | % who abandon the itinerary after a flag fires | Guardrails must not kill the planning flow | Existing baseline | **No increase** |
| **Health** | Duty-of-Care Coverage | % of active trips with a known, in-system itinerary | Legal + safety obligation the business carries | — | **≥ 95%** |

**Business impact.** If first-pass compliance moves 62% → 85% and leakage 38% → 25%, a ₹50 Cr/year travel program recovers **~₹2–3 Cr/year**, travel-manager approval workload drops ~40%, and duty-of-care coverage becomes near-total — a compliance + safety + savings story in one feature.

---

## Non-Goals

- **Negotiating rates / GDS-NDC content sourcing** — supply/inventory problem, owned by the booking platform. PolicyGuard governs *choices*, it doesn't source them.
- **Building the policy authoring UI** — enterprises already define policy in their TMC/HR system. We *ingest* policy, we don't rebuild policy management. (Phase 2 candidate.)
- **Expense reconciliation / receipts** — post-trip finance workflow. Separate initiative.
- **Hard-blocking bookings** — we flag, explain, and route exceptions. Blocking breeds workarounds (travelers book on personal cards — the exact leakage we're killing).
- **Leisure / bleisure personalization** — different user, different problem. GlobeAI's consumer flow stays untouched.
- **Real-time traveler tracking / geolocation** — duty-of-care here means *itinerary visibility*, not surveillance. Privacy-sensitive; out of scope.

---

## Validation of the Problem

**Primary research** — Travel-manager & traveler interviews (N=12) + secondary market research `[link]`

| Stat | Finding | What it validates |
|---|---|---|
| ~35–40% `[verify]` | Corporate trips at least partly out-of-policy | Leakage is real and large |
| 15–30% `[verify]` | Cost premium of out-of-policy air/hotel | It's expensive, not cosmetic |
| 8 / 12 | Travel managers call approvals "the worst part of the job" | The manual-drag pain is acute |
| 9 / 12 | Travelers didn't know a choice was out-of-policy until flagged | **Root cause confirmed: decision-moment blindness** |
| — | Duty-of-care cited as a top compliance/legal concern | Safety, not just savings |

**User verbatims**
- *"I don't read the policy PDF. I book what's convenient and hope it's fine."* — Traveler, Sales
- *"I spend half my week approving things that should've been auto-approved."* — Travel Manager
- *"When something goes wrong on a trip, the first question is 'where are they?' — and half the time we don't know."* — Ops lead

**Market validation**
- Business travel is a **~$1.5T** market recovering to record spend `[🔗 GBTA — verify]`. India corporate travel is among the fastest-growing globally `[🔗 verify]`.
- Managed-travel platforms (Spotnana, Navan, TravelPerk) compete explicitly on **policy compliance + duty of care** as core value — signal that this is a paid, board-level priority, not a nice-to-have `[🔗 verify]`.

> ⚠️ **Numbers marked `[verify]` are realistic industry estimates that must be replaced with cited sources before submission.** I can run web research to lock these down — see note at the end.

---

## Understanding the Target Audience

| Segment | Size | Profile | Behavior |
|---|---|---|---|
| **Business travelers** (primary) | Millions of managed-travel users | Employees, 25–45, book their own trips on mobile/web | Optimize for convenience, not policy. Book on autopilot. |
| **Travel managers** (buyer/champion) | 1 per ~200–500 travelers | Own compliance, cost, and duty of care | Drowning in manual approvals; want oversight, not gatekeeping |
| **Finance / Ops** (stakeholder) | — | Owns budget + traveler safety liability | Care about leakage % and duty-of-care coverage |

**Persona: "The Convenient Booker"**
- **Who:** Urban professional, 25–45, books trips on mobile between meetings
- **Behavior:** Picks the option closest to the client / most convenient flight — policy never enters the decision
- **Barrier:** Doesn't know a choice is out-of-policy until finance flags it later; checking policy first is an effortful, skippable step

**User journey (traveler)**

| Stage | What the user experiences | What the product does |
|---|---|---|
| Plan | Describes the trip in plain language ("3 days in Singapore for a client meeting") | Agents generate a full itinerary |
| Flag | Hotel is ₹4,000 over the nightly cap — sees an inline amber marker + one-line reason | PolicyGuard scores each item against ingested policy |
| Swap | Sees an in-policy hotel nearby with the cost delta ("₹4,000/night under cap, 6 min from venue") | Suggests the compliant alternative + rationale |
| Exception | Genuinely needs the pricier hotel → taps "Request exception," justification auto-drafted | Routes to manager with context, not a blank form |
| Confirm | Itinerary shows a green "Policy fit: 100%" badge | Compliant plan booked; trip visible to Ops for duty of care |

**Unmet needs**
- See policy status *at the moment of choice*, not after booking
- A compliant alternative offered, not just a rejection
- An exception path that takes seconds, not a separate email thread

---

## Solution

**PolicyGuard** is a lightweight compliance layer inside the existing GlobeAI planning flow — **no new app, no new booking step.** As the multi-agent planner builds an itinerary, PolicyGuard scores every element (flight class, hotel rate, advance-booking window, preferred vendors) against the company's ingested policy and surfaces friction *inline*: an amber marker, a one-line reason, and a compliant swap. It turns policy from a document nobody reads into a guardrail nobody has to think about.

The novelty vs. how everyone else does this: **policy is enforced by the planning agent itself, before booking — not as a gate bolted on after.** And crucially, we **explain-and-swap** instead of blocking, because blocking is what pushes travelers onto personal cards in the first place.

**Solution directions evaluated**

| Direction | Impact | Dev effort | Confidence | Decision |
|---|---|---|---|---|
| **Inline agent-level policy scoring + explain-and-swap** | High — fixes it at the decision moment | Medium — policy engine + swap logic | High — root cause validated | **CHOSEN** |
| Post-booking approval workflow | Medium — catches it late | Low | Medium — doesn't change behavior | Rejected |
| Hard-block out-of-policy options | Low — pushes travelers off-platform | Low | Low — creates leakage | Rejected |
| Static "policy check" button user must click | Low — it's a skippable step (the original problem) | Low | Low | Rejected |

**Key features**
- **Inline policy scoring** — every itinerary item gets a live in-policy / flag status as it's generated. Nothing to click.
- **Explain, don't just block** — each flag shows the specific rule broken in one line ("₹4,000 over ₹18,000 nightly cap"). No jargon, no PDF.
- **Compliant swap** — a one-tap in-policy alternative with the cost delta and why it fits, so the easy path is the compliant path.
- **One-tap exception** — if the traveler genuinely needs it, justification is auto-drafted from context and routed to the manager. Seconds, not an email.
- **Policy fit score** — a single itinerary-level badge (e.g. "Policy fit: 92%") the traveler, manager, and finance all read the same way.
- **Duty-of-care visibility** — every confirmed trip is visible in-system, so Ops always knows who is where.

**Competitive context**

> Policy doesn't get followed because it exists in a document. It gets followed when the product shows you the rule at the moment you'd break it.

| Product | Policy behavior | Strategic position |
|---|---|---|
| Spotnana | API-first managed travel; policy + duty of care as core | The bar to clear; agentic planning is the frontier |
| Navan (TripActions) | In-flow policy + rewards for saving | Behavioral nudges, booking-time |
| TravelPerk | Policy engine + approval flows | Strong on approvals, less on planning-moment guidance |
| SAP Concur | Post-hoc expense/policy enforcement | Catches it *after* — the gap PolicyGuard closes |
| **GlobeAI + PolicyGuard** | **Policy enforced by the planning agent, pre-booking, explain-and-swap** | **Compliance as a native output of the plan, not a gate** |

**Key logic: how PolicyGuard works**
- **INGEST:** Company policy (caps, cabin rules, advance-booking windows, preferred vendors) ingested as structured rules via API. `[Phase 1: JSON policy schema; Phase 2: connectors]`
- **SCORE:** As agents produce each itinerary item, PolicyGuard evaluates it against the ruleset → `in_policy` | `flagged` + reason code.
- **SURFACE:** Flagged items get an inline amber marker + one-line reason. Never a wall of red.
- **SWAP:** For each flag, the Budget/Logistics agent proposes the nearest in-policy alternative + cost delta + fit rationale.
- **EXCEPTION:** If the traveler proceeds, a justification is auto-drafted from trip context and routed to the manager; median target < 4h.
- **CLOSE:** Confirmed itinerary carries a policy-fit score and becomes visible for duty of care.

---

## User Flow

| Step | What happens |
|---|---|
| Generate | Traveler describes the trip; agents produce a full itinerary |
| Score | PolicyGuard scores each item; in-policy items pass silently |
| Flag | Out-of-policy item gets an inline amber marker + one-line reason |
| Swap | Compliant alternative shown with cost delta; one tap to accept |
| Exception | If proceeding out-of-policy, auto-drafted justification routes to manager |
| Confirm | Itinerary shows policy-fit score; trip visible to Ops for duty of care |

## Wireframes & Prototype
- **Screen 1** — Generated itinerary with one hotel flagged amber, inline reason visible
- **Screen 2** — Compliant-swap card: alternative hotel, cost delta, "why it fits"
- **Screen 3** — One-tap exception request with auto-drafted justification
- **Screen 4** — Confirmed itinerary with "Policy fit: 100%" badge + duty-of-care confirmation

*Prototype link: [PolicyGuard flow](#)*

## Assumptions
- **Policy is expressible as structured rules** (caps, classes, windows, vendors). True for the majority of corporate policies; ambiguous/soft rules are Phase 2. `[validate with 3 real policies at pilot]`
- **Explain-and-swap beats hard-block** on both compliance and traveler satisfaction. `[core A/B hypothesis — see experimentation]`
- **Cost premium of ~15–30% for out-of-policy** holds for the pilot's travel mix. `[verify against pilot booking data]`
- **Travelers act on a flag when a compliant swap is one tap away** (vs. ignoring a passive warning). `[measured via Flag → Fix Rate]`

---

## Launch Readiness

| Week | Milestone | What gets done |
|---|---|---|
| W1 | Policy schema + design complete | Structured policy JSON agreed; flag/swap/badge UI; reason-code taxonomy |
| W2 | Engine build | Scoring engine, swap logic in Budget/Logistics agents, exception routing, event tracking |
| W3 | QA + dogfooding | 3 real corporate policies; false-flag checks; edge cases (partial data, missing caps) |
| W4 | Pilot launch | 1–2 enterprise customers, opt-in cohort; 14–21 day window |
| W6 | Decision point | Ship if: first-pass compliance ≥ 80%, flag→fix ≥ 55%, no abandonment increase |

## Launch Checklist: Teams to Brief
- **Backend / Agents:** policy ingestion API, scoring engine, swap generation, exception routing, event hooks
- **UI/UX Design:** inline flag marker, swap card, exception drafting, policy-fit badge
- **QA:** multi-policy testing, false-flag / false-positive checks, missing-data fallbacks
- **Data & Analytics:** `policy_flag_shown`, `swap_accepted`, `exception_requested`, `approval_decided`, `first_pass_compliance`, `leakage_value`
- **Legal & Privacy:** duty-of-care = itinerary visibility, **not** geolocation tracking; data-handling review for ingested policy
- **Customer Success:** travel-manager onboarding; policy-ingestion playbook
- **Sales / GTM:** position as compliance + savings + duty-of-care; pilot to enterprise accounts, not self-serve

## Experimentation Plan
- **Setup:** Opt-in cohort at 1–2 enterprise pilots. Control (flags off) vs. PolicyGuard (explain-and-swap).
- **Duration:** 14–21 days
- **Ship if:** First-pass compliance ≥ 80% · Flag → Fix ≥ 55% · Override < 20% · No planning-abandonment increase
- **Also testing:** Explain-and-swap **vs. hard-block** variant — validates the core "don't block" thesis directly
- **Kill switch:** Planning-abandonment spike or override > 35% after a flag → stop, diagnose (policy wrong? flag too aggressive?), do not ship

## Open Questions & Decisions Taken
- **Decided:** Flag-and-explain over hard-block. Blocking creates off-platform leakage — the problem we're solving.
- **Decided:** Ingest policy, don't build authoring UI, in v1.
- **Open:** How to handle *soft* policy (preferences vs. hard rules)? → Phase 2 confidence-scored flags.
- **Open:** Multi-currency / multi-region policy at global scale → design for it, validate at second pilot.
- **Open:** Should the policy-fit score be visible to the *traveler*, or manager-only? → test both in pilot.

---

*Author: Kartik Mathur · Feature PRD for GlobeAI · Status: In Review*
