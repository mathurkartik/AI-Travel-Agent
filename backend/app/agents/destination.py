"""
Destination Research Agent - Phase 4a.
Finds best places, experiences, and food based on traveler preferences.
Uses LLM to generate specific, real activities for any destination worldwide.
"""

from typing import List, Optional, Dict
import json

from ..models import (
    TravelConstraints, ActivityCatalog, Activity, ActivityType,
    CrowdLevel, CostBand
)


class DestinationAgent:
    """
    Researches destinations and curates activity catalogs.
    Uses LLM knowledge to generate real, specific activities for any city.
    """

    def __init__(self, tool_router=None, llm_client=None):
        self.tool_router = tool_router
        self.llm_client = llm_client

    async def research(self, constraints: TravelConstraints) -> ActivityCatalog:
        """Generate ActivityCatalog from constraints using LLM."""
        per_city_catalogs: Dict[str, List[str]] = {}
        all_activities: List[Activity] = []

        for city in constraints.cities:
            city_activities = await self._research_city(city=city, constraints=constraints)
            per_city_catalogs[city] = [a.id for a in city_activities]
            all_activities.extend(city_activities)

        return ActivityCatalog(
            activities=all_activities,
            per_city=per_city_catalogs,
            neighborhood_notes=self._create_neighborhood_notes(all_activities)
        )

    async def _research_city(self, city: str, constraints: TravelConstraints) -> List[Activity]:
        """Research activities for a specific city, LLM-first."""
        if self.llm_client:
            try:
                activities = await self._llm_generate_activities(city, constraints)
                if activities:
                    return activities
            except Exception as e:
                print(f"LLM activity generation failed for {city}: {e}")

        return self._generate_generic_activities(city, constraints)

    async def _llm_generate_activities(self, city: str, constraints: TravelConstraints) -> List[Activity]:
        """Use LLM to generate specific activity names with details."""
        system_prompt = f"""You are a travel expert for {city}. Generate specific, real activities based on traveler preferences.

Respond with valid JSON object with an "activities" key containing an array. Each activity:
{{
  "name": "Specific real place name (e.g., 'Senso-ji Temple', not 'Morning activity')",
  "type": "temple|food|museum|nature|shopping|entertainment|transport|other",
  "estimated_duration_hours": number (0.5-4.0),
  "crowd_level": "low|medium|high",
  "cost_band": "budget|moderate|expensive|luxury",
  "must_do": boolean,
  "rationale": "Brief reason (under 100 chars)",
  "best_time": "When to visit",
  "address": "Area name",
  "tags": ["1-2 keywords"]
}}

Rules:
- Use REAL, specific place names only
- Include crowd avoidance timing if user hates crowds
- Suggest specific neighborhoods for food/activities
- Duration should be realistic (minimum 0.5 hours)
- Generate exactly 4-5 activities (keep it concise)"""

        user_prompt = f"""Generate specific activities for {city} based on:
- Preferences: {', '.join(constraints.preferences) if constraints.preferences else 'general sightseeing'}
- Avoidances: {', '.join(constraints.avoidances) if constraints.avoidances else 'none'}
- Duration: {constraints.duration_days} days total trip
- Budget: {constraints.budget_total} {constraints.currency}

Include variety: landmarks, food spots, cultural sites, nature, neighborhoods."""

        content = await self.llm_client.chat_with_retry(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=900,
            response_format={"type": "json_object"}
        )

        data = json.loads(content)

        if isinstance(data, dict) and "activities" in data:
            activities_data = data["activities"]
        elif isinstance(data, list):
            activities_data = data
        else:
            activities_data = []

        type_mapping = {
            "temple": ActivityType.TEMPLE, "food": ActivityType.FOOD,
            "museum": ActivityType.MUSEUM, "nature": ActivityType.NATURE,
            "shopping": ActivityType.SHOPPING, "entertainment": ActivityType.ENTERTAINMENT,
            "transport": ActivityType.TRANSPORT, "other": ActivityType.OTHER
        }
        crowd_mapping = {"low": CrowdLevel.LOW, "medium": CrowdLevel.MEDIUM, "high": CrowdLevel.HIGH}
        cost_mapping = {
            "budget": CostBand.BUDGET, "moderate": CostBand.MODERATE,
            "expensive": CostBand.EXPENSIVE, "luxury": CostBand.LUXURY
        }

        activities = []
        for i, item in enumerate(activities_data):
            name = str(item.get("name", ""))[:100]
            rationale = str(item.get("rationale", ""))[:200]
            best_time = str(item.get("best_time", ""))[:50]
            address = str(item.get("address", ""))[:100]

            name_part = name.lower().replace(' ', '-').replace("'", '').replace('"', '').replace('(', '').replace(')', '').replace('&', 'and').replace(',', '')[:30]
            activity_id = f"{city.lower().replace(' ', '-')}-{name_part}-{i}"

            activity = Activity(
                id=activity_id,
                name=name,
                city=city,
                type=type_mapping.get(item.get("type"), ActivityType.OTHER),
                estimated_duration_hours=max(0.5, float(item.get("estimated_duration_hours", 2.0))),
                cost_band=cost_mapping.get(item.get("cost_band"), CostBand.MODERATE),
                crowd_level=crowd_mapping.get(item.get("crowd_level"), CrowdLevel.MEDIUM),
                must_do=bool(item.get("must_do", False)),
                rationale=rationale,
                address=address,
                best_time=best_time,
                tags=item.get("tags", [])[:5]
            )
            activities.append(activity)

        if constraints.avoidances:
            activities = self._filter_avoidances(activities, constraints.avoidances)

        return activities

    def _generate_generic_activities(self, city: str, constraints: TravelConstraints) -> List[Activity]:
        """Minimal generic fallback when LLM is unavailable."""
        city_clean = city.lower().replace(' ', '-')

        activities = [
            Activity(id=f"{city_clean}-landmark-0", name=f"{city} Main Landmark", city=city,
                     type=ActivityType.OTHER, estimated_duration_hours=2.5, cost_band=CostBand.MODERATE,
                     crowd_level=CrowdLevel.HIGH, must_do=True,
                     rationale=f"Top-rated attraction in {city}", tags=["sightseeing", "iconic"],
                     address=f"Central {city}"),
            Activity(id=f"{city_clean}-food-1", name=f"{city} Local Food Experience", city=city,
                     type=ActivityType.FOOD, estimated_duration_hours=2.0, cost_band=CostBand.MODERATE,
                     crowd_level=CrowdLevel.MEDIUM, must_do=True,
                     rationale=f"Authentic local cuisine in {city}", tags=["food", "local"],
                     address=f"Old Town, {city}"),
            Activity(id=f"{city_clean}-culture-2", name=f"{city} Cultural Site", city=city,
                     type=ActivityType.MUSEUM, estimated_duration_hours=2.0, cost_band=CostBand.MODERATE,
                     crowd_level=CrowdLevel.MEDIUM, must_do=False,
                     rationale=f"Cultural heritage of {city}", tags=["culture", "history"],
                     address=f"Museum District, {city}"),
            Activity(id=f"{city_clean}-nature-3", name=f"{city} Park or Garden", city=city,
                     type=ActivityType.NATURE, estimated_duration_hours=1.5, cost_band=CostBand.BUDGET,
                     crowd_level=CrowdLevel.LOW, must_do=False,
                     rationale=f"Green space in {city}", tags=["nature", "relaxing"],
                     address=f"City Park, {city}"),
        ]

        if constraints.avoidances:
            activities = self._filter_avoidances(activities, constraints.avoidances)

        return activities

    def _filter_avoidances(self, activities: List[Activity], avoidances: List[str]) -> List[Activity]:
        """Filter out activities matching avoidances."""
        filtered = []
        for activity in activities:
            should_include = True
            for avoidance in avoidances:
                avoidance_lower = avoidance.lower()
                if any(avoidance_lower in tag.lower() for tag in activity.tags):
                    should_include = False
                    break
                if avoidance_lower in ["crowd", "crowds"] and activity.crowd_level == CrowdLevel.HIGH:
                    should_include = False
                    break
            if should_include:
                filtered.append(activity)
        return filtered

    def _create_neighborhood_notes(self, activities: List[Activity]) -> Dict[str, str]:
        """Create neighborhood notes from activity addresses."""
        notes = {}
        for activity in activities:
            if activity.address:
                parts = activity.address.split(",")
                if len(parts) >= 2:
                    ward = parts[-2].strip() if len(parts) > 2 else parts[-1].strip()
                    if ward not in notes:
                        notes[ward] = f"Area with {activity.type.value} attractions"
        return notes
