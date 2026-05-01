"""
Tests for Phase 4 Worker Agents.
Tests use mocked ToolRouter to avoid external API calls.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

from app.agents import DestinationAgent, LogisticsAgent, BudgetAgent
from app.models import (
    TravelConstraints, ActivityCatalog, ActivityType,
    CrowdLevel, CostBand, LogisticsOutput, BudgetBreakdown
)
from app.tools import ToolRouter


@pytest.fixture
def sample_constraints():
    """Sample Japan travel constraints."""
    return TravelConstraints(
        destination_region="Japan",
        cities=["Tokyo", "Kyoto"],
        duration_days=5,
        budget_total=3000,
        currency="USD",
        preferences=["food", "temples"],
        avoidances=["crowds"]
    )


class TestDestinationAgent:
    """Test Destination Research Agent (Phase 4a)."""
    
    @pytest.mark.asyncio
    async def test_research_returns_activity_catalog(self, sample_constraints):
        """Agent returns ActivityCatalog with activities."""
        agent = DestinationAgent()
        
        catalog = await agent.research(sample_constraints)
        
        assert isinstance(catalog, ActivityCatalog)
        assert len(catalog.all_activities) > 0
        assert "Tokyo" in catalog.per_city
        assert "Kyoto" in catalog.per_city
    
    @pytest.mark.asyncio
    async def test_research_filters_by_avoidances(self):
        """Agent filters out activities matching avoidances."""
        constraints = TravelConstraints(
            destination_region="Japan",
            cities=["Tokyo"],
            duration_days=3,
            budget_total=1000,
            currency="USD",
            preferences=["temples"],
            avoidances=["crowds"]  # Should filter high-crowd activities
        )
        agent = DestinationAgent()
        
        catalog = await agent.research(constraints)
        
        # High crowd activities should be filtered
        for activity in catalog.all_activities:
            assert activity.crowd_level != CrowdLevel.HIGH
    
    @pytest.mark.asyncio
    async def test_research_tags_must_do(self, sample_constraints):
        """Must-do activities are tagged based on preferences."""
        agent = DestinationAgent()
        
        catalog = await agent.research(sample_constraints)
        
        # Should have some must-do activities
        must_do_count = sum(1 for a in catalog.all_activities if a.must_do)
        assert must_do_count > 0
    
    @pytest.mark.asyncio
    async def test_research_with_tool_router(self, sample_constraints):
        """Agent uses ToolRouter when available."""
        mock_router = MagicMock()
        mock_router.search = AsyncMock(return_value=[
            {"title": "Test Temple", "snippet": "A beautiful temple", "url": "http://test.com"}
        ])
        
        agent = DestinationAgent(tool_router=mock_router)
        catalog = await agent.research(sample_constraints)
        
        # ToolRouter should have been called
        assert mock_router.search.called
        assert isinstance(catalog, ActivityCatalog)


class TestLogisticsAgent:
    """Test Logistics Agent (Phase 4b)."""
    
    @pytest.mark.asyncio
    async def test_plan_returns_logistics_output(self, sample_constraints):
        """Agent returns LogisticsOutput with lodging, movement, skeletons."""
        agent = LogisticsAgent()
        
        output = await agent.plan(sample_constraints)
        
        assert isinstance(output, LogisticsOutput)
        assert len(output.lodging_plans) == 2  # Tokyo + Kyoto
        assert len(output.movement_plans) == 1  # Tokyo -> Kyoto
        assert len(output.day_skeletons) == 5  # 5 days
    
    @pytest.mark.asyncio
    async def test_plan_allocates_nights(self, sample_constraints):
        """Nights are allocated across cities."""
        agent = LogisticsAgent()
        
        output = await agent.plan(sample_constraints)
        
        total_nights = sum(l.nights for l in output.lodging_plans)
        assert total_nights == sample_constraints.duration_days
    
    @pytest.mark.asyncio
    async def test_plan_creates_travel_days(self, sample_constraints):
        """Travel days are marked in skeletons."""
        agent = LogisticsAgent()
        
        output = await agent.plan(sample_constraints)
        
        # Should have at least one travel day for inter-city movement
        travel_days = [s for s in output.day_skeletons if s.is_travel_day]
        assert len(travel_days) >= 1
    
    @pytest.mark.asyncio
    async def test_plan_uses_tool_router(self, sample_constraints):
        """Agent uses ToolRouter.geo_estimate when available."""
        mock_router = MagicMock()
        mock_router.geo_estimate = AsyncMock(return_value={
            "distance_km": 513,
            "duration_minutes": 135,
            "mode": "shinkansen",
            "estimated_cost_usd": 100,
            "notes": "Fast train"
        })
        
        agent = LogisticsAgent(tool_router=mock_router)
        output = await agent.plan(sample_constraints)
        
        # Should have called geo_estimate for inter-city travel
        assert mock_router.geo_estimate.called
        assert output.movement_plans[0].mode == "shinkansen"
    
    @pytest.mark.asyncio
    async def test_single_city_no_movement(self):
        """Single city trip has no movement plans."""
        constraints = TravelConstraints(
            destination_region="Japan",
            cities=["Tokyo"],
            duration_days=3,
            budget_total=1000,
            currency="USD",
            preferences=["food"],
            avoidances=[]
        )
        agent = LogisticsAgent()
        
        output = await agent.plan(constraints)
        
        assert len(output.movement_plans) == 0
        assert "no inter-city travel" in output.logistics_summary.lower()


class TestBudgetAgent:
    """Test Budget Agent (Phase 4c)."""
    
    @pytest.mark.asyncio
    async def test_analyze_returns_budget_breakdown(self, sample_constraints):
        """Agent returns BudgetBreakdown with categories."""
        agent = BudgetAgent()
        
        breakdown = await agent.analyze(sample_constraints)
        
        assert isinstance(breakdown, BudgetBreakdown)
        assert len(breakdown.categories) > 0
        assert breakdown.currency == "USD"
    
    @pytest.mark.asyncio
    async def test_analyze_detects_budget_status(self):
        """Agent correctly identifies within/over budget."""
        # Under budget case
        constraints_under = TravelConstraints(
            destination_region="Japan",
            cities=["Tokyo"],
            duration_days=3,
            budget_total=5000,  # High budget
            currency="USD",
            preferences=["food"],
            avoidances=[]
        )
        agent = BudgetAgent()
        
        breakdown = await agent.analyze(constraints_under)
        assert breakdown.within_budget is True
        assert breakdown.remaining_buffer > 0
        
        # Over budget case
        constraints_over = TravelConstraints(
            destination_region="Japan",
            cities=["Tokyo", "Kyoto", "Osaka"],  # Many cities
            duration_days=10,
            budget_total=500,  # Low budget
            currency="USD",
            preferences=["luxury"],
            avoidances=[]
        )
        
        breakdown = await agent.analyze(constraints_over)
        assert breakdown.within_budget is False
        assert len(breakdown.violations) > 0
    
    @pytest.mark.asyncio
    async def test_analyze_suggests_swaps_when_over_budget(self):
        """Agent suggests cost-saving swaps when over budget."""
        constraints = TravelConstraints(
            destination_region="Japan",
            cities=["Tokyo", "Kyoto"],
            duration_days=5,
            budget_total=500,  # Very tight budget
            currency="USD",
            preferences=["luxury"],
            avoidances=[]
        )
        agent = BudgetAgent()
        
        breakdown = await agent.analyze(constraints)
        
        assert not breakdown.within_budget
        assert len(breakdown.suggested_swaps) > 0
    
    @pytest.mark.asyncio
    async def test_analyze_uses_tool_router(self, sample_constraints):
        """Agent uses ToolRouter.price_band when available."""
        mock_router = MagicMock()
        mock_router.price_band = AsyncMock(return_value={
            "estimate_usd": 120,
            "notes": "3-star hotel"
        })
        
        agent = BudgetAgent(tool_router=mock_router)
        breakdown = await agent.analyze(sample_constraints)
        
        # Should have called price_band for hotel estimates
        assert mock_router.price_band.called
        assert isinstance(breakdown, BudgetBreakdown)
    
    def test_price_band_determination(self):
        """Agent correctly determines price band from budget."""
        agent = BudgetAgent()
        
        # Budget traveler
        budget_constraints = TravelConstraints(
            destination_region="Test",
            cities=["City"],
            duration_days=5,
            budget_total=400,  # $80/day
            currency="USD",
            preferences=[],
            avoidances=[]
        )
        assert agent._determine_price_band(budget_constraints) == "budget"
        
        # Luxury traveler
        luxury_constraints = TravelConstraints(
            destination_region="Test",
            cities=["City"],
            duration_days=5,
            budget_total=3000,  # $600/day
            currency="USD",
            preferences=[],
            avoidances=[]
        )
        assert agent._determine_price_band(luxury_constraints) == "luxury"


class TestAgentIntegration:
    """Integration tests for all three agents working together."""
    
    @pytest.mark.asyncio
    async def test_agents_workflow(self, sample_constraints):
        """All three agents can work together in sequence."""
        tool_router = ToolRouter()
        
        # Create agents with shared ToolRouter
        dest_agent = DestinationAgent(tool_router=tool_router)
        logistics_agent = LogisticsAgent(tool_router=tool_router)
        budget_agent = BudgetAgent(tool_router=tool_router)
        
        # Run agents
        catalog = await dest_agent.research(sample_constraints)
        logistics = await logistics_agent.plan(sample_constraints, catalog)
        budget = await budget_agent.analyze(sample_constraints)
        
        # Verify outputs
        assert isinstance(catalog, ActivityCatalog)
        assert isinstance(logistics, LogisticsOutput)
        assert isinstance(budget, BudgetBreakdown)
        
        # Cities should align
        assert set(catalog.per_city.keys()) == set(sample_constraints.cities)
        assert len(logistics.lodging_plans) == len(sample_constraints.cities)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
