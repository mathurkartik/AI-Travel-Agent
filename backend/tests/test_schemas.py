"""
Tests for shared data models - Phase 1 Exit Criteria.
Golden JSON fixtures should round-trip through parsers without LLM calls.
"""

import pytest
from pydantic import ValidationError

from app.models import (
    TravelConstraints,
    Activity,
    ActivityCatalog,
    BudgetBreakdown,
    BudgetCategory,
    ActivityType,
    CrowdLevel,
    CostBand,
    JAPAN_5D_TOKYO_KYOTO_3000_CONSTRAINTS,
)


class TestTravelConstraints:
    """Test core constraint model."""
    
    def test_valid_constraints(self):
        """Golden fixture should validate."""
        constraints = JAPAN_5D_TOKYO_KYOTO_3000_CONSTRAINTS
        assert constraints.destination_region == "Japan"
        assert constraints.cities == ["Tokyo", "Kyoto"]
        assert constraints.duration_days == 5
        assert constraints.budget_total == 3000
        assert "food" in constraints.preferences
        assert "crowds" in constraints.avoidances
    
    def test_min_duration(self):
        """Duration must be at least 1 day."""
        with pytest.raises(ValidationError):
            TravelConstraints(
                destination_region="Test",
                cities=["City"],
                duration_days=0,
                budget_total=1000,
            )
    
    def test_budget_must_be_positive(self):
        """Budget must be positive."""
        with pytest.raises(ValidationError):
            TravelConstraints(
                destination_region="Test",
                cities=["City"],
                duration_days=5,
                budget_total=-100,
            )
    
    def test_cities_required(self):
        """Must have at least one city."""
        with pytest.raises(ValidationError):
            TravelConstraints(
                destination_region="Test",
                cities=[],
                duration_days=5,
                budget_total=1000,
            )
    
    def test_auto_trace_id(self):
        """Trace ID should auto-generate."""
        constraints = TravelConstraints(
            destination_region="Test",
            cities=["City"],
            duration_days=5,
            budget_total=1000,
        )
        assert constraints.trace_id is not None
    
    def test_serialization_roundtrip(self):
        """JSON serialization and deserialization."""
        original = JAPAN_5D_TOKYO_KYOTO_3000_CONSTRAINTS
        json_str = original.model_dump_json()
        restored = TravelConstraints.model_validate_json(json_str)
        
        assert restored.destination_region == original.destination_region
        assert restored.cities == original.cities
        assert restored.trace_id == original.trace_id


class TestActivityCatalog:
    """Test destination agent output model."""
    
    def test_valid_activity(self):
        """Activity with all required fields."""
        activity = Activity(
            id="tokyo-temple-001",
            name="Senso-ji Temple",
            city="Tokyo",
            type=ActivityType.TEMPLE,
            estimated_duration_hours=2,
            crowd_level=CrowdLevel.HIGH,
            cost_band=CostBand.BUDGET,
            must_do=True,
            rationale="Tokyo's oldest temple",
        )
        assert activity.id == "tokyo-temple-001"
        assert activity.type == ActivityType.TEMPLE
    
    def test_activity_duration_positive(self):
        """Duration must be positive."""
        with pytest.raises(ValidationError):
            Activity(
                id="test",
                name="Test",
                city="City",
                type=ActivityType.OTHER,
                estimated_duration_hours=0,
                cost_band=CostBand.MODERATE,
                rationale="Test",
            )
    
    def test_catalog_per_city_validation(self):
        """Activity IDs in per_city must exist in activities."""
        activity = Activity(
            id="valid-id",
            name="Test Activity",
            city="Tokyo",
            type=ActivityType.FOOD,
            estimated_duration_hours=1,
            cost_band=CostBand.MODERATE,
            rationale="Test",
        )
        
        # Valid: ID exists in activities
        catalog = ActivityCatalog(
            activities=[activity],
            per_city={"Tokyo": ["valid-id"]}
        )
        assert "Tokyo" in catalog.per_city
        
        # Invalid: ID not found
        with pytest.raises(ValidationError):
            ActivityCatalog(
                activities=[activity],
                per_city={"Tokyo": ["invalid-id"]}
            )


class TestBudgetBreakdown:
    """Test budget agent output model."""
    
    def test_grand_total_matches_sum(self):
        """Grand total must equal sum of categories."""
        categories = [
            BudgetCategory(category="stay", estimated_total=800, currency="USD"),
            BudgetCategory(category="food", estimated_total=500, currency="USD"),
            BudgetCategory(category="transport", estimated_total=700, currency="USD"),
            BudgetCategory(category="activities", estimated_total=450, currency="USD"),
        ]
        
        # Valid: totals match
        budget = BudgetBreakdown(
            categories=categories,
            grand_total=2450,
            currency="USD",
            within_budget=True,
            remaining_buffer=550,
        )
        assert budget.grand_total == 2450
        
        # Invalid: totals don't match
        with pytest.raises(ValidationError):
            BudgetBreakdown(
                categories=categories,
                grand_total=3000,  # Wrong!
                currency="USD",
                within_budget=False,
                remaining_buffer=-50,
            )
    
    def test_within_budget_flag(self):
        """Within budget flag should be consistent."""
        categories = [
            BudgetCategory(category="stay", estimated_total=2000, currency="USD"),
        ]
        
        budget = BudgetBreakdown(
            categories=categories,
            grand_total=2000,
            currency="USD",
            within_budget=False,  # Flag doesn't match, but schema allows
            remaining_buffer=-500,
            violations=[]
        )
        # Schema allows flag mismatch - business logic validates


class TestGoldenFixture:
    """Phase 1 exit criteria: Golden fixture round-trips."""
    
    def test_japan_fixture_serialization(self):
        """Japan 5d fixture serializes and deserializes correctly."""
        fixture = JAPAN_5D_TOKYO_KYOTO_3000_CONSTRAINTS
        
        # Serialize to JSON
        json_data = fixture.model_dump()
        
        # Verify structure
        assert json_data["destination_region"] == "Japan"
        assert json_data["duration_days"] == 5
        assert json_data["budget_total"] == 3000
        assert "Tokyo" in json_data["cities"]
        assert "Kyoto" in json_data["cities"]
        
        # Deserialize back
        restored = TravelConstraints.model_validate(json_data)
        assert restored.destination_region == fixture.destination_region


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
