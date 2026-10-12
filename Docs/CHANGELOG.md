# Changelog

All notable changes to GlobeAI are documented here.

---

## [v1.2.0] — 2026-10-12

### LLM Provider Migration & Stability Fixes

**Summary:** Resolved production pipeline failures caused by a deprecated Groq model and SDK incompatibility. Added multi-LLM support with Gemini as a fallback provider.

#### Breaking Changes

- **Groq model changed:** `llama-3.3-70b-versatile` → `openai/gpt-oss-120b`
  - `llama-3.3-70b-versatile` was [retired by Groq on August 16, 2026](https://console.groq.com/docs/deprecations)
  - `openai/gpt-oss-120b` is the official replacement recommended by Groq
  - If you have `GROQ_MODEL` set in your environment, update it to `openai/gpt-oss-120b`

- **Groq SDK upgraded:** `groq==0.4.2` → `groq>=0.13.0`
  - Required for compatibility with `httpx>=0.28.1` (which removed the deprecated `proxies` parameter)
  - The `groq` SDK API (`Groq()`, `client.chat.completions.create()`) is unchanged

- **httpx version bumped:** `httpx==0.26.0` → `httpx>=0.28.1,<1.0.0`
  - Required by `google-genai==1.14.0` (Gemini SDK)

#### New Features

- **Multi-LLM support:** Added Google Gemini as a fallback LLM provider
  - Set `LLM_PROVIDER=gemini` and `GEMINI_API_KEY` to use Gemini
  - If `GROQ_API_KEY` is missing but `GEMINI_API_KEY` is set, Gemini is used automatically
  - Gemini client implements the same interface: `chat_with_retry`, `extract_constraints`, `generate_with_schema`
  - Uses `google-genai==1.14.0` SDK with `gemini-3.5-flash` model

- **Pipeline diagnostic endpoints:**
  - `GET /api/debug/llm-test` — Smoke test verifying LLM returns text
  - `GET /api/debug/pipeline-test` — Step-by-step pipeline validation (LLM client → orchestrator init → constraint extraction → validation)

#### Bug Fixes

- **Token cap raised:** `chat_with_retry` max_tokens cap changed from `600` → `2000`
  - The 600-token cap was a debugging workaround that truncated agent JSON outputs (activity catalogs, insights), causing `json.loads()` parse failures in production
  - Agents request 300–900 tokens; the cap is now a safety ceiling, not a bottleneck

- **`lodging_area` schema limit:** Increased from 100 → 300 characters
  - LLM-generated lodging descriptions (e.g., "Le Marais (3rd/4th arrondissement)") exceeded the 100-char limit, causing 500 errors on the plan endpoint

- **`max_tokens_per_request` restored:** `900` → `4000`
  - Was reduced during Tier 1 refactor to manage OTPM pressure on the old Groq model

#### Configuration Changes

| Variable | Old Default | New Default | Notes |
|----------|------------|-------------|-------|
| `LLM_PROVIDER` | `groq` | `groq` | Now also accepts `gemini` |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | `openai/gpt-oss-120b` | Old model retired |
| `GROQ_MAX_TOKENS_PER_REQUEST` | `900` | `4000` | Restored from pre-Tier 1 value |
| `GEMINI_API_KEY` | *(new)* | `None` | Optional fallback |
| `GEMINI_MODEL` | *(new)* | `gemini-3.5-flash` | Used when provider is gemini |

#### Dependencies

```
groq>=0.13.0,<2.0.0       # was groq==0.4.2
httpx>=0.28.1,<1.0.0       # was httpx==0.26.0
google-genai==1.14.0        # new dependency
```

#### Test Results (Production — Render)

All test cases passed on the live deployment with `openai/gpt-oss-120b`:

| Destination | Days | Budget | Cities | Review | Time |
|------------|------|--------|--------|--------|------|
| New Zealand | 15 | $3,000 USD | Auckland, Rotorua, Wellington, Queenstown, Milford Sound | pass | 63s |
| Spain | 15 | 2,500 EUR | Madrid, Barcelona, Seville, Valencia | warnings | 69s |
| France | 15 | 3,000 EUR | Paris, Bordeaux, Lyon | warnings | 63s |

---

## [v1.1.0] — 2026-10-12

### Tier 1 & Tier 2: LLM-Powered Agent Outputs

**Summary:** Refactored all agents to generate content via LLM instead of using hardcoded data. Added rich output quality fields for strategic travel insights.

#### Tier 1 — Schema Enrichment

- All agents (Destination, Logistics, Budget) now use `chat_with_retry` to generate content via LLM
- Removed hardcoded activity catalogs and static route templates
- Activities, lodging plans, and budget breakdowns are now fully LLM-generated
- Added Trip Structuring Agent for trips > 7 days (geographic region decomposition)

#### Tier 2 — Richer Prompts & Insights

- Added `_generate_insights()` to Orchestrator — produces strategic travel analysis
- New output fields in `FinalItinerary`:
  - `strategic_insight` — Why the routing/pacing is smart
  - `budget_analysis` — Budget reality check (tight/comfortable/generous)
  - `cost_optimization_tips` — Specific, actionable tips for the destination
  - `why_this_plan` — How the plan matches stated preferences
  - `what_not_to_do` — Common tourist mistakes to avoid
  - `base_selection_rationale` — Why each city was chosen as a base
  - `experience_highlights` — Standout moments with tags (splurge, hidden-gem, etc.)
  - `best_time_to_visit` — Seasonal considerations

---

## [v1.0.0] — 2026-10-11

### Initial Production Release

- Multi-agent architecture with 5 agents (Orchestrator, Destination, Logistics, Budget, Review)
- Natural language constraint extraction via Groq LLM
- Strict 3-pillar validation (Destination, Duration, Budget)
- Parallel agent execution (Architecture §4, §9)
- Review → Repair loop (max 3 cycles)
- Budget breakdown with category-level tracking
- React + TypeScript frontend with responsive itinerary display
- Booking integration (email-based)
- Docker deployment support
- Deployed on Render (backend) + Vercel (frontend)
