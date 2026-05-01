"""
Tests for TripStructuringAgent.
"""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import UUID

from app.agents.trip_structuring import TripStructuringAgent
from app.models import TravelConstraints, TripStructure, Region


@pytest.fixture
def agent():
    return TripStructuringAgent(llm_client=None)


@pytest.fixture
def long_trip_constraints():
    return TravelConstraints(
        destination_region="Iceland",
        cities=["Reykjavik", "Akureyri", "Vik"],
        duration_days=10,
        budget_total=5000,
        currency="USD"
    )


@pytest.fixture
def short_trip_constraints():
    return TravelConstraints(
        destination_region="Japan",
        cities=["Tokyo"],
        duration_days=5,
        budget_total=2000,
        currency="USD"
    )


class TestTripStructuringAgent:

    @pytest.mark.asyncio
    async def test_structure_long_trip_uses_database(self, agent, long_trip_constraints):
        """Should use static database for known long trips."""
        structure = await agent.structure(long_trip_constraints)
        
        assert isinstance(structure, TripStructure)
        assert len(structure.regions) > 1
        assert structure.trip_type == "road_trip"
        # Iceland 10 days should have specific regions from DB
        region_names = [r.name for r in structure.regions]
        assert "South Coast" in region_names
        
        # Total days in regions should roughly match duration
        total_days = sum(r.days for r in structure.regions)
        assert total_days == 10

    @pytest.mark.asyncio
    async def test_structure_short_trip_returns_single_region(self, agent, short_trip_constraints):
        """Short single-city trips should just get a single region structure."""
        structure = await agent.structure(short_trip_constraints)
        
        assert isinstance(structure, TripStructure)
        assert len(structure.regions) == 1
        assert structure.regions[0].name == "Tokyo"
        assert structure.regions[0].days == 5

    @pytest.mark.asyncio
    async def test_structure_unknown_long_trip_fallback(self, agent):
        """Unknown long trip should fallback to chunking cities."""
        constraints = TravelConstraints(
            destination_region="UnknownCountry",
            cities=["CityA", "CityB", "CityC"],
            duration_days=12,
            budget_total=5000,
            currency="USD"
        )
        
        structure = await agent.structure(constraints)
        
        assert isinstance(structure, TripStructure)
        assert len(structure.regions) == 3
        assert structure.regions[0].name == "CityA"
        assert structure.regions[1].name == "CityB"
        assert structure.regions[2].name == "CityC"
        
        # 12 days / 3 cities = 4 days each
        assert structure.regions[0].days == 4

    @pytest.mark.asyncio
    async def test_structure_road_trip_flag(self, agent):
        """If is_road_trip is true, it should structure it even if short."""
        constraints = TravelConstraints(
            destination_region="Iceland",
            cities=["Reykjavik"],
            duration_days=5,
            budget_total=5000,
            currency="USD",
            is_road_trip=True
        )
        
        structure = await agent.structure(constraints)
        
        assert isinstance(structure, TripStructure)
        assert len(structure.regions) > 1
        assert structure.trip_type == "road_trip"
