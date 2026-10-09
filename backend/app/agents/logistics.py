"""
Logistics Agent - Phase 4b.
Handles practical side of moving and staying.
Uses LLM for neighborhood suggestions and route planning.
"""

import json
from typing import List, Optional, Dict
from datetime import datetime, timedelta

from ..models import (
    TravelConstraints,
    LogisticsOutput,
    LodgingPlan,
    MovementPlan,
    DaySkeleton,
    DaySlot,
    ActivityType,
    CostBand,
)


class LogisticsAgent:
    """
    Plans lodging, transport, and day structures.
    Uses LLM for city-specific neighborhood and transport recommendations.
    """

    def __init__(self, tool_router=None, llm_client=None):
        self.tool_router = tool_router
        self.llm_client = llm_client

    async def plan(self, constraints: TravelConstraints, activity_catalog: Optional[any] = None) -> LogisticsOutput:
        """Generate logistics plan from constraints."""
        cities = constraints.cities
        duration = constraints.duration_days

        night_allocation = self._allocate_nights(cities, duration)
        lodging_plans = await self._create_lodging_plans(cities, night_allocation, constraints, activity_catalog)
        movement_plans = await self._create_movement_plans(cities, constraints)
        day_skeletons = self._build_day_skeletons(night_allocation, lodging_plans, movement_plans, constraints, activity_catalog)
        total_transit_hours = sum(m.duration_hours for m in movement_plans)

        route_desc = None
        if constraints.is_road_trip:
            route_desc = await self._generate_route_description(constraints)

        return LogisticsOutput(
            lodging_plans=lodging_plans,
            movement_plans=movement_plans,
            day_skeletons=day_skeletons,
            total_estimated_transit_hours=total_transit_hours,
            route_description=route_desc,
            logistics_summary=self._generate_summary(movement_plans)
        )

    def _allocate_nights(self, cities: List[str], duration_days: int) -> Dict[str, int]:
        """Distribute nights across cities."""
        if not cities:
            return {}
        base_nights = duration_days // len(cities)
        remainder = duration_days % len(cities)
        allocation = {}
        for i, city in enumerate(cities):
            allocation[city] = base_nights + (1 if i < remainder else 0)
        return allocation

    async def _create_lodging_plans(self, cities: List[str], night_allocation: Dict[str, int],
                                     constraints: TravelConstraints, activity_catalog: Optional[any]) -> List[LodgingPlan]:
        """Create lodging plans, using LLM for neighborhood suggestions."""
        plans = []

        neighborhoods_map = {}
        if self.llm_client:
            try:
                neighborhoods_map = await self._llm_get_neighborhoods(cities, constraints)
            except Exception as e:
                print(f"LLM neighborhood generation failed: {e}")

        for city in cities:
            nights = night_allocation.get(city, 1)
            neighborhoods = neighborhoods_map.get(city, [f"Central {city}"])

            plan = LodgingPlan(
                city=city,
                nights=nights,
                suggested_neighborhoods=neighborhoods[:3],
                neighborhood_rationale=f"Selected based on proximity to activities in {city}",
                estimated_cost_per_night=CostBand.MODERATE
            )
            plans.append(plan)

        return plans

    async def _llm_get_neighborhoods(self, cities: List[str], constraints: TravelConstraints) -> Dict[str, List[str]]:
        """Use LLM to get best neighborhoods for each city."""
        system_prompt = """You are a travel accommodation expert. For each city, suggest the 3 best neighborhoods to stay in for a tourist.

Respond with valid JSON:
{
  "neighborhoods": {
    "CityName": ["Neighborhood1", "Neighborhood2", "Neighborhood3"]
  }
}

Rules:
- Use REAL neighborhood/district names
- Pick areas that are safe, well-connected, and close to attractions
- Consider the traveler's budget and preferences"""

        user_prompt = f"""Suggest 3 best neighborhoods to stay in for each city:
Cities: {', '.join(cities)}
Preferences: {', '.join(constraints.preferences) if constraints.preferences else 'general sightseeing'}
Budget: {constraints.budget_total} {constraints.currency} for {constraints.duration_days} days"""

        content = await self.llm_client.chat_with_retry(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=500,
            response_format={"type": "json_object"}
        )

        data = json.loads(content)
        return data.get("neighborhoods", {})

    async def _create_movement_plans(self, cities: List[str], constraints: TravelConstraints) -> List[MovementPlan]:
        """Create inter-city movement plans."""
        if len(cities) < 2:
            return []

        if self.llm_client:
            try:
                return await self._llm_generate_movements(cities, constraints)
            except Exception as e:
                print(f"LLM movement planning failed: {e}")

        movements = []
        trace_id = getattr(constraints, 'trace_id', None)

        for i in range(len(cities) - 1):
            from_city = cities[i]
            to_city = cities[i + 1]

            if self.tool_router:
                try:
                    geo_result = await self.tool_router.geo_estimate(
                        from_location=from_city, to_location=to_city, trace_id=trace_id
                    )
                    movement = MovementPlan(
                        from_city=from_city, to_city=to_city,
                        mode=geo_result.get("mode", "transit"),
                        duration_hours=geo_result.get("duration_minutes", 120) / 60,
                        cost_band=CostBand.MODERATE,
                        booking_notes=geo_result.get("notes", "")
                    )
                    movements.append(movement)
                except Exception:
                    movements.append(self._create_fallback_movement(from_city, to_city))
            else:
                movements.append(self._create_fallback_movement(from_city, to_city))

        return movements

    async def _llm_generate_movements(self, cities: List[str], constraints: TravelConstraints) -> List[MovementPlan]:
        """Use LLM to plan inter-city transport with real options."""
        pairs = [f"{cities[i]} to {cities[i+1]}" for i in range(len(cities) - 1)]

        system_prompt = """You are a travel logistics expert. For each city pair, suggest the best transport option.

Respond with valid JSON:
{
  "movements": [
    {
      "from_city": "City A",
      "to_city": "City B",
      "mode": "train|bus|flight|drive|ferry",
      "duration_hours": number,
      "booking_notes": "Specific transport name or tip (e.g., 'Shinkansen Nozomi, book at JR station')"
    }
  ]
}

Rules:
- Use real transport options (train names, airline routes, highway names)
- Duration should be realistic
- Consider budget when suggesting options"""

        user_prompt = f"""Plan transport for these segments:
{chr(10).join(f'- {p}' for p in pairs)}
Trip type: {"road trip (driving)" if constraints.is_road_trip else "multi-city"}
Budget: {constraints.budget_total} {constraints.currency}"""

        content = await self.llm_client.chat_with_retry(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=600,
            response_format={"type": "json_object"}
        )

        data = json.loads(content)
        movements = []
        for m in data.get("movements", []):
            movements.append(MovementPlan(
                from_city=m["from_city"],
                to_city=m["to_city"],
                mode=m.get("mode", "transit"),
                duration_hours=float(m.get("duration_hours", 2.0)),
                cost_band=CostBand.MODERATE,
                booking_notes=m.get("booking_notes", "")
            ))
        return movements

    def _create_fallback_movement(self, from_city: str, to_city: str) -> MovementPlan:
        return MovementPlan(
            from_city=from_city, to_city=to_city,
            mode="transit", duration_hours=2.0, cost_band=CostBand.MODERATE,
            booking_notes="Check local transit options"
        )

    def _build_day_skeletons(self, night_allocation: Dict[str, int], lodging_plans: List[LodgingPlan],
                              movement_plans: List[MovementPlan], constraints: TravelConstraints,
                              activity_catalog: Optional[any] = None) -> List[DaySkeleton]:
        """Create day-by-day structure with travel time buffers."""
        skeletons = []
        cities = constraints.cities
        if not cities:
            return skeletons

        current_day = 1
        current_city_idx = 0
        city_day_counter: Dict[str, int] = {}

        while current_day <= constraints.duration_days and current_city_idx < len(cities):
            city = cities[current_city_idx]
            nights_in_city = night_allocation.get(city, 1)

            is_travel_day = False
            travel_buffer_minutes = 0

            if current_city_idx < len(cities) - 1:
                days_remaining = sum(night_allocation.get(cities[i], 1) for i in range(current_city_idx, len(cities)))
                if current_day == constraints.duration_days - days_remaining + nights_in_city:
                    is_travel_day = True
                    if current_city_idx < len(movement_plans):
                        travel_buffer_minutes = int(movement_plans[current_city_idx].duration_hours * 60) + 60

            travel_hours = travel_buffer_minutes / 60
            if is_travel_day:
                next_city = cities[current_city_idx + 1] if current_city_idx + 1 < len(cities) else "next"
                slots = [
                    DaySlot(slot_index=0, start_time="09:00", end_time="10:00",
                            activity_type="checkout", city=city,
                            notes=f"Check out and travel to {next_city}"),
                    DaySlot(slot_index=1, start_time="10:00", end_time=f"{10 + int(travel_hours):02d}:00",
                            activity_type="travel", city=city, notes="Inter-city travel"),
                    DaySlot(slot_index=2, start_time=f"{10 + int(travel_hours):02d}:00",
                            end_time=f"{11 + int(travel_hours):02d}:00",
                            activity_type="checkin", city=cities[current_city_idx + 1],
                            notes=f"Arrive and check in to {cities[current_city_idx + 1]}")
                ]
            else:
                day_idx = city_day_counter.get(city, 0)
                slots = self._generate_day_slots(city, constraints, activity_catalog, day_in_city=day_idx)
                city_day_counter[city] = day_idx + 1

            skeleton = DaySkeleton(
                day_number=current_day, city=city, slots=slots,
                total_travel_time_hours=travel_hours,
                pacing_notes=f"Day in {city}" if not is_travel_day else f"Travel day: {city} -> {cities[current_city_idx + 1] if current_city_idx + 1 < len(cities) else 'next'}"
            )
            skeletons.append(skeleton)

            if is_travel_day or (not is_travel_day and current_day >= sum(night_allocation.get(cities[i], 1) for i in range(current_city_idx + 1))):
                current_city_idx += 1

            current_day += 1

        return skeletons

    def _generate_day_slots(self, city: str, constraints: TravelConstraints,
                             activity_catalog: Optional[any] = None,
                             day_in_city: int = 0) -> List[DaySlot]:
        """Generate day slots with activity descriptions, rotating activities across days."""
        city_activities = []
        if activity_catalog and hasattr(activity_catalog, 'activities'):
            city_activities = [a for a in activity_catalog.activities if a.city == city]

        prefs = [p.lower() for p in constraints.preferences] if constraints.preferences else []
        avoids = [a.lower() for a in constraints.avoidances] if constraints.avoidances else []
        crowd_avoid = any("crowd" in a for a in avoids)

        offset = day_in_city * 2
        available = city_activities[offset:] + city_activities[:offset] if city_activities else []
        picks = available[:2] if available else []

        if picks:
            morning_note = f"Visit {picks[0].name} in {city}."
            if crowd_avoid:
                morning_note += " Arrive early to avoid crowds."
        else:
            morning_note = f"Explore {city}'s landmarks and cultural sites."

        food_activities = [a for a in available if a.type.value == "food"]
        food_pick = food_activities[day_in_city % max(1, len(food_activities))] if food_activities else None
        if food_pick:
            lunch_note = f"Lunch at {food_pick.name} in {city}."
        elif any("food" in p or "eat" in p or "cuisine" in p for p in prefs):
            lunch_note = f"Enjoy authentic {city} cuisine at a local restaurant."
        else:
            lunch_note = f"Lunch at a nearby restaurant."

        if len(picks) > 1:
            afternoon_note = f"Visit {picks[1].name} in {city}."
        else:
            afternoon_note = f"Explore more of {city}'s attractions and neighborhoods."

        dinner_note = f"Dinner and evening in {city}."

        return [
            DaySlot(slot_index=0, start_time="09:00", end_time="12:00",
                    activity_type="morning", city=city, notes=morning_note),
            DaySlot(slot_index=1, start_time="12:00", end_time="13:30",
                    activity_type="lunch", city=city, notes=lunch_note),
            DaySlot(slot_index=2, start_time="14:00", end_time="17:00",
                    activity_type="afternoon", city=city, notes=afternoon_note),
            DaySlot(slot_index=3, start_time="18:00", end_time="20:00",
                    activity_type="dinner", city=city, notes=dinner_note)
        ]

    async def _generate_route_description(self, constraints: TravelConstraints) -> str:
        """Use LLM to generate route description for road trips."""
        if self.llm_client:
            try:
                content = await self.llm_client.chat_with_retry(
                    messages=[
                        {"role": "system", "content": "Write a one-paragraph route overview for a road trip. Be specific about roads, regions, and key stops. Under 150 words."},
                        {"role": "user", "content": f"Road trip through {constraints.destination_region}, {constraints.duration_days} days, cities: {', '.join(constraints.cities)}"}
                    ],
                    max_tokens=300
                )
                return content.strip()
            except Exception:
                pass
        return f"A {constraints.duration_days}-day road trip through {constraints.destination_region}."

    def _generate_summary(self, movement_plans: List[MovementPlan]) -> str:
        if not movement_plans:
            return "Single city stay - no inter-city travel"
        parts = [f"{m.from_city} → {m.to_city} ({m.mode}, {m.duration_hours}h)" for m in movement_plans]
        return " | ".join(parts)
