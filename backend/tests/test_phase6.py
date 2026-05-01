"""
Test Suite for Phase 6 - Review Agent

Tests the quality gate that validates draft itineraries before user delivery.
Two-layer design: Programmatic checks + optional LLM qualitative checks.
"""

import pytest
from datetime import datetime
from uuid import uuid4

from app.agents.review import ReviewAgent
from app.models import (
    TravelConstraints,
    DraftItinerary,
    DayItinerary,
    DayItineraryItem,
    BudgetBreakdown,
    BudgetCategory,
    ReviewStatus,
    ReviewSeverity,
    ActivityType,
    CostBand,
)


@pytest.fixture
def sample_constraints():
    """Create sample travel constraints for testing."""
    return TravelConstraints(
        destination_region="Japan",
        cities=["Tokyo", "Kyoto"],
        duration_days=5,
        budget_total=3000.0,
        currency="USD",
        soft_preferences=["food", "temples", "culture"],
        avoidances=["crowds"],
        trace_id=uuid4()
    )


@pytest.fixture
def sample_budget():
    """Create sample budget breakdown."""
    return BudgetBreakdown(
        categories=[
            BudgetCategory(
                category="stay",
                estimated_total=1200.0,
                currency="USD",
                notes="5 nights"
            ),
            BudgetCategory(
                category="food",
                estimated_total=500.0,
                currency="USD",
                notes="Daily meals"
            ),
            BudgetCategory(
                category="activities",
                estimated_total=400.0,
                currency="USD",
                notes="Attractions"
            ),
        ],
        grand_total=2100.0,
        currency="USD",
        within_budget=True,
        remaining_buffer=900.0,
    )


@pytest.fixture
def valid_draft(sample_constraints, sample_budget):
    """Create a valid draft itinerary for testing."""
    days = [
        DayItinerary(
            day_number=1,
            city="Tokyo",
            items=[
                DayItineraryItem(
                    slot_index=0,
                    time="09:00 - 12:00",
                    activity_id="tokyo-temple-1",
                    activity_name="Senso-ji Temple",
                    city="Tokyo",
                    type=ActivityType.TEMPLE,
                    cost_estimate=0.0,
                ),
                DayItineraryItem(
                    slot_index=1,
                    time="12:00 - 13:30",
                    activity_id="tokyo-food-1",
                    activity_name="Lunch in Asakusa",
                    city="Tokyo",
                    type=ActivityType.FOOD,
                    cost_estimate=25.0,
                ),
            ],
            day_summary="Explore Senso-ji Temple and enjoy local food in Asakusa",
            day_cost=25.0,
            lodging_area="Shibuya",
        ),
        DayItinerary(
            day_number=2,
            city="Tokyo",
            items=[
                DayItineraryItem(
                    slot_index=0,
                    time="09:00 - 12:00",
                    activity_id="tokyo-museum-1",
                    activity_name="Tokyo National Museum",
                    city="Tokyo",
                    type=ActivityType.MUSEUM,
                    cost_estimate=15.0,
                ),
            ],
            day_summary="Visit Tokyo National Museum",
            day_cost=15.0,
            lodging_area="Shibuya",
        ),
        DayItinerary(
            day_number=3,
            city="Kyoto",
            items=[
                DayItineraryItem(
                    slot_index=0,
                    time="09:00 - 12:00",
                    activity_id="kyoto-temple-1",
                    activity_name="Kinkaku-ji",
                    city="Kyoto",
                    type=ActivityType.TEMPLE,
                    cost_estimate=5.0,
                ),
            ],
            day_summary="Visit Kinkaku-ji Temple",
            day_cost=5.0,
            lodging_area="Gion",
        ),
        DayItinerary(
            day_number=4,
            city="Kyoto",
            items=[
                DayItineraryItem(
                    slot_index=0,
                    time="09:00 - 12:00",
                    activity_id="kyoto-shrine-1",
                    activity_name="Fushimi Inari",
                    city="Kyoto",
                    type=ActivityType.TEMPLE,
                    cost_estimate=0.0,
                ),
            ],
            day_summary="Explore Fushimi Inari Shrine",
            day_cost=0.0,
            lodging_area="Gion",
        ),
        DayItinerary(
            day_number=5,
            city="Kyoto",
            items=[
                DayItineraryItem(
                    slot_index=0,
                    time="09:00 - 12:00",
                    activity_id="kyoto-food-1",
                    activity_name="Nishiki Market",
                    city="Kyoto",
                    type=ActivityType.FOOD,
                    cost_estimate=30.0,
                ),
            ],
            day_summary="Visit Nishiki Market for food",
            day_cost=30.0,
            lodging_area="Gion",
        ),
    ]
    
    return DraftItinerary(
        constraints=sample_constraints,
        days=days,
        total_estimated_cost=2100.0,
        currency="USD",
        budget_summary=sample_budget,
        catalog_references=["tokyo-temple-1", "tokyo-food-1", "tokyo-museum-1", 
                           "kyoto-temple-1", "kyoto-shrine-1", "kyoto-food-1"],
    )


@pytest.fixture
def review_agent():
    """Create ReviewAgent instance without LLM for testing."""
    return ReviewAgent(llm_client=None)


class TestReviewAgent:
    """Test the ReviewAgent quality gate functionality."""
    
    @pytest.mark.asyncio
    async def test_review_agent_initializes(self):
        """ReviewAgent can be instantiated."""
        agent = ReviewAgent(llm_client=None)
        assert agent is not None
        assert agent.llm_client is None
    
    @pytest.mark.asyncio
    async def test_valid_draft_passes_review(self, review_agent, valid_draft, sample_constraints):
        """A valid draft should pass programmatic checks."""
        report = await review_agent.review(valid_draft, sample_constraints)
        
        assert report is not None
        assert report.overall_status in [ReviewStatus.PASS, ReviewStatus.WARNINGS]
        assert report.can_deliver is True
        assert len(report.checklist) > 0
    
    @pytest.mark.asyncio
    async def test_duration_mismatch_fails(self, review_agent, valid_draft, sample_constraints):
        """Draft with wrong day count should fail."""
        # Remove a day to create mismatch
        valid_draft.days = valid_draft.days[:4]  # Only 4 days instead of 5
        
        report = await review_agent.review(valid_draft, sample_constraints)
        
        assert report.overall_status == ReviewStatus.FAIL
        assert not report.can_deliver
        
        # Check for duration check in checklist
        duration_check = next((c for c in report.checklist if c.check == "days_match_duration"), None)
        assert duration_check is not None
        assert not duration_check.passed
        assert duration_check.severity == ReviewSeverity.BLOCKING
    
    @pytest.mark.asyncio
    async def test_missing_city_fails(self, review_agent, valid_draft, sample_constraints):
        """Draft missing a required city should fail."""
        # Remove all Kyoto days
        valid_draft.days = [d for d in valid_draft.days if d.city == "Tokyo"]
        valid_draft.total_estimated_cost = sum(item.cost_estimate for d in valid_draft.days for item in d.items)
        
        report = await review_agent.review(valid_draft, sample_constraints)
        
        assert report.overall_status == ReviewStatus.FAIL
        assert not report.can_deliver
        
        # Check for cities check in checklist
        cities_check = next((c for c in report.checklist if c.check == "cities_included"), None)
        assert cities_check is not None
        assert not cities_check.passed
    
    @pytest.mark.asyncio
    async def test_over_budget_fails(self, review_agent, valid_draft, sample_constraints):
        """Draft over budget should fail or warn."""
        # Set budget to very low
        sample_constraints.budget_total = 1000.0
        valid_draft.total_estimated_cost = 2100.0
        
        report = await review_agent.review(valid_draft, sample_constraints)
        
        # Should have a budget check that failed
        budget_check = next((c for c in report.checklist if c.check == "within_budget"), None)
        assert budget_check is not None
        assert not budget_check.passed
    
    @pytest.mark.asyncio
    async def test_empty_day_fails(self, review_agent, valid_draft, sample_constraints):
        """Draft with empty day should fail."""
        # Add an empty day
        valid_draft.days.append(
            DayItinerary(
                day_number=6,
                city="Tokyo",
                items=[],  # Empty
                day_summary="Empty day - needs activities",
                day_cost=0.0,
                lodging_area="Shibuya",
            )
        )
        valid_draft.constraints.duration_days = 6
        
        report = await review_agent.review(valid_draft, sample_constraints)
        
        # Should have a check about empty day
        empty_check = next((c for c in report.checklist if "has_activities" in c.check), None)
        assert empty_check is not None
        assert not empty_check.passed
    
    @pytest.mark.asyncio
    async def test_repair_hints_generated(self, review_agent, valid_draft, sample_constraints):
        """Failed checks should generate repair hints."""
        # Make draft fail by removing a day
        valid_draft.days = valid_draft.days[:3]
        
        report = await review_agent.review(valid_draft, sample_constraints)
        
        assert not report.can_deliver
        assert len(report.repair_hints) > 0
        
        # Check for relevant repair hints
        duration_hint = next((h for h in report.repair_hints if "duration" in h.issue.lower() or "day count" in h.issue.lower()), None)
        assert duration_hint is not None
        assert duration_hint.priority >= 1
        assert duration_hint.priority <= 10
    
    @pytest.mark.asyncio
    async def test_checklist_items_populated(self, review_agent, valid_draft, sample_constraints):
        """Review should populate checklist with all programmatic checks."""
        report = await review_agent.review(valid_draft, sample_constraints)
        
        # Should have basic checks
        check_names = [c.check for c in report.checklist]
        assert "days_match_duration" in check_names
        assert "cities_included" in check_names
        assert "within_budget" in check_names
        assert "no_duplicate_days" in check_names
    
    @pytest.mark.asyncio
    async def test_qualitative_check_skipped_without_llm(self, review_agent, valid_draft, sample_constraints):
        """Without LLM client, qualitative check should be skipped."""
        report = await review_agent.review(valid_draft, sample_constraints)
        
        # Should pass without LLM
        assert report.overall_status == ReviewStatus.PASS
        # Qualitative assessment should be None
        assert report.qualitative_assessment is None


class TestReviewReportStructure:
    """Test the structure and properties of ReviewReport."""
    
    @pytest.mark.asyncio
    async def test_report_has_draft_version(self, review_agent, valid_draft, sample_constraints):
        """Report should reference draft version."""
        report = await review_agent.review(valid_draft, sample_constraints)
        
        assert report.draft_version == valid_draft.version
    
    @pytest.mark.asyncio
    async def test_report_has_review_timestamp(self, review_agent, valid_draft, sample_constraints):
        """Report should have reviewed_at timestamp."""
        before = datetime.utcnow()
        report = await review_agent.review(valid_draft, sample_constraints)
        after = datetime.utcnow()
        
        assert before <= report.reviewed_at <= after
    
    @pytest.mark.asyncio
    async def test_can_deliver_property(self, review_agent, valid_draft, sample_constraints):
        """can_deliver should be True only when no blocking issues."""
        # Valid draft should be deliverable
        report = await review_agent.review(valid_draft, sample_constraints)
        if report.overall_status != ReviewStatus.FAIL:
            assert report.can_deliver is True
        
        # Invalid draft should not be deliverable
        valid_draft.days = []  # Empty
        report = await review_agent.review(valid_draft, sample_constraints)
        assert not report.can_deliver
