# Test Plan - AI Travel Planner (Groq Edition)

**Document Version:** 1.0  
**Date:** 2026-04-27  
**Constraint:** Groq API - 100,000 tokens/day limit  

---

## 1. Overview

### Token Budget Context
- **Daily Limit:** 100,000 tokens (Groq free tier)
- **Safety Buffer:** 20% (20,000 tokens reserved)
- **Effective Budget:** 80,000 tokens/day for testing
- **Per-Request Limit:** ~15,000 tokens max (configured)

### Testing Philosophy
1. **Unit Tests:** Run without LLM calls (mocked/stubbed) - 0 tokens
2. **Integration Tests:** Use real LLM calls selectively with caching
3. **E2E Tests:** Minimal, high-value scenarios only
4. **Token Tracking:** All LLM calls logged and counted

---

## 2. Test Categories & Token Budget

| Category | Test Count | Avg Tokens/Test | Total Tokens | Priority |
|----------|-----------|-----------------|--------------|----------|
| **Unit Tests (No LLM)** | 70+ | 0 | 0 | Must Run |
| **Schema Validation** | 56+ | 0 | 0 | Must Run |
| **LLM Integration** | 10 | 3,000 | 30,000 | Daily Run |
| **E2E Pipeline** | 5 | 8,000 | 40,000 | Weekly Run |
| **Edge Case E2E** | 3 | 5,000 | 15,000 | As Needed |
| **Buffer** | - | - | 15,000 | Contingency |
| **TOTAL** | **140+** | - | **~100,000** | - |

---

## 3. Unit Tests (0 Tokens) - Phase 0-1

### 3.1 Schema Validation (`test_schemas.py`)
**File:** `backend/tests/test_schemas.py`  
**Token Cost:** 0 (no LLM calls)  
**Run Frequency:** Every commit  
**Test Count:** 13+ tests

| Test Class | Purpose | Count |
|------------|---------|-------|
| `TestTravelConstraints` | Core constraint model | 6 tests |
| `TestActivityCatalog` | Destination agent output | 3 tests |
| `TestBudgetBreakdown` | Budget validation | 4 tests |
| `TestGoldenFixture` | Japan fixture round-trip | 1 test |

**Run Command:**
```bash
pytest backend/tests/test_schemas.py -v
```

### 3.2 Edge Case Tests (`test_edge_cases.py`)
**File:** `backend/tests/test_edge_cases.py`  
**Token Cost:** 0 (no LLM calls)  
**Run Frequency:** Every commit  
**Test Count:** 56+ tests

| Test Class | Edge Cases Covered | Count |
|------------|---------------------|-------|
| `TestTravelConstraintsEdgeCases` | Boundaries, duplicates, currency | 15 tests |
| `TestActivityEdgeCases` | ID format, duration, tags | 12 tests |
| `TestActivityCatalogEdgeCases` | Empty lists, invalid refs | 2 tests |
| `TestBudgetBreakdownEdgeCases` | Mismatches, violations, limits | 14 tests |
| `TestDayItineraryEdgeCases` | Slots, costs, boundaries | 8 tests |
| `TestIntegrationEdgeCases` | Unicode, precision | 5 tests |

**Run Command:**
```bash
pytest backend/tests/test_edge_cases.py -v
```

### 3.3 Token Tracker Tests (`test_token_tracker.py`)
**File:** `backend/tests/test_token_tracker.py` (create)  
**Token Cost:** 0  
**Test Count:** 8 tests

```python
# Test scenarios
- test_daily_reset_at_midnight
- test_budget_check_allows_safe_request
- test_budget_check_blocks_excessive_request
- test_remaining_tokens_calculation
- test_percent_used_calculation
- test_usage_summary_by_model
- test_thread_safety_concurrent_updates
- test_estimate_request_cost_accuracy
```

---

## 4. Integration Tests (30,000 tokens budget) - Phase 2-4

### 4.1 Groq Client Integration (`test_groq_client.py`)
**File:** `backend/tests/test_groq_client.py` (create)  
**Token Budget:** 15,000 tokens  
**Run Frequency:** Once per day (CI/CD)  
**Test Count:** 5 tests

| Test | Scenario | Est. Tokens | Cache |
|------|----------|-------------|-------|
| `test_extract_constraints_japan` | Japan 5-day extraction | ~3,000 | Yes |
| `test_extract_constraints_europe` | Europe multi-city | ~3,500 | Yes |
| `test_cache_hit_returns_cached` | Verify caching works | ~500 | N/A |
| `test_token_budget_enforced` | Budget exceeded error | ~500 | N/A |
| `test_invalid_request_handling` | Malformed input | ~1,000 | Yes |

**Run Command:**
```bash
# With token tracking enabled
GROQ_API_KEY=gsk_... pytest backend/tests/test_groq_client.py -v --tb=short
```

**Optimization:**
- All tests use `enable_cache=True` (default)
- Repeated prompts return cached responses (0 tokens)
- Clear cache between test runs: `get_cache().clear()`

### 4.2 Agent Stub Tests (`test_agents.py`)
**File:** `backend/tests/test_agents.py` (create)  
**Token Cost:** 0 (stubs don't call LLM)  
**Run Frequency:** Every commit  
**Test Count:** 8 tests

| Agent | Test | Status |
|-------|------|--------|
| Orchestrator | `test_extract_constraints_stub` | Raises NotImplementedError |
| Destination | `test_research_activities_stub` | Returns mock catalog |
| Logistics | `test_plan_lodging_stub` | Returns mock lodging |
| Budget | `test_calculate_budget_stub` | Returns static prices |
| Review | `test_validate_draft_stub` | Returns mock report |

---

## 5. E2E Tests (40,000 tokens budget) - Phase 5-7

### 5.1 Full Pipeline E2E (`test_e2e_pipeline.py`)
**File:** `backend/tests/test_e2e_pipeline.py` (create)  
**Token Budget:** 40,000 tokens  
**Run Frequency:** Weekly or pre-release  
**Test Count:** 5 tests  
**Prerequisites:** All unit + integration tests pass

| Test | Scenario | Est. Tokens | Agents Called |
|------|----------|-------------|---------------|
| `test_japan_5day_full_pipeline` | Japan trip, all agents | ~15,000 | 4 agents + review |
| `test_bali_3day_budget_focus` | Budget optimization | ~10,000 | 4 agents + 1 repair |
| `test_europe_7day_complex` | Multi-city logistics | ~18,000 | 4 agents + 2 repairs |
| `test_single_city_simple` | Simple 2-day trip | ~5,000 | 4 agents |
| `test_review_repair_loop` | Intentional failure + fix | ~12,000 | 4 agents + 2 review cycles |

**Run Command:**
```bash
# Weekly full test (expensive)
GROQ_API_KEY=gsk_... pytest backend/tests/test_e2e_pipeline.py -v --tb=short -x
```

**Token Monitoring:**
```python
# Each test logs usage
summary = groq_client.get_token_summary()
print(f"Tokens used: {summary['daily_total']}/{summary['daily_limit']}")
print(f"Remaining: {summary['remaining']}")
```

### 5.2 API Endpoint Tests (`test_api.py`)
**File:** `backend/tests/test_api.py`  
**Token Cost:** 0 (uses stub responses)  
**Run Frequency:** Every commit  
**Test Count:** 6 tests

| Endpoint | Test |
|----------|------|
| `GET /health` | Returns healthy status |
| `POST /api/plan` | Returns stub with trace_id |
| `POST /api/plan` | Validates request body |
| `GET /plan/{id}` | Returns 501 (not implemented) |
| Error handling | Returns trace_id on 500 |
| CORS | Accepts frontend origin |

---

## 6. Token-Efficient Testing Strategies

### 6.1 Caching Strategy
```python
# All tests use cache by default
from app.llm import get_cache, get_groq_client

# Before expensive test suite
cache = get_cache()
cache.clear()  # Start fresh

# After tests - check savings
stats = cache.get_stats()
savings = cache.estimate_savings(avg_tokens_per_request=3000)
print(f"Cache hit rate: {stats['hit_rate_percent']}%")
print(f"Tokens saved: {savings['tokens_saved']}")
```

### 6.2 Test Fixtures (Pre-computed)
Instead of calling LLM for every test, use pre-computed fixtures:

```python
# backend/tests/fixtures/llm_responses.py
JAPAN_CONSTRAINTS_RESPONSE = {
    "destination_region": "Japan",
    "cities": ["Tokyo", "Kyoto"],
    "duration_days": 5,
    "budget_total": 3000,
    "currency": "USD",
    "preferences": ["food", "temples"],
    "avoidances": ["crowds"],
}

# Mock the LLM client in unit tests
@pytest.fixture
def mock_groq_client():
    client = MagicMock()
    client.extract_constraints.return_value = TravelConstraints(**JAPAN_CONSTRAINTS_RESPONSE)
    return client
```

### 6.3 Progressive Test Execution
```bash
# Level 1: Unit tests (0 tokens) - Always run
pytest backend/tests/test_schemas.py backend/tests/test_edge_cases.py -v

# Level 2: Integration (15k tokens) - Daily
pytest backend/tests/test_token_tracker.py backend/tests/test_groq_client.py -v

# Level 3: E2E (40k tokens) - Weekly/Release
pytest backend/tests/test_e2e_pipeline.py -v
```

---

## 7. Token Monitoring & Alerts

### 7.1 Daily Token Budget Dashboard
```python
# Add to health check endpoint
@app.get("/health")
async def health_check():
    token_summary = get_token_tracker().get_usage_summary()
    return {
        "status": "healthy",
        "tokens": {
            "daily_total": token_summary["daily_total"],
            "remaining": token_summary["remaining"],
            "percent_used": token_summary["percent_used"],
        }
    }
```

### 7.2 Test Suite Token Guard
```python
# In conftest.py
@pytest.fixture(autouse=True)
def check_token_budget():
    """Skip tests if token budget is low."""
    tracker = get_token_tracker()
    if tracker.percent_used > 85:
        pytest.skip(f"Token budget low: {tracker.percent_used:.1f}% used")
```

### 7.3 Post-Test Report
```python
# Generate after test run
def generate_token_report():
    tracker = get_token_tracker()
    cache = get_cache()
    
    summary = tracker.get_usage_summary()
    cache_stats = cache.get_stats()
    savings = cache.estimate_savings()
    
    return {
        "date": datetime.utcnow().isoformat(),
        "tokens_used": summary["daily_total"],
        "tokens_remaining": summary["remaining"],
        "percent_used": summary["percent_used"],
        "cache_hit_rate": cache_stats["hit_rate_percent"],
        "tokens_saved_by_cache": savings["tokens_saved"],
        "by_model": summary.get("by_model", {}),
    }
```

---

## 8. Test Data & Fixtures

### 8.1 Golden Fixtures (No Tokens)
```python
# backend/tests/fixtures/golden.py
JAPAN_5D_REQUEST = "Plan a 5-day trip to Japan. Tokyo + Kyoto. $3,000 budget. Love food and temples, hate crowds."

JAPAN_5D_CONSTRAINTS = TravelConstraints(
    destination_region="Japan",
    cities=["Tokyo", "Kyoto"],
    duration_days=5,
    budget_total=3000,
    currency="USD",
    preferences=["food", "temples"],
    avoidances=["crowds"],
)
```

### 8.2 Test Request Variations (Low Token)
```python
# Variations for cache testing
TEST_REQUESTS = [
    "3 days in Paris, $2000, love art museums",
    "Week in Thailand, beach focused, $1500",
    "Japan 7 days: Tokyo, Kyoto, Osaka, $4000, foodies",
    "NYC weekend, $800, Broadway shows",
    "Iceland road trip 10 days, $5000, northern lights",
]
```

---

## 9. CI/CD Integration

### 9.1 GitHub Actions Workflow
```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Unit Tests (0 tokens)
        run: |
          pytest backend/tests/test_schemas.py 
                 backend/tests/test_edge_cases.py 
                 backend/tests/test_token_tracker.py -v
  
  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    if: github.event_name == 'schedule'  # Daily
    steps:
      - uses: actions/checkout@v3
      - name: Run Integration Tests (~15k tokens)
        env:
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
        run: pytest backend/tests/test_groq_client.py -v
  
  e2e-tests:
    runs-on: ubuntu-latest
    needs: integration-tests
    if: github.event_name == 'schedule' && github.event.schedule == '0 0 * * 0'  # Weekly
    steps:
      - uses: actions/checkout@v3
      - name: Run E2E Tests (~40k tokens)
        env:
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
        run: pytest backend/tests/test_e2e_pipeline.py -v
```

### 9.2 Token Budget Gates
```yaml
# Fail CI if token usage exceeds threshold
- name: Check Token Budget
  run: |
    python -c "
    from app.llm import get_token_tracker
    t = get_token_tracker()
    if t.percent_used > 90:
        print(f'ERROR: Token budget at {t.percent_used:.1f}%')
        exit(1)
    print(f'OK: Token budget at {t.percent_used:.1f}%')
    "
```

---

## 10. Manual Testing Guide

### 10.1 Quick Smoke Test (0 tokens)
```bash
# 1. Start backend
cd backend
uvicorn app.main:app --reload

# 2. Health check
curl http://localhost:8000/health
# Expected: {"status": "healthy", "tokens": {...}}

# 3. Stub plan (no LLM)
curl -X POST http://localhost:8000/api/plan \
  -H "Content-Type: application/json" \
  -d '{"request": "Test"}'
# Expected: Stub response with Japan fixture
```

### 10.2 LLM Integration Test (~3k tokens)
```bash
# Set API key
export GROQ_API_KEY=gsk_your_key_here

# Run single extraction test
python -c "
import asyncio
from app.llm import get_groq_client

async def test():
    client = get_groq_client()
    constraints = await client.extract_constraints(
        'Plan a 3-day trip to Paris. Love museums and cafes.'
    )
    print(f'Destination: {constraints.destination_region}')
    print(f'Cities: {constraints.cities}')
    print(f'Token usage: {client.get_token_summary()}')

asyncio.run(test())
"
```

---

## 11. Troubleshooting

### 11.1 Token Budget Exceeded
```
Error: TokenBudgetExceeded: requested 15000, remaining 5000, daily limit 100000
```
**Solutions:**
1. Wait for next UTC day (resets at midnight)
2. Use cached responses: `get_cache().clear()` then re-run
3. Switch to mock mode: `LLM_PROVIDER=mock` in .env
4. Reduce test scope: run only unit tests

### 11.2 Cache Not Working
**Symptoms:** Repeated prompts consume tokens  
**Check:**
```python
cache = get_cache()
print(f"Hit rate: {cache.get_stats()['hit_rate_percent']}%")
```
**Fix:** Ensure `enable_response_cache=true` in config

### 11.3 Rate Limiting (429 errors)
**Solution:** Add delays between requests:
```python
import asyncio
async def test_with_backoff():
    for i in range(5):
        try:
            result = await client.extract_constraints(request)
            break
        except RateLimitError:
            await asyncio.sleep(2 ** i)  # Exponential backoff
```

---

## 12. Summary

| Phase | Tests | Tokens | When to Run |
|-------|-------|--------|-------------|
| 0-1: Unit | 70+ | 0 | Every commit |
| 2-4: Integration | 10 | ~15k | Daily |
| 5-7: E2E | 5 | ~40k | Weekly |
| **Total Budget** | **85+** | **~100k** | **Daily Limit** |

### Key Principles
1. **Unit tests first** - Fast, free, reliable
2. **Cache aggressively** - Reuse LLM responses
3. **Track everything** - Know where tokens go
4. **Fail fast** - Stop tests if budget low
5. **Mock liberally** - Don't call LLM unless necessary

---

## Appendices

### A. Token Estimation Guide
```
System prompt: ~200 tokens
User prompt: length / 4 tokens
Expected response: length / 4 tokens
Safety margin: +500 tokens

Example:
- Prompt: 800 chars = 200 tokens
- Response: 1200 chars = 300 tokens
- System: 200 tokens
- Total: ~700 tokens
```

### B. Cost-Effective Models (Groq)
| Model | Context | Speed | Use Case |
|-------|---------|-------|----------|
| `mixtral-8x7b-32768` | 32k | Fast | Extraction, structure |
| `llama3-70b-8192` | 8k | Fast | Complex reasoning |
| `llama3-8b-8192` | 8k | Fastest | Simple tasks |
| `gemma-7b-it` | 8k | Fast | Testing, prototyping |

### C. Quick Reference Commands
```bash
# Run all unit tests (0 tokens)
pytest backend/tests/test_schemas.py backend/tests/test_edge_cases.py -v

# Run with token tracking
pytest backend/tests/test_groq_client.py -v --tb=short

# Check token usage
python -c "from app.llm import get_token_tracker; print(get_token_tracker().get_usage_summary())"

# Clear cache
python -c "from app.llm import get_cache; get_cache().clear()"

# Generate token report
python -c "from app.llm.token_tracker import generate_token_report; print(generate_token_report())"
```
