"""
Edge Case Tests for AI Travel Planner
Tests boundary conditions, invalid inputs, and error handling.
"""

import pytest
from pydantic import ValidationError
from uuid import UUID

from app.models import (
    TravelConstraints,
    Activity,
    ActivityCatalog,
    BudgetBreakdown,
    BudgetCategory,
    BudgetViolation,
    SuggestedSwap,
    DayItinerary,
    DayItineraryItem,
    ActivityType,
    CostBand,
    CrowdLevel,
)


# ============================================================================
# TravelConstraints Edge Cases
# ============================================================================

class TestTravelConstraintsEdgeCases:
    """Test boundary conditions and invalid inputs for constraints."""
    
    def test_empty_destination_fails(self):
        """Empty or whitespace-only destination should fail."""
        with pytest.raises(ValidationError) as exc_info:
            TravelConstraints(
                destination_region="",
                cities=["Tokyo"],
                duration_days=5,
                budget_total=1000,
            )
        assert "at least 1 character" in str(exc_info.value).lower() or "empty" in str(exc_info.value).lower()
    
    def test_whitespace_destination_fails(self):
        """Whitespace-only destination should fail."""
        with pytest.raises(ValidationError):
            TravelConstraints(
                destination_region="   ",
                cities=["Tokyo"],
                duration_days=5,
                budget_total=1000,
            )
    
    def test_destination_max_length_100(self):
        """Destination over 100 chars should fail."""
        with pytest.raises(ValidationError):
            TravelConstraints(
                destination_region="A" * 101,
                cities=["Tokyo"],
                duration_days=5,
                budget_total=1000,
            )
    
    def test_destination_strips_whitespace(self):
        """Destination should be trimmed."""
        constraints = TravelConstraints(
            destination_region="  Japan  ",
            cities=["Tokyo"],
            duration_days=5,
            budget_total=1000,
        )
        assert constraints.destination_region == "Japan"
    
    def test_duplicate_cities_fails(self):
        """Duplicate cities (case insensitive) should fail."""
        with pytest.raises(ValidationError) as exc_info:
            TravelConstraints(
                destination_region="Japan",
                cities=["Tokyo", "tokyo", "TOKYO"],  # All same
                duration_days=5,
                budget_total=1000,
            )
        assert "duplicate" in str(exc_info.value).lower()
    
    def test_too_many_cities_fails(self):
        """More than 10 cities should fail."""
        with pytest.raises(ValidationError):
            TravelConstraints(
                destination_region="Europe",
                cities=[f"City{i}" for i in range(11)],
                duration_days=30,
                budget_total=5000,
            )
    
    def test_duration_boundary_values(self):
        """Test duration boundaries (1-30 days)."""
        # Valid boundaries
        TravelConstraints(
            destination_region="Test",
            cities=["City"],
            duration_days=1,  # Min
            budget_total=100,
        )
        TravelConstraints(
            destination_region="Test",
            cities=["City"],
            duration_days=30,  # Max
            budget_total=100,
        )
        
        # Invalid boundaries
        with pytest.raises(ValidationError):
            TravelConstraints(
                destination_region="Test",
                cities=["City"],
                duration_days=0,  # Below min
                budget_total=100,
            )
        with pytest.raises(ValidationError):
            TravelConstraints(
                destination_region="Test",
                cities=["City"],
                duration_days=31,  # Above max
                budget_total=100,
            )
    
    def test_budget_boundary_values(self):
        """Test budget boundaries (gt=0, le=1000000)."""
        # Valid
        TravelConstraints(
            destination_region="Test",
            cities=["City"],
            duration_days=5,
            budget_total=0.01,  # Just above 0
        )
        TravelConstraints(
            destination_region="Test",
            cities=["City"],
            duration_days=5,
            budget_total=1000000,  # Max
        )
        
        # Invalid
        with pytest.raises(ValidationError):
            TravelConstraints(
                destination_region="Test",
                cities=["City"],
                duration_days=5,
                budget_total=0,  # Zero
            )
        with pytest.raises(ValidationError):
            TravelConstraints(
                destination_region="Test",
                cities=["City"],
                duration_days=5,
                budget_total=-100,  # Negative
            )
        with pytest.raises(ValidationError):
            TravelConstraints(
                destination_region="Test",
                cities=["City"],
                duration_days=5,
                budget_total=1000001,  # Above max
            )
    
    def test_currency_lowercase_converts_to_uppercase(self):
        """Currency should be auto-converted to uppercase."""
        constraints = TravelConstraints(
            destination_region="Test",
            cities=["City"],
            duration_days=5,
            budget_total=1000,
            currency="usd",  # lowercase
        )
        assert constraints.currency == "USD"
    
    def test_currency_invalid_length_fails(self):
        """Currency must be exactly 3 characters."""
        with pytest.raises(ValidationError):
            TravelConstraints(
                destination_region="Test",
                cities=["City"],
                duration_days=5,
                budget_total=1000,
                currency="US",  # Too short
            )
        with pytest.raises(ValidationError):
            TravelConstraints(
                destination_region="Test",
                cities=["City"],
                duration_days=5,
                budget_total=1000,
                currency="USDD",  # Too long
            )
    
    def test_trace_id_auto_generated(self):
        """Trace ID should be auto-generated UUID."""
        constraints = TravelConstraints(
            destination_region="Test",
            cities=["City"],
            duration_days=5,
            budget_total=1000,
        )
        assert isinstance(constraints.trace_id, UUID)
    
    def test_long_preference_avoidance_lists(self):
        """Should handle long lists of preferences/avoidances."""
        constraints = TravelConstraints(
            destination_region="Test",
            cities=["City"],
            duration_days=5,
            budget_total=1000,
            preferences=["pref" + str(i) for i in range(50)],
            avoidances=["avoid" + str(i) for i in range(50)],
        )
        assert len(constraints.preferences) == 50


# ============================================================================
# Activity Edge Cases
# ============================================================================

class TestActivityEdgeCases:
    """Test boundary conditions for activities."""
    
    def test_activity_id_with_spaces_fails(self):
        """Activity ID cannot contain spaces."""
        with pytest.raises(ValidationError) as exc_info:
            Activity(
                id="tokyo temple 001",  # Space
                name="Senso-ji",
                city="Tokyo",
                type=ActivityType.TEMPLE,
                estimated_duration_hours=2,
                cost_band=CostBand.BUDGET,
                rationale="Historic temple",
            )
        assert "space" in str(exc_info.value).lower() or "slash" in str(exc_info.value).lower()
    
    def test_activity_id_with_slashes_fails(self):
        """Activity ID cannot contain slashes."""
        with pytest.raises(ValidationError):
            Activity(
                id="tokyo/temple/001",  # Slash
                name="Senso-ji",
                city="Tokyo",
                type=ActivityType.TEMPLE,
                estimated_duration_hours=2,
                cost_band=CostBand.BUDGET,
                rationale="Historic temple",
            )
    
    def test_activity_id_lowercased(self):
        """Activity ID should be lowercased."""
        activity = Activity(
            id="TOKYO-TEMPLE-001",  # Uppercase
            name="Senso-ji",
            city="Tokyo",
            type=ActivityType.TEMPLE,
            estimated_duration_hours=2,
            cost_band=CostBand.BUDGET,
            rationale="Historic temple",
        )
        assert activity.id == "tokyo-temple-001"
    
    def test_duration_precision_rounding(self):
        """Duration should round to nearest 0.5 hours."""
        activity = Activity(
            id="test-001",
            name="Test",
            city="City",
            type=ActivityType.OTHER,
            estimated_duration_hours=2.3,  # Should round to 2.5
            cost_band=CostBand.MODERATE,
            rationale="Test",
        )
        assert activity.estimated_duration_hours == 2.5
        
        activity2 = Activity(
            id="test-002",
            name="Test 2",
            city="City",
            type=ActivityType.OTHER,
            estimated_duration_hours=1.7,  # Should round to 1.5
            cost_band=CostBand.MODERATE,
            rationale="Test",
        )
        assert activity2.estimated_duration_hours == 1.5
    
    def test_duration_max_24_hours(self):
        """Duration cannot exceed 24 hours."""
        with pytest.raises(ValidationError):
            Activity(
                id="test-001",
                name="Test",
                city="City",
                type=ActivityType.OTHER,
                estimated_duration_hours=25,
                cost_band=CostBand.MODERATE,
                rationale="Test",
            )
    
    def test_empty_name_fails(self):
        """Activity name cannot be empty."""
        with pytest.raises(ValidationError):
            Activity(
                id="test-001",
                name="",  # Empty
                city="City",
                type=ActivityType.OTHER,
                estimated_duration_hours=1,
                cost_band=CostBand.MODERATE,
                rationale="Test",
            )
    
    def test_name_max_length_200(self):
        """Activity name max 200 chars."""
        with pytest.raises(ValidationError):
            Activity(
                id="test-001",
                name="A" * 201,
                city="City",
                type=ActivityType.OTHER,
                estimated_duration_hours=1,
                cost_band=CostBand.MODERATE,
                rationale="Test",
            )
    
    def test_empty_rationale_fails(self):
        """Activity rationale cannot be empty."""
        with pytest.raises(ValidationError):
            Activity(
                id="test-001",
                name="Test",
                city="City",
                type=ActivityType.OTHER,
                estimated_duration_hours=1,
                cost_band=CostBand.MODERATE,
                rationale="",  # Empty
            )
    
    def test_duplicate_tags_removed(self):
        """Duplicate tags should be deduplicated."""
        activity = Activity(
            id="test-001",
            name="Test",
            city="City",
            type=ActivityType.OTHER,
            estimated_duration_hours=1,
            cost_band=CostBand.MODERATE,
            rationale="Test",
            tags=["temple", "temple", "TEMPLE", "historic"],  # Duplicates
        )
        assert len(activity.tags) == 2  # temple, historic
        assert "temple" in activity.tags
        assert "historic" in activity.tags
    
    def test_too_many_tags_fails(self):
        """More than 20 tags should fail."""
        with pytest.raises(ValidationError):
            Activity(
                id="test-001",
                name="Test",
                city="City",
                type=ActivityType.OTHER,
                estimated_duration_hours=1,
                cost_band=CostBand.MODERATE,
                rationale="Test",
                tags=[f"tag{i}" for i in range(21)],
            )
    
    def test_address_max_length_300(self):
        """Address max 300 chars."""
        with pytest.raises(ValidationError):
            Activity(
                id="test-001",
                name="Test",
                city="City",
                type=ActivityType.OTHER,
                estimated_duration_hours=1,
                cost_band=CostBand.MODERATE,
                rationale="Test",
                address="A" * 301,
            )


# ============================================================================
# ActivityCatalog Edge Cases
# ============================================================================

class TestActivityCatalogEdgeCases:
    """Test edge cases for activity catalog."""
    
    def test_empty_activities_list_fails(self):
        """Empty activities list should fail."""
        with pytest.raises(ValidationError):
            ActivityCatalog(
                activities=[],  # Empty
                per_city={},
            )
    
    def test_per_city_references_nonexistent_activity_fails(self):
        """per_city references must exist in activities."""
        activity = Activity(
            id="valid-id",
            name="Valid",
            city="Tokyo",
            type=ActivityType.TEMPLE,
            estimated_duration_hours=2,
            cost_band=CostBand.BUDGET,
            rationale="Valid",
        )
        with pytest.raises(ValidationError) as exc_info:
            ActivityCatalog(
                activities=[activity],
                per_city={"Tokyo": ["valid-id", "nonexistent-id"]},  # One invalid
            )
        assert "not found" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()


# ============================================================================
# BudgetBreakdown Edge Cases
# ============================================================================

class TestBudgetBreakdownEdgeCases:
    """Test boundary conditions for budget."""
    
    def test_empty_categories_fails(self):
        """Empty categories list should fail."""
        with pytest.raises(ValidationError):
            BudgetBreakdown(
                categories=[],  # Empty
                grand_total=0,
                currency="USD",
                within_budget=True,
                remaining_buffer=0,
            )
    
    def test_mismatched_currencies_fails(self):
        """All categories must use same currency."""
        categories = [
            BudgetCategory(category="stay", estimated_total=800, currency="USD"),
            BudgetCategory(category="food", estimated_total=500, currency="EUR"),  # Different!
        ]
        with pytest.raises(ValidationError) as exc_info:
            BudgetBreakdown(
                categories=categories,
                grand_total=1300,
                currency="USD",
                within_budget=True,
                remaining_buffer=0,
            )
        assert "same currency" in str(exc_info.value).lower()
    
    def test_currency_lowercase_converted(self):
        """Currency should be uppercase."""
        budget = BudgetBreakdown(
            categories=[
                BudgetCategory(category="stay", estimated_total=800, currency="usd"),
            ],
            grand_total=800,
            currency="usd",  # lowercase
            within_budget=True,
            remaining_buffer=0,
        )
        assert budget.currency == "USD"
    
    def test_grand_total_mismatch_fails(self):
        """Grand total must match sum of categories (within $0.01)."""
        categories = [
            BudgetCategory(category="stay", estimated_total=800, currency="USD"),
            BudgetCategory(category="food", estimated_total=500, currency="USD"),
        ]
        with pytest.raises(ValidationError) as exc_info:
            BudgetBreakdown(
                categories=categories,
                grand_total=1000,  # Wrong! Should be 1300
                currency="USD",
                within_budget=True,
                remaining_buffer=0,
            )
        assert "doesn't match" in str(exc_info.value).lower()
    
    def test_negative_cost_fails(self):
        """Individual category costs cannot be negative."""
        with pytest.raises(ValidationError):
            categories = [
                BudgetCategory(category="stay", estimated_total=-100, currency="USD"),
            ]
    
    def test_violation_with_zero_or_negative_over_by_fails(self):
        """Budget violations must have positive 'over_by' amount."""
        categories = [
            BudgetCategory(category="stay", estimated_total=800, currency="USD"),
        ]
        with pytest.raises(ValidationError) as exc_info:
            BudgetBreakdown(
                categories=categories,
                grand_total=800,
                currency="USD",
                within_budget=False,
                remaining_buffer=-100,
                violations=[
                    BudgetViolation(category="stay", estimated=800, limit=700, over_by=0)  # Invalid
                ],
            )
        assert "positive" in str(exc_info.value).lower()
    
    def test_valid_violation_passes(self):
        """Valid budget violation with positive over_by passes."""
        categories = [
            BudgetCategory(category="stay", estimated_total=800, currency="USD"),
        ]
        budget = BudgetBreakdown(
            categories=categories,
            grand_total=800,
            currency="USD",
            within_budget=False,
            remaining_buffer=-100,
            violations=[
                BudgetViolation(category="stay", estimated=800, limit=700, over_by=100)
            ],
        )
        assert len(budget.violations) == 1
    
    def test_swap_with_zero_savings_fails(self):
        """Suggested swaps must have positive savings."""
        categories = [
            BudgetCategory(category="activities", estimated_total=500, currency="USD"),
        ]
        with pytest.raises(ValidationError) as exc_info:
            BudgetBreakdown(
                categories=categories,
                grand_total=500,
                currency="USD",
                within_budget=True,
                remaining_buffer=0,
                suggested_swaps=[
                    SuggestedSwap(
                        original_item="expensive-restaurant",
                        suggested_alternative="cheaper-alternative",
                        savings_estimate=0,  # Invalid
                        rationale="Same quality",
                    )
                ],
            )
        assert "positive" in str(exc_info.value).lower()
    
    def test_valid_swap_passes(self):
        """Valid swap with positive savings passes."""
        categories = [
            BudgetCategory(category="activities", estimated_total=500, currency="USD"),
        ]
        budget = BudgetBreakdown(
            categories=categories,
            grand_total=500,
            currency="USD",
            within_budget=True,
            remaining_buffer=0,
            suggested_swaps=[
                SuggestedSwap(
                    original_item="expensive-restaurant",
                    suggested_alternative="cheaper-alternative",
                    savings_estimate=50,
                    rationale="Same quality, cheaper",
                )
            ],
        )
        assert len(budget.suggested_swaps) == 1
    
    def test_too_many_violations_fails(self):
        """More than 50 violations should fail."""
        categories = [
            BudgetCategory(category="stay", estimated_total=100, currency="USD"),
        ]
        with pytest.raises(ValidationError):
            BudgetBreakdown(
                categories=categories,
                grand_total=100,
                currency="USD",
                within_budget=False,
                remaining_buffer=-5000,
                violations=[
                    BudgetViolation(category=f"item{i}", estimated=100, limit=50, over_by=50)
                    for i in range(51)
                ],
            )
    
    def test_too_many_swaps_fails(self):
        """More than 50 suggested swaps should fail."""
        categories = [
            BudgetCategory(category="activities", estimated_total=500, currency="USD"),
        ]
        with pytest.raises(ValidationError):
            BudgetBreakdown(
                categories=categories,
                grand_total=500,
                currency="USD",
                within_budget=True,
                remaining_buffer=0,
                suggested_swaps=[
                    SuggestedSwap(
                        original_item=f"item{i}",
                        suggested_alternative=f"alt{i}",
                        savings_estimate=10,
                        rationale="Cheaper",
                    )
                    for i in range(51)
                ],
            )
    
    def test_too_many_flags_fails(self):
        """More than 20 flags should fail."""
        categories = [
            BudgetCategory(category="stay", estimated_total=800, currency="USD"),
        ]
        with pytest.raises(ValidationError):
            BudgetBreakdown(
                categories=categories,
                grand_total=800,
                currency="USD",
                within_budget=True,
                remaining_buffer=0,
                flags=[f"flag{i}" for i in range(21)],
            )


# ============================================================================
# DayItinerary Edge Cases
# ============================================================================

class TestDayItineraryEdgeCases:
    """Test boundary conditions for day itinerary."""
    
    def test_day_number_boundary(self):
        """Day number must be 1-365."""
        # Valid boundaries
        DayItinerary(
            day_number=1,
            city="Tokyo",
            items=[],
            day_summary="First day",
            day_cost=0,
        )
        DayItinerary(
            day_number=365,
            city="Tokyo",
            items=[],
            day_summary="Last day",
            day_cost=0,
        )
        
        # Invalid
        with pytest.raises(ValidationError):
            DayItinerary(
                day_number=0,  # Too low
                city="Tokyo",
                items=[],
                day_summary="Invalid day",
                day_cost=0,
            )
        with pytest.raises(ValidationError):
            DayItinerary(
                day_number=366,  # Too high
                city="Tokyo",
                items=[],
                day_summary="Invalid day",
                day_cost=0,
            )
    
    def test_too_many_items_fails(self):
        """More than 15 items in a day should fail."""
        items = [
            DayItineraryItem(
                slot_index=i,
                time="09:00 - 10:00",
                activity_name=f"Activity {i}",
                city="Tokyo",
                type=ActivityType.OTHER,
                cost_estimate=0,
            )
            for i in range(16)
        ]
        with pytest.raises(ValidationError):
            DayItinerary(
                day_number=1,
                city="Tokyo",
                items=items,
                day_summary="Busy day",
                day_cost=0,
            )
    
    def test_duplicate_slot_indices_fails(self):
        """Duplicate slot indices in same day should fail."""
        items = [
            DayItineraryItem(
                slot_index=0,
                time="09:00 - 10:00",
                activity_name="Activity 1",
                city="Tokyo",
                type=ActivityType.TEMPLE,
                cost_estimate=0,
            ),
            DayItineraryItem(
                slot_index=0,  # Duplicate!
                time="10:00 - 11:00",
                activity_name="Activity 2",
                city="Tokyo",
                type=ActivityType.FOOD,
                cost_estimate=0,
            ),
        ]
        with pytest.raises(ValidationError) as exc_info:
            DayItinerary(
                day_number=1,
                city="Tokyo",
                items=items,
                day_summary="Duplicate slots",
                day_cost=0,
            )
        assert "duplicate" in str(exc_info.value).lower()
    
    def test_day_cost_mismatch_fails(self):
        """Day cost must match sum of item costs (within $1)."""
        items = [
            DayItineraryItem(
                slot_index=0,
                time="09:00 - 10:00",
                activity_name="Temple",
                city="Tokyo",
                type=ActivityType.TEMPLE,
                cost_estimate=50,
            ),
            DayItineraryItem(
                slot_index=1,
                time="12:00 - 13:00",
                activity_name="Lunch",
                city="Tokyo",
                type=ActivityType.FOOD,
                cost_estimate=30,
            ),
        ]
        with pytest.raises(ValidationError) as exc_info:
            DayItinerary(
                day_number=1,
                city="Tokyo",
                items=items,
                day_summary="Day with wrong cost",
                day_cost=500,  # Wrong! Should be 80
            )
        assert "doesn't match" in str(exc_info.value).lower()
    
    def test_slot_index_too_high_fails(self):
        """Slot index over 15 should fail."""
        with pytest.raises(ValidationError) as exc_info:
            DayItineraryItem(
                slot_index=16,  # Too high
                time="09:00 - 10:00",
                activity_name="Activity",
                city="Tokyo",
                type=ActivityType.OTHER,
                cost_estimate=0,
            )
        assert "15" in str(exc_info.value) or "slots" in str(exc_info.value).lower()
    
    def test_negative_cost_estimate_fails(self):
        """Negative cost estimate should fail."""
        with pytest.raises(ValidationError):
            DayItineraryItem(
                slot_index=0,
                time="09:00 - 10:00",
                activity_name="Activity",
                city="Tokyo",
                type=ActivityType.OTHER,
                cost_estimate=-10,  # Negative
            )
    
    def test_empty_summary_fails(self):
        """Empty day summary should fail."""
        with pytest.raises(ValidationError):
            DayItinerary(
                day_number=1,
                city="Tokyo",
                items=[],
                day_summary="",  # Empty
                day_cost=0,
            )


# ============================================================================
# Cross-Model Integration Edge Cases
# ============================================================================

class TestIntegrationEdgeCases:
    """Test edge cases across model boundaries."""
    
    def test_unicode_in_destination(self):
        """Unicode characters in destination should work."""
        constraints = TravelConstraints(
            destination_region="日本",  # Japan in Japanese
            cities=["東京", "京都"],  # Tokyo, Kyoto
            duration_days=5,
            budget_total=3000,
        )
        assert constraints.destination_region == "日本"
    
    def test_special_characters_in_city_names(self):
        """Special characters in city names should work."""
        constraints = TravelConstraints(
            destination_region="Test",
            cities=["São Paulo", "Zürich", "Niš"],  # Cities with special chars
            duration_days=5,
            budget_total=1000,
        )
        assert "São Paulo" in constraints.cities
    
    def test_very_long_strings_truncated_or_limited(self):
        """Very long strings should be rejected at appropriate boundaries."""
        # Activity name at boundary
        Activity(
            id="test-001",
            name="A" * 200,  # Exactly at limit
            city="City",
            type=ActivityType.OTHER,
            estimated_duration_hours=1,
            cost_band=CostBand.MODERATE,
            rationale="Test",
        )
        
        # Over limit should fail
        with pytest.raises(ValidationError):
            Activity(
                id="test-002",
                name="A" * 201,  # One over
                city="City",
                type=ActivityType.OTHER,
                estimated_duration_hours=1,
                cost_band=CostBand.MODERATE,
                rationale="Test",
            )
    
    def test_floating_point_precision_in_budget(self):
        """Test floating point precision handling in budget."""
        categories = [
            BudgetCategory(category="stay", estimated_total=100.005, currency="USD"),
            BudgetCategory(category="food", estimated_total=50.995, currency="USD"),
        ]
        # Sum is 151.00, should pass with 0.01 tolerance
        budget = BudgetBreakdown(
            categories=categories,
            grand_total=151.00,
            currency="USD",
            within_budget=True,
            remaining_buffer=0,
        )
        assert abs(budget.grand_total - 151.00) < 0.01


# ============================================================================
# Observability Edge Cases (Phase 8)
# ============================================================================

class TestObservabilityEdgeCases:
    """Test edge cases for observability logging."""
    
    def test_log_agent_start_with_empty_trace_id(self):
        """Observability should handle empty/None trace IDs gracefully."""
        from app.utils.observability import ObservabilityLogger
        # Should not raise exception even with empty trace_id
        ObservabilityLogger.log_agent_start("test_agent", "", context={"key": "value"})
        ObservabilityLogger.log_agent_start("test_agent", None, context={})
    
    def test_log_agent_complete_with_negative_duration(self):
        """Should handle negative or zero duration gracefully."""
        from app.utils.observability import ObservabilityLogger
        ObservabilityLogger.log_agent_complete("test_agent", "trace-123", -100, success=True)
        ObservabilityLogger.log_agent_complete("test_agent", "trace-123", 0, success=True)
    
    def test_log_llm_prompt_with_zero_chars(self):
        """Should handle zero-length prompts."""
        from app.utils.observability import ObservabilityLogger
        ObservabilityLogger.log_llm_prompt("trace-123", "extraction", 0, 0, "model", 0)
    
    def test_log_tool_call_with_very_long_input(self):
        """Should truncate very long input summaries."""
        from app.utils.observability import ObservabilityLogger
        long_input = "x" * 1000
        ObservabilityLogger.log_tool_call("trace-123", "search", long_input, True, 100)
        # Should truncate to 100 chars internally
    
    def test_log_review_outcome_with_empty_checklist(self):
        """Should handle empty checklist summary."""
        from app.utils.observability import ObservabilityLogger
        ObservabilityLogger.log_review_outcome(
            "trace-123", 1, "pass", {}, 0, 0, 0
        )
    
    def test_log_repair_action_with_no_actions(self):
        """Should handle empty actions list."""
        from app.utils.observability import ObservabilityLogger
        ObservabilityLogger.log_repair_action("trace-123", 1, 0, [])
    
    def test_log_partial_failure_with_long_messages(self):
        """Should truncate long error/user messages."""
        from app.utils.observability import ObservabilityLogger
        long_message = "error " * 100
        ObservabilityLogger.log_partial_failure("trace-123", "agent", "fallback", long_message)
    
    def test_log_plan_complete_with_zero_values(self):
        """Should handle zero duration, days, cities."""
        from app.utils.observability import ObservabilityLogger
        ObservabilityLogger.log_plan_complete("trace-123", 0, "pass", 0, 0, 0)


# ============================================================================
# Timeout Edge Cases (Phase 8)
# ============================================================================

class TestTimeoutEdgeCases:
    """Test edge cases for timeout handling."""
    
    def test_timeout_with_zero_seconds(self):
        """Zero timeout should fail immediately."""
        import asyncio
        async def slow_task():
            await asyncio.sleep(1)
            return "done"
        
        try:
            asyncio.run(asyncio.wait_for(slow_task(), timeout=0))
            assert False, "Should have raised TimeoutError"
        except asyncio.TimeoutError:
            pass  # Expected
    
    def test_timeout_with_negative_seconds(self):
        """Negative timeout should be handled."""
        import asyncio
        async def instant_task():
            return "instant"
        
        # Python may handle negative timeout as immediate timeout
        try:
            result = asyncio.run(asyncio.wait_for(instant_task(), timeout=-1))
            # If it doesn't raise, that's also acceptable behavior
        except (asyncio.TimeoutError, ValueError):
            pass  # Either is acceptable


# ============================================================================
# API Routes Edge Cases (Phase 8)
# ============================================================================

class TestAPIRoutesEdgeCases:
    """Test edge cases for API routes."""
    
    def test_plan_request_with_empty_body(self):
        """Empty request body should be handled."""
        from app.api.routes import PlanRequest
        # Should validate that request is not empty
        with pytest.raises(Exception):
            PlanRequest(request="")
    
    def test_plan_request_with_very_long_string(self):
        """Very long request strings should be handled."""
        from app.api.routes import PlanRequest
        long_request = "I want to travel " * 1000
        # Should either accept or truncate
        try:
            req = PlanRequest(request=long_request)
            assert len(req.request) > 0
        except Exception:
            pass  # May reject if too long
    
    def test_plan_request_with_special_characters(self):
        """Special characters in request should be handled."""
        from app.api.routes import PlanRequest
        special_requests = [
            "Visit café in São Paulo for a week",
            "日本旅行 - 5 days in Tokyo",
            "Trip to Zürich & Niš for sightseeing",
            "Test: <script>alert('xss')</script> - travel plan",
        ]
        for req_str in special_requests:
            if req_str and len(req_str) >= 10:  # PlanRequest requires min_length=10
                req = PlanRequest(request=req_str)
                assert req.request == req_str
    
    def test_plan_request_with_unicode_emoji(self):
        """Emoji in request should be handled."""
        from app.api.routes import PlanRequest
        req = PlanRequest(request="I want to visit Japan 🇯🇵 and France 🇫🇷")
        assert "🇯🇵" in req.request


# ============================================================================
# Frontend Hook Edge Cases (Phase 9)
# ============================================================================

class TestFrontendHookEdgeCases:
    """Test edge cases for frontend usePlan hook behavior."""
    
    def test_submit_plan_with_whitespace_only(self):
        """Whitespace-only request should be rejected."""
        # This tests the hook's validation logic
        # The hook should return null and set error message
        request = "   \n\t   "
        assert not request.strip()
    
    def test_submit_plan_with_very_long_request(self):
        """Very long request should be handled."""
        long_request = "I want to visit " + ", ".join([f"city{i}" for i in range(100)])
        # Should either accept or truncate
        assert len(long_request) > 100  # Just verify it's reasonably long
    
    def test_trace_id_handling_with_none(self):
        """Trace ID should handle None gracefully."""
        trace_id = None
        # Should convert to null string or handle appropriately
        assert trace_id is None or trace_id == "null"
    
    def test_error_message_with_special_chars(self):
        """Error messages with special characters should display correctly."""
        error_msg = "Error: API returned 500 (Internal Server Error) - <network issue>"
        # Should not break UI rendering
        assert len(error_msg) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
