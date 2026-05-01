"""
Groq Integration Tests - Real LLM calls with token tracking.
**WARNING: These tests consume Groq tokens (~3k per test).**

Run only when:
- Token budget > 50% remaining
- Testing actual LLM integration
- Verifying production setup

To skip: pytest -m "not expensive"
"""

import pytest
import os

# Skip all tests if GROQ_API_KEY not set
pytestmark = [
    pytest.mark.expensive,
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.getenv("GROQ_API_KEY"),
        reason="GROQ_API_KEY not set"
    ),
]

from app.llm import get_groq_client, get_token_tracker
from app.models import TravelConstraints


class TestGroqConstraintExtraction:
    """
    Test real Groq LLM constraint extraction.
    **Consumes ~3,000 tokens per test.**
    """
    
    @pytest.fixture(autouse=True)
    def reset_tracker(self):
        """Reset tracker before each test to ensure clean state."""
        tracker = get_token_tracker()
        initial_usage = tracker._daily_total
        yield
        # Print usage after test
        final_usage = tracker._daily_total
        tokens_used = final_usage - initial_usage
        print(f"\n[TEST] Tokens used: {tokens_used}")
    
    @pytest.mark.asyncio
    async def test_extract_japan_constraints(self):
        """
        Extract constraints from Japan travel request.
        Expected tokens: ~2,500-3,500
        """
        client = get_groq_client()
        
        request = "Plan a 5-day trip to Japan. Tokyo + Kyoto. $3,000 budget. Love food and temples, hate crowds."
        
        constraints = await client.extract_constraints(request)
        
        # Validate extracted data
        assert constraints.destination_region.lower() == "japan"
        assert "tokyo" in [c.lower() for c in constraints.cities]
        assert "kyoto" in [c.lower() for c in constraints.cities]
        assert constraints.duration_days == 5
        assert constraints.budget_total == 3000
        assert "food" in [p.lower() for p in constraints.preferences] or "temples" in [p.lower() for p in constraints.preferences]
        
        # Verify token tracking
        summary = client.get_token_summary()
        assert summary["daily_total"] > 0
        print(f"\nToken usage: {summary}")
    
    @pytest.mark.asyncio
    async def test_extract_paris_constraints(self):
        """
        Extract constraints from Paris travel request.
        Expected tokens: ~2,500-3,500
        """
        client = get_groq_client()
        
        request = "3 days in Paris, $2000 budget, love art museums and cafes"
        
        constraints = await client.extract_constraints(request)
        
        # Validate
        assert "paris" in constraints.destination_region.lower() or any("paris" in c.lower() for c in constraints.cities)
        assert constraints.duration_days == 3
        assert constraints.budget_total == 2000
        
        print(f"\nExtracted: {constraints.destination_region}, {constraints.cities}")
    
    @pytest.mark.asyncio
    async def test_caching_reduces_tokens(self):
        """
        Verify that caching prevents duplicate token usage.
        First call: ~3k tokens
        Second call: 0 tokens (cached)
        """
        from app.llm import get_cache
        
        client = get_groq_client()
        cache = get_cache()
        cache.clear()
        
        request = "Weekend in NYC, $800, love Broadway shows"
        
        # First call - should use tokens
        tracker = get_token_tracker()
        tokens_before = tracker._daily_total
        
        result1 = await client.extract_constraints(request)
        tokens_after_first = tracker._daily_total
        first_call_tokens = tokens_after_first - tokens_before
        
        # Second call - should be cached (0 new tokens)
        result2 = await client.extract_constraints(request)
        tokens_after_second = tracker._daily_total
        second_call_tokens = tokens_after_second - tokens_after_first
        
        # Verify
        assert first_call_tokens > 0, "First call should consume tokens"
        assert second_call_tokens == 0, "Second call should use cache (0 tokens)"
        
        # Cache stats
        stats = cache.get_stats()
        assert stats["hits"] >= 1, "Cache should have at least 1 hit"
        
        print(f"\nFirst call: {first_call_tokens} tokens")
        print(f"Second call: {second_call_tokens} tokens (cached)")
        print(f"Cache hit rate: {stats['hit_rate_percent']}%")
    
    def test_token_budget_tracking(self):
        """
        Verify token tracker accurately counts usage.
        """
        tracker = get_token_tracker()
        initial_total = tracker._daily_total
        
        # Simulate some usage
        tracker.record_usage(prompt_tokens=1000, completion_tokens=500, model="mixtral")
        tracker.record_usage(prompt_tokens=2000, completion_tokens=1000, model="llama3")
        
        # Check summary
        summary = tracker.get_usage_summary()
        assert summary["daily_total"] == initial_total + 4500
        assert summary["request_count"] >= 2
        
        print(f"\nToken summary: {summary}")


class TestGroqClientConfiguration:
    """Test Groq client configuration without making API calls."""
    
    def test_client_uses_configured_model(self):
        """Client should use model from settings."""
        from app.config import get_settings
        
        settings = get_settings()
        client = get_groq_client()
        
        assert client.model == settings.groq_model
    
    def test_client_uses_configured_temperature(self):
        """Client should use temperature from settings."""
        from app.config import get_settings
        
        settings = get_settings()
        client = get_groq_client()
        
        assert client.temperature == settings.groq_temperature
    
    def test_token_tracker_enabled_by_default(self):
        """Token tracking should be enabled."""
        client = get_groq_client()
        
        assert client.enable_tracking is True
        assert client._tracker is not None
    
    def test_cache_enabled_by_default(self):
        """Caching should be enabled by default."""
        client = get_groq_client()
        
        assert client.enable_cache is True


class TestTokenBudgetProtection:
    """Test token budget protection mechanisms."""
    
    def test_can_make_request_allows_reasonable_request(self):
        """Should allow request that fits in budget."""
        from app.llm.token_tracker import TokenBudgetExceeded
        
        tracker = get_token_tracker()
        
        # Should allow 10k token request
        assert tracker.can_make_request(10000) is True
    
    def test_budget_exceeded_error_includes_details(self):
        """Budget exceeded error should be informative."""
        from app.llm.token_tracker import TokenBudgetExceeded
        
        exc = TokenBudgetExceeded(
            requested=15000,
            remaining=5000,
            limit=100000
        )
        
        assert "15000" in str(exc)
        assert "5000" in str(exc)
        assert "100000" in str(exc)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
