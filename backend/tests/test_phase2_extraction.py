"""
Phase 2 Tests - Constraint Extraction with Groq LLM.
Real LLM calls with ~2,500-4,000 tokens per test.

Run with: GROQ_API_KEY=gsk_... pytest tests/test_phase2_extraction.py -v
Skip with: pytest -m "not expensive"
"""

import pytest
import os

pytestmark = [
    pytest.mark.expensive,
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.getenv("GROQ_API_KEY"),
        reason="GROQ_API_KEY not set - Phase 2 tests require LLM"
    ),
]

from app.agents import OrchestratorAgent
from app.llm import get_groq_client, get_token_tracker
from app.models import TravelConstraints


class TestPhase2ConstraintExtraction:
    """
    Phase 2: LLM constraint extraction tests.
    **Consumes ~2,500-4,000 tokens per test.**
    """
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator with Groq client."""
        client = get_groq_client()
        return OrchestratorAgent(llm_client=client)
    
    @pytest.mark.asyncio
    async def test_extract_japan_5day_trip(self, orchestrator):
        """
        Extract constraints from Japan 5-day trip request.
        Expected tokens: ~3,000
        """
        request = (
            "Plan a 5-day trip to Japan. "
            "Tokyo + Kyoto. "
            "$3,000 budget. "
            "Love food and temples, hate crowds."
        )
        
        constraints = await orchestrator.extract_constraints(request)
        
        # Validate structure
        assert isinstance(constraints, TravelConstraints)
        assert constraints.destination_region.lower() == "japan"
        
        # Should extract both cities
        cities_lower = [c.lower() for c in constraints.cities]
        assert "tokyo" in cities_lower
        assert "kyoto" in cities_lower
        
        # Duration and budget
        assert constraints.duration_days == 5
        assert constraints.budget_total == 3000
        assert constraints.currency == "USD"
        
        # Preferences and avoidances
        prefs_lower = [p.lower() for p in constraints.preferences]
        assert any(word in prefs_lower for word in ["food", "temple", "temples"])
        
        avoids_lower = [a.lower() for a in constraints.avoidances]
        assert any(word in avoids_lower for word in ["crowd", "crowds"])
        
        print(f"\n✓ Extracted: {constraints.destination_region}, {constraints.cities}, ${constraints.budget_total}")
    
    @pytest.mark.asyncio
    async def test_extract_paris_weekend(self, orchestrator):
        """
        Extract constraints from Paris weekend request.
        Expected tokens: ~2,800
        """
        request = "Weekend in Paris, $800 budget, love art museums and cafes"
        
        constraints = await orchestrator.extract_constraints(request)
        
        assert "paris" in constraints.destination_region.lower() or any("paris" in c.lower() for c in constraints.cities)
        assert constraints.duration_days in [2, 3]  # Weekend
        assert constraints.budget_total == 800
        
        prefs_lower = [p.lower() for p in constraints.preferences]
        assert any(word in prefs_lower for word in ["art", "museum", "museums", "cafe", "cafes"])
        
        print(f"\n✓ Extracted: {constraints.destination_region}, {constraints.duration_days} days")
    
    @pytest.mark.asyncio
    async def test_extract_thailand_beach(self, orchestrator):
        """
        Extract beach-focused Thailand request.
        Expected tokens: ~3,200
        """
        request = "7 days in Thailand, $2000, beach vacation, love snorkeling and seafood, avoid parties"
        
        constraints = await orchestrator.extract_constraints(request)
        
        assert "thailand" in constraints.destination_region.lower()
        assert constraints.duration_days == 7
        assert constraints.budget_total == 2000
        
        prefs_lower = [p.lower() for p in constraints.preferences]
        assert any(word in prefs_lower for word in ["beach", "snorkel", "seafood"])
        
        avoids_lower = [a.lower() for a in constraints.avoidances]
        assert any(word in avoids_lower for word in ["party", "parties"])
        
        print(f"\n✓ Extracted: {constraints.destination_region}, beach focus")
    
    @pytest.mark.asyncio
    async def test_extract_europe_multi_city(self, orchestrator):
        """
        Extract multi-city Europe request.
        Expected tokens: ~3,500
        """
        request = "10 days in Europe visiting Paris, Rome, and Barcelona. $4000 budget. Love architecture and history."
        
        constraints = await orchestrator.extract_constraints(request)
        
        assert "europe" in constraints.destination_region.lower()
        assert constraints.duration_days == 10
        assert constraints.budget_total == 4000
        
        # Should extract multiple cities
        assert len(constraints.cities) >= 2
        cities_lower = [c.lower() for c in constraints.cities]
        assert any(city in cities_lower for city in ["paris", "rome", "barcelona"])
        
        print(f"\n✓ Extracted: {constraints.destination_region}, cities: {constraints.cities}")
    
    @pytest.mark.asyncio
    async def test_token_usage_tracked(self, orchestrator):
        """
        Verify token usage is tracked for extractions.
        """
        tracker = get_token_tracker()
        tokens_before = tracker._daily_total
        
        request = "3 days in NYC, $1000, love Broadway shows"
        await orchestrator.extract_constraints(request)
        
        tokens_after = tracker._daily_total
        tokens_used = tokens_after - tokens_before
        
        # Should have used some tokens (typically 2,000-4,000)
        assert tokens_used > 0
        print(f"\n✓ Tokens used for extraction: {tokens_used}")
        
        # Verify summary includes this request
        summary = tracker.get_usage_summary()
        assert summary["request_count"] >= 1
        print(f"Total daily usage: {summary['daily_total']} / {summary['daily_limit']}")
    
    def test_orchestrator_without_llm_raises_error(self):
        """
        Orchestrator without LLM should raise clear error.
        """
        orchestrator = OrchestratorAgent(llm_client=None)
        
        with pytest.raises(RuntimeError) as exc_info:
            import asyncio
            asyncio.run(orchestrator.extract_constraints("Test request"))
        
        assert "LLM client not available" in str(exc_info.value)


class TestPhase2FallbackToStub:
    """Test fallback behavior when LLM is not available."""
    
    @pytest.mark.asyncio
    async def test_api_uses_stub_when_no_groq_key(self, client):
        """
        API should return stub response when GROQ_API_KEY not set.
        """
        import os
        
        # Temporarily unset API key
        original_key = os.environ.get("GROQ_API_KEY")
        if original_key:
            del os.environ["GROQ_API_KEY"]
        
        try:
            from httpx import AsyncClient
            
            async with AsyncClient(app=app, base_url="http://test") as ac:
                response = await ac.post("/api/plan", json={
                    "request": "Plan a trip to Japan"
                })
                
                assert response.status_code == 200
                data = response.json()
                
                # Should be stub response
                assert data["used_stub_mode"] is True
                assert "stub" in data["final_itinerary"]["disclaimer"].lower()
        finally:
            # Restore API key
            if original_key:
                os.environ["GROQ_API_KEY"] = original_key


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
