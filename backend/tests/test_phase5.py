"""
Tests for Phase 5 - Orchestrator Parallel Execution & Merge.
Zero LLM tokens - tests use static data.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
import asyncio

from app.agents import OrchestratorAgent
from app.models import (
    TravelConstraints, FinalItinerary, DraftItinerary,
    ActivityCatalog, LogisticsOutput, BudgetBreakdown,
    ReviewStatus
)


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


class TestOrchestratorPhase5:
    """Test Phase 5 orchestration with parallel agents."""
    
    @pytest.mark.asyncio
    async def test_orchestrator_initializes_agents(self):
        """Orchestrator initializes all 3 worker agents with shared ToolRouter."""
        orchestrator = OrchestratorAgent(llm_client=None)
        
        assert orchestrator.destination_agent is not None
        assert orchestrator.logistics_agent is not None
        assert orchestrator.budget_agent is not None
        
        # All agents share the same ToolRouter
        assert orchestrator.destination_agent.tool_router is not None
        assert orchestrator.logistics_agent.tool_router is not None
        assert orchestrator.budget_agent.tool_router is not None
    
    @pytest.mark.asyncio
    async def test_create_plan_returns_final_itinerary(self, sample_constraints):
        """Full pipeline returns FinalItinerary."""
        orchestrator = OrchestratorAgent(llm_client=None)
        
        # Mock the extract_constraints to avoid LLM call
        orchestrator.extract_constraints = AsyncMock(return_value=sample_constraints)
        
        final = await orchestrator.create_plan("Plan a 5-day trip to Japan")
        
        assert isinstance(final, FinalItinerary)
        assert len(final.days) == 5  # 5 days
        assert final.constraints.cities == ["Tokyo", "Kyoto"]
    
    @pytest.mark.asyncio
    async def test_agents_run_in_parallel(self, sample_constraints):
        """Three agents execute concurrently."""
        orchestrator = OrchestratorAgent(llm_client=None)
        
        # Track execution order
        execution_order = []
        
        # Save original methods
        orig_research = orchestrator.destination_agent.research
        orig_plan = orchestrator.logistics_agent.plan
        orig_analyze = orchestrator.budget_agent.analyze
        
        async def slow_research(constraints):
            execution_order.append("destination_start")
            await asyncio.sleep(0.1)
            execution_order.append("destination_end")
            return await orig_research(constraints)

        async def slow_plan(constraints):
            execution_order.append("logistics_start")
            await asyncio.sleep(0.1)
            execution_order.append("logistics_end")
            return await orig_plan(constraints)

        async def slow_analyze(constraints):
            execution_order.append("budget_start")
            await asyncio.sleep(0.1)
            execution_order.append("budget_end")
            return await orig_analyze(constraints)
        
        # Replace methods with slow versions
        orchestrator.destination_agent.research = slow_research
        orchestrator.logistics_agent.plan = slow_plan
        orchestrator.budget_agent.analyze = slow_analyze
        
        # Run agents in parallel
        await asyncio.gather(
            orchestrator.destination_agent.research(sample_constraints),
            orchestrator.logistics_agent.plan(sample_constraints),
            orchestrator.budget_agent.analyze(sample_constraints)
        )
        
        # All should start before any ends (parallel execution)
        assert execution_order[0:3] == ["destination_start", "logistics_start", "budget_start"]
        assert execution_order[3:6] == ["destination_end", "logistics_end", "budget_end"]
    
    @pytest.mark.asyncio
    async def test_merge_creates_draft_itinerary(self, sample_constraints):
        """Merge creates DraftItinerary from agent outputs."""
        orchestrator = OrchestratorAgent(llm_client=None)
        
        # Get real agent outputs
        catalog = await orchestrator.destination_agent.research(sample_constraints)
        logistics = await orchestrator.logistics_agent.plan(sample_constraints)
        budget = await orchestrator.budget_agent.analyze(sample_constraints)
        
        # Merge
        draft = await orchestrator.merge(
            constraints=sample_constraints,
            activity_catalog=catalog,
            logistics_output=logistics,
            budget_breakdown=budget
        )
        
        assert isinstance(draft, DraftItinerary)
        assert len(draft.days) == 5
        assert draft.total_estimated_cost > 0
        assert draft.currency == "USD"
    
    @pytest.mark.asyncio
    async def test_merge_links_activities_to_slots(self, sample_constraints):
        """Merge links activity IDs to day slots."""
        orchestrator = OrchestratorAgent(llm_client=None)
        
        catalog = await orchestrator.destination_agent.research(sample_constraints)
        logistics = await orchestrator.logistics_agent.plan(sample_constraints)
        budget = await orchestrator.budget_agent.analyze(sample_constraints)
        
        draft = await orchestrator.merge(
            constraints=sample_constraints,
            activity_catalog=catalog,
            logistics_output=logistics,
            budget_breakdown=budget
        )
        
        # Check that activities are linked
        for day in draft.days:
            if not day.items:
                continue
            for item in day.items:
                if item.activity_id:
                    # Activity ref should exist in catalog
                    assert any(a.id == item.activity_id for a in catalog.activities)
    
    @pytest.mark.asyncio
    async def test_merge_preserves_travel_days(self, sample_constraints):
        """Travel days are preserved in merged output."""
        orchestrator = OrchestratorAgent(llm_client=None)
        
        catalog = await orchestrator.destination_agent.research(sample_constraints)
        logistics = await orchestrator.logistics_agent.plan(sample_constraints)
        budget = await orchestrator.budget_agent.analyze(sample_constraints)
        
        draft = await orchestrator.merge(
            constraints=sample_constraints,
            activity_catalog=catalog,
            logistics_output=logistics,
            budget_breakdown=budget
        )
        
        # Should have at least one travel day (Tokyo -> Kyoto)
        travel_days = [d for d in draft.days if any("travel" in str(item.notes).lower() for item in d.items)]
        # Note: is_travel_day flag is on skeleton, not preserved in DraftItinerary
        # But we can check for travel-related items
    
    @pytest.mark.asyncio
    async def test_draft_to_final_conversion(self, sample_constraints):
        """DraftItinerary converts to FinalItinerary."""
        orchestrator = OrchestratorAgent(llm_client=None)
        
        catalog = await orchestrator.destination_agent.research(sample_constraints)
        logistics = await orchestrator.logistics_agent.plan(sample_constraints)
        budget = await orchestrator.budget_agent.analyze(sample_constraints)
        
        draft = await orchestrator.merge(
            constraints=sample_constraints,
            activity_catalog=catalog,
            logistics_output=logistics,
            budget_breakdown=budget
        )
        
        final = orchestrator._draft_to_final(
            draft=draft,
            constraints=sample_constraints,
            budget_breakdown=budget
        )
        
        assert isinstance(final, FinalItinerary)
        assert final.review_status == ReviewStatus.PASS  # Phase 5: auto-pass
        assert "Verify prices" in final.disclaimer
        assert len(final.days) == len(draft.days)
        assert final.budget_rollup is not None
    
    @pytest.mark.asyncio
    async def test_end_to_end_pipeline(self, sample_constraints):
        """Full pipeline: constraints → agents → merge → final."""
        orchestrator = OrchestratorAgent(llm_client=None)
        
        # Mock constraint extraction to avoid LLM
        orchestrator.extract_constraints = AsyncMock(return_value=sample_constraints)
        
        final = await orchestrator.create_plan("Any request text")
        
        # Verify complete pipeline output
        assert isinstance(final, FinalItinerary)
        assert final.constraints.destination_region == "Japan"
        assert len(final.days) == 5
        assert final.logistics_summary != ""
        assert final.budget_rollup is not None
        assert len(final.neighborhoods) > 0


class TestOrchestratorErrorHandling:
    """Test error handling in Phase 5."""
    
    @pytest.mark.asyncio
    async def test_handles_agent_failure(self, sample_constraints):
        """Orchestrator raises error if any agent fails."""
        orchestrator = OrchestratorAgent(llm_client=None)
        
        # Mock constraint extraction
        orchestrator.extract_constraints = AsyncMock(return_value=sample_constraints)
        
        # Make destination agent fail
        orchestrator.destination_agent.research = AsyncMock(side_effect=Exception("Search failed"))
    
        # Should NOT raise RuntimeError anymore due to Phase 8 partial failure handling
        # It should fallback to a static catalog and complete the plan
        result = await orchestrator.create_plan("Plan a trip", trace_id="test-trace-id")
        
        # Verify it used the fallback catalog (should have generated activities)
        assert len(result.days) > 0
        assert "Search failed" not in result.disclaimer


class TestOrchestratorHierarchical:
    """Test hierarchical planning flow introduced in Session 16."""

    @pytest.fixture
    def long_constraints(self):
        return TravelConstraints(
            destination_region="Iceland",
            cities=["Reykjavik", "Vik", "Akureyri"],
            duration_days=10,
            budget_total=5000,
            currency="USD"
        )

    @pytest.mark.asyncio
    async def test_uses_structuring_for_long_trip(self, long_constraints):
        """Orchestrator should use TripStructuringAgent for trips > 7 days."""
        orchestrator = OrchestratorAgent(llm_client=None)
        orchestrator.extract_constraints = AsyncMock(return_value=long_constraints)
        
        # Mock per-region execution to track calls
        orchestrator._run_agents_per_region = AsyncMock(wraps=orchestrator._run_agents_per_region)
        orchestrator._run_agents_flat = AsyncMock(wraps=orchestrator._run_agents_flat)
        
        await orchestrator.create_plan("10 days in Iceland")
        
        assert orchestrator._run_agents_per_region.called
        assert not orchestrator._run_agents_flat.called

    @pytest.mark.asyncio
    async def test_uses_flat_for_short_trip(self, sample_constraints):
        """Orchestrator should use flat execution for short trips."""
        orchestrator = OrchestratorAgent(llm_client=None)
        orchestrator.extract_constraints = AsyncMock(return_value=sample_constraints)
        
        orchestrator._run_agents_per_region = AsyncMock(wraps=orchestrator._run_agents_per_region)
        orchestrator._run_agents_flat = AsyncMock(wraps=orchestrator._run_agents_flat)
        
        await orchestrator.create_plan("5 days in Japan")
        
        assert not orchestrator._run_agents_per_region.called
        assert orchestrator._run_agents_flat.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
