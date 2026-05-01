"""
Pytest configuration and fixtures for Groq-aware testing.
Provides token budget protection and shared fixtures.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock

# Skip markers for different test levels
unit_test = pytest.mark.unit
integration_test = pytest.mark.integration
e2e_test = pytest.mark.e2e
expensive_test = pytest.mark.expensive  # Uses real LLM tokens


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests (no LLM calls)")
    config.addinivalue_line("markers", "integration: Integration tests (may use LLM)")
    config.addinivalue_line("markers", "e2e: End-to-end tests (use LLM)")
    config.addinivalue_line("markers", "expensive: Tests that consume significant tokens")


@pytest.fixture(autouse=True)
def check_token_budget(request):
    """
    Automatically skip expensive tests if token budget is low.
    Only applies to tests marked with 'expensive' or 'e2e'.
    """
    if not any(marker in request.keywords for marker in ["expensive", "e2e"]):
        return
    
    # Check token budget before expensive tests
    try:
        from app.llm import get_token_tracker
        tracker = get_token_tracker()
        
        if tracker.percent_used > 85:
            pytest.skip(
                f"Token budget low: {tracker.percent_used:.1f}% used. "
                f"Remaining: {tracker.remaining_tokens}. "
                f"Wait until UTC midnight or run unit tests only."
            )
    except ImportError:
        pass  # Token tracker not available, skip check


@pytest.fixture
def mock_groq_client():
    """Mock Groq client for unit tests (0 tokens)."""
    client = MagicMock()
    
    # Mock extract_constraints to return predictable result
    from app.models import TravelConstraints
    
    async def mock_extract(request: str) -> TravelConstraints:
        return TravelConstraints(
            destination_region="Japan",
            cities=["Tokyo", "Kyoto"],
            duration_days=5,
            budget_total=3000,
            currency="USD",
            preferences=["food", "temples"],
            avoidances=["crowds"],
        )
    
    client.extract_constraints = AsyncMock(side_effect=mock_extract)
    client.get_token_summary = MagicMock(return_value={
        "daily_total": 0,
        "remaining": 80000,
        "percent_used": 0.0,
    })
    
    return client


@pytest.fixture
def mock_token_tracker():
    """Mock token tracker for isolated testing."""
    tracker = MagicMock()
    tracker.DAILY_LIMIT = 100000
    tracker.effective_limit = 80000
    tracker.remaining_tokens = 75000
    tracker.percent_used = 12.5
    tracker.can_make_request = MagicMock(return_value=True)
    tracker.get_usage_summary = MagicMock(return_value={
        "daily_total": 12500,
        "remaining": 75000,
        "percent_used": 12.5,
        "daily_limit": 100000,
        "effective_limit": 80000,
        "request_count": 5,
    })
    return tracker


@pytest.fixture
def mock_response_cache():
    """Mock response cache for testing."""
    cache = MagicMock()
    cache.get = MagicMock(return_value=None)  # Default: cache miss
    cache.set = MagicMock()
    cache.get_stats = MagicMock(return_value={
        "entries": 0,
        "hits": 0,
        "misses": 10,
        "hit_rate_percent": 0.0,
    })
    return cache


@pytest.fixture
def japan_request():
    """Standard Japan test request."""
    return "Plan a 5-day trip to Japan. Tokyo + Kyoto. $3,000 budget. Love food and temples, hate crowds."


@pytest.fixture
def europe_request():
    """Europe multi-city test request."""
    return "10 days in Europe. Paris, Rome, Barcelona. $5000 budget. Love art and architecture."


@pytest.fixture(autouse=True)
def clear_cache_between_tests():
    """Clear LLM response cache between tests to ensure isolation."""
    yield
    
    try:
        from app.llm import get_cache
        cache = get_cache()
        if hasattr(cache, '_cache'):
            cache._cache.clear()
    except (ImportError, AttributeError):
        pass


@pytest.fixture(scope="session")
def token_report():
    """
    Generate token usage report after test session.
    Usage: pytest --token-report
    """
    yield
    
    # After all tests, print token summary
    try:
        from app.llm import get_token_tracker, get_cache
        
        tracker = get_token_tracker()
        summary = tracker.get_usage_summary()
        
        cache = get_cache()
        cache_stats = cache.get_stats()
        
        print("\n" + "="*60)
        print("TOKEN USAGE REPORT")
        print("="*60)
        print(f"Daily Total: {summary['daily_total']:,} tokens")
        print(f"Remaining:   {summary['remaining']:,} tokens")
        print(f"Used:        {summary['percent_used']:.1f}%")
        print(f"Cache Hit Rate: {cache_stats['hit_rate_percent']:.1f}%")
        print("="*60)
    except Exception as e:
        print(f"\nCould not generate token report: {e}")


# Configure pytest to show token usage in verbose mode
def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Add token usage summary to terminal output."""
    try:
        from app.llm import get_token_tracker, get_cache
        
        tracker = get_token_tracker()
        summary = tracker.get_usage_summary()
        
        cache = get_cache()
        stats = cache.get_stats()
        
        terminalreporter.write_sep("=", "Token Usage Summary")
        terminalreporter.write_line(f"Tokens Used: {summary['daily_total']:,} / {summary['daily_limit']:,}")
        terminalreporter.write_line(f"Percent Used: {summary['percent_used']:.1f}%")
        terminalreporter.write_line(f"Cache Hit Rate: {stats['hit_rate_percent']:.1f}%")
        terminalreporter.write_line(f"Requests Made: {summary['request_count']}")
        
        if summary['percent_used'] > 80:
            terminalreporter.write_line(
                f"WARNING: Token budget at {summary['percent_used']:.1f}%!",
                yellow=True,
                bold=True,
            )
    except Exception:
        pass  # Don't fail tests if reporting fails
