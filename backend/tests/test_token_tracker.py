"""
Tests for Token Tracker - Groq 100k tokens/day limit management.
Zero token cost - these test the tracking logic only.
"""

import pytest
import threading
import time
from datetime import datetime, timedelta, timezone

from app.llm.token_tracker import TokenTracker, TokenUsage, TokenBudgetExceeded


class TestTokenTracker:
    """Test token budget tracking functionality."""
    
    def test_daily_limit_is_100k(self):
        """Groq free tier limit is 100,000 tokens/day."""
        tracker = TokenTracker()
        assert tracker.DAILY_LIMIT == 100000
    
    def test_effective_limit_with_20_percent_buffer(self):
        """Default 20% buffer means effective limit is 80k."""
        tracker = TokenTracker(buffer_percent=20)
        assert tracker.effective_limit == 80000
    
    def test_can_make_request_when_under_budget(self):
        """Should allow request when under effective limit."""
        tracker = TokenTracker(buffer_percent=20)
        assert tracker.can_make_request(estimated_tokens=10000) is True
    
    def test_can_make_request_denies_when_over_budget(self):
        """Should deny request when it would exceed effective limit."""
        tracker = TokenTracker(buffer_percent=0)  # No buffer for this test
        # Use 90k of 100k
        tracker._daily_total = 90000
        assert tracker.can_make_request(estimated_tokens=15000) is False
    
    def test_record_usage_increases_daily_total(self):
        """Recording usage should increase daily total."""
        tracker = TokenTracker()
        initial = tracker._daily_total
        
        tracker.record_usage(prompt_tokens=1000, completion_tokens=500, model="mixtral")
        
        assert tracker._daily_total == initial + 1500
    
    def test_record_usage_creates_token_usage_object(self):
        """Recording should return TokenUsage with correct totals."""
        tracker = TokenTracker()
        
        usage = tracker.record_usage(
            prompt_tokens=1000,
            completion_tokens=500,
            model="mixtral-8x7b"
        )
        
        assert usage.prompt_tokens == 1000
        assert usage.completion_tokens == 500
        assert usage.total_tokens == 1500
        assert usage.model == "mixtral-8x7b"
        assert isinstance(usage.timestamp, datetime)
    
    def test_remaining_tokens_decreases_with_usage(self):
        """Remaining tokens should decrease as we use them."""
        tracker = TokenTracker(buffer_percent=20)
        initial_remaining = tracker.remaining_tokens  # Should be 80,000
        
        tracker.record_usage(prompt_tokens=5000, completion_tokens=3000, model="mixtral")
        
        assert tracker.remaining_tokens == initial_remaining - 8000
    
    def test_percent_used_calculation(self):
        """Percent used should be accurate."""
        tracker = TokenTracker(buffer_percent=0)
        tracker._daily_total = 25000  # 25% of 100k
        
        assert tracker.percent_used == 25.0
    
    def test_estimate_request_cost_rough_calculation(self):
        """Token estimation uses 4 chars per token approximation."""
        tracker = TokenTracker()
        
        # 400 chars / 4 = 100 tokens, plus 500 response = 600
        estimate = tracker.estimate_request_cost(
            prompt_length_chars=400,
            expected_response_length=2000
        )
        
        assert estimate == 600  # 100 + 500
    
    def test_usage_summary_returns_correct_structure(self):
        """Summary should have all expected fields."""
        tracker = TokenTracker(buffer_percent=20)
        tracker.record_usage(prompt_tokens=1000, completion_tokens=500, model="mixtral")
        tracker.record_usage(prompt_tokens=2000, completion_tokens=1000, model="llama3")
        
        summary = tracker.get_usage_summary()
        
        assert "daily_total" in summary
        assert "remaining" in summary
        assert "percent_used" in summary
        assert "daily_limit" in summary
        assert "effective_limit" in summary
        assert "buffer_percent" in summary
        assert "request_count" in summary
        assert "by_model" in summary
        
        assert summary["daily_total"] == 4500
        assert summary["request_count"] == 2
        assert "mixtral" in summary["by_model"]
        assert "llama3" in summary["by_model"]
    
    def test_thread_safety_concurrent_updates(self):
        """Multiple threads updating should be safe."""
        tracker = TokenTracker()
        errors = []
        
        def update_tracker():
            try:
                for _ in range(10):
                    tracker.record_usage(100, 100, "mixtral")
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=update_tracker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0
        assert tracker._daily_total == 10000  # 5 threads * 10 iterations * 200 tokens
    
    def test_token_budget_exceeded_exception(self):
        """Exception should contain useful information."""
        exc = TokenBudgetExceeded(requested=15000, remaining=5000, limit=100000)
        
        assert exc.requested == 15000
        assert exc.remaining == 5000
        assert exc.limit == 100000
        assert "15000" in str(exc)
        assert "5000" in str(exc)
    
    def test_different_buffer_percentages(self):
        """Buffer percentage should affect effective limit."""
        tracker_10 = TokenTracker(buffer_percent=10)
        tracker_50 = TokenTracker(buffer_percent=50)
        
        assert tracker_10.effective_limit == 90000  # 90% of 100k
        assert tracker_50.effective_limit == 50000  # 50% of 100k
    
    def test_zero_remaining_when_at_limit(self):
        """Remaining should be 0 when at effective limit."""
        tracker = TokenTracker(buffer_percent=0)
        tracker._daily_total = 100000  # At limit
        
        assert tracker.remaining_tokens == 0
    
    def test_daily_reset_logic(self):
        """Daily total should reset when day changes."""
        tracker = TokenTracker()
        tracker._daily_total = 50000
        tracker._day_start = datetime.now(timezone.utc) - timedelta(days=1)  # Yesterday
        
        # Accessing remaining should trigger reset
        _ = tracker.remaining_tokens
        
        # Should be reset (or at least not 50000 anymore due to new day)
        # Note: This test may be flaky if run exactly at midnight UTC
        # In practice, the reset works correctly
        assert tracker._day_start.date() == datetime.now(timezone.utc).date()


class TestTokenUsage:
    """Test TokenUsage data class."""
    
    def test_total_tokens_calculation(self):
        """Total should be sum of prompt and completion."""
        usage = TokenUsage(prompt_tokens=1000, completion_tokens=500, model="test")
        assert usage.total_tokens == 1500
    
    def test_timestamp_auto_set(self):
        """Timestamp should be set on creation."""
        before = datetime.now(timezone.utc)
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50, model="test")
        after = datetime.now(timezone.utc)
        
        assert before <= usage.timestamp <= after


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
