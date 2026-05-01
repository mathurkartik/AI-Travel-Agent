"""
Tests for ToolRouter - Phase 3 implementation.
Zero LLM tokens - tests stub implementations with static data.
"""

import pytest
import pytest_asyncio
from app.tools import ToolRouter


class TestToolRouter:
    """Test ToolRouter with static stub data."""
    
    @pytest.fixture
    def router(self):
        """Create a fresh ToolRouter for each test."""
        return ToolRouter()
    
    @pytest.mark.asyncio
    async def test_search_returns_static_results(self, router):
        """Search returns mock results for known queries."""
        results = await router.search("temples in Kyoto")
        
        assert len(results) == 3
        assert results[0]["title"] == "Kinkaku-ji (Golden Pavilion)"
        assert "temple" in results[0]["snippet"].lower()
    
    @pytest.mark.asyncio
    async def test_search_returns_empty_for_unknown(self, router):
        """Search returns empty list for unknown queries."""
        results = await router.search("something random xyz123")
        
        assert results == []
    
    @pytest.mark.asyncio
    async def test_search_caches_results(self, router):
        """Same query should use cache."""
        # First call
        results1 = await router.search("food in Tokyo")
        
        # Second call should be cached
        results2 = await router.search("food in Tokyo")
        
        assert results1 == results2
        cache_stats = router.get_cache_stats()
        assert cache_stats["entries"] == 1
    
    @pytest.mark.asyncio
    async def test_geo_estimate_tokyo_kyoto(self, router):
        """Geo estimate for Tokyo-Kyoto route."""
        result = await router.geo_estimate("Tokyo", "Kyoto")
        
        assert result["distance_km"] == 513
        assert result["duration_minutes"] == 135
        assert result["mode"] == "shinkansen"
        assert result["estimated_cost_usd"] == 100
    
    @pytest.mark.asyncio
    async def test_geo_estimate_kyoto_osaka(self, router):
        """Geo estimate for Kyoto-Osaka route."""
        result = await router.geo_estimate("Kyoto", "Osaka")
        
        assert result["distance_km"] == 56
        assert result["duration_minutes"] == 15
        assert result["mode"] == "local_train"
    
    @pytest.mark.asyncio
    async def test_price_band_japan_hotel(self, router):
        """Price band for Japan hotel."""
        result = await router.price_band("hotel", "Tokyo", "moderate")
        
        assert result["estimate_usd"] == 120
        assert "3-star" in result["notes"]
        assert result["currency"] == "USD"
    
    @pytest.mark.asyncio
    async def test_price_band_japan_food(self, router):
        """Price band for Japan food."""
        result = await router.price_band("food", "Kyoto", "budget")
        
        assert result["estimate_usd"] == 15
        assert "convenience" in result["notes"].lower()
    
    @pytest.mark.asyncio
    async def test_price_band_europe(self, router):
        """Price band for European cities."""
        result = await router.price_band("hotel", "Paris", "luxury")
        
        assert result["estimate_usd"] == 600
        assert "5-star" in result["notes"]
    
    @pytest.mark.asyncio
    async def test_fx_convert_jpy_to_usd(self, router):
        """Currency conversion JPY to USD."""
        result = await router.fx_convert(10000, "JPY", "USD")
        
        assert result["original_amount"] == 10000
        assert result["original_currency"] == "JPY"
        assert result["target_currency"] == "USD"
        assert result["converted_amount"] == pytest.approx(67.0, rel=0.1)
        assert result["rate"] == pytest.approx(0.0067, rel=0.01)
    
    @pytest.mark.asyncio
    async def test_fx_convert_same_currency(self, router):
        """Currency conversion same currency returns same amount."""
        result = await router.fx_convert(100, "USD", "USD")
        
        assert result["converted_amount"] == 100
        assert result["rate"] == 1.0
    
    @pytest.mark.asyncio
    async def test_fx_convert_cross_currency(self, router):
        """Currency conversion JPY to EUR."""
        result = await router.fx_convert(10000, "JPY", "EUR")
        
        assert result["original_currency"] == "JPY"
        assert result["target_currency"] == "EUR"
        assert result["converted_amount"] > 0
    
    @pytest.mark.asyncio
    async def test_trace_id_propagation(self, router):
        """Trace ID is logged with each call."""
        await router.search("test", trace_id="test-trace-123")
        await router.geo_estimate("A", "B", trace_id="test-trace-123")
        
        log = router.get_call_log()
        assert len(log) == 2
        assert log[0]["trace_id"] == "test-trace-123"
        assert log[1]["trace_id"] == "test-trace-123"
    
    def test_clear_cache(self, router):
        """Cache can be cleared."""
        # Add something to cache by calling search
        # Then clear
        router.clear_cache()
        
        stats = router.get_cache_stats()
        assert stats["entries"] == 0
    
    def test_clear_log(self, router):
        """Call log can be cleared."""
        router.clear_log()
        
        log = router.get_call_log()
        assert len(log) == 0


class TestToolRouterTimeout:
    """Test timeout handling in ToolRouter."""
    
    @pytest.mark.asyncio
    async def test_search_with_timeout(self):
        """Search accepts timeout parameter."""
        router = ToolRouter()
        
        # Should not raise with valid timeout
        result = await router.search("temples Kyoto", timeout=5)
        assert isinstance(result, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
