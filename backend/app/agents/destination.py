"""
Destination Research Agent - Phase 4a.
Finds best places, experiences, and food based on traveler preferences.
"""

from typing import List, Optional, Dict
import asyncio

from ..models import (
    TravelConstraints, ActivityCatalog, Activity, ActivityType, 
    CrowdLevel, CostBand
)


class DestinationAgent:
    """
    Researches destinations and curates activity catalogs.
    
    Inputs: TravelConstraints + optional ToolRouter.search
    Output: ActivityCatalog
    
    Responsibilities:
    - Recommend neighborhoods, temples, food streets
    - Suggest less-crowded options where possible
    - Identify "must-do" vs "nice-to-have" items
    """
    
    def __init__(self, tool_router=None, llm_client=None):
        self.tool_router = tool_router
        self.llm_client = llm_client
    
    async def research(self, constraints: TravelConstraints) -> ActivityCatalog:
        """
        Phase 4a: Generate ActivityCatalog from constraints.
        
        Uses ToolRouter.search for destination research and structures
        results into ActivityCatalog format.
        
        **Phase 4a**: Uses static ToolRouter data (no LLM calls).
        **Phase 8**: Could add LLM for richer descriptions and rationale.
        
        Args:
            constraints: TravelConstraints with cities, preferences, avoidances
            
        Returns:
            ActivityCatalog with activities per city
        """
        per_city_catalogs: Dict[str, List[str]] = {}
        all_activities: List[Activity] = []
        
        for city in constraints.cities:
            # Research activities for this city
            city_activities = await self._research_city(
                city=city,
                constraints=constraints
            )
            
            per_city_catalogs[city] = [a.id for a in city_activities]
            all_activities.extend(city_activities)
        
        # Create consolidated catalog
        catalog = ActivityCatalog(
            activities=all_activities,
            per_city=per_city_catalogs,
            neighborhood_notes=self._create_neighborhood_notes(all_activities)
        )
        
        return catalog
    
    async def _research_city(
        self,
        city: str,
        constraints: TravelConstraints
    ) -> List[Activity]:
        """
        Research activities for a specific city using LLM for specific names.
        
        Uses LLM to generate specific, detailed activity names instead of generic labels.
        """
        # Try LLM first for specific activity names
        if self.llm_client:
            try:
                print(f"Attempting LLM activity generation for {city}...")
                activities = await self._llm_generate_activities(city, constraints)
                print(f"LLM generated {len(activities)} activities for {city}")
                if activities:
                    return activities
            except Exception as e:
                print(f"LLM activity generation failed: {e}")
                import traceback
                traceback.print_exc()
        
        # Fallback to static data
        print(f"Using static data for {city}")
        return self._get_static_activities_for_city(city, constraints)
    
    async def _llm_generate_activities(
        self,
        city: str,
        constraints: TravelConstraints
    ) -> List[Activity]:
        """Use LLM to generate specific activity names with details."""
        import json
        
        system_prompt = f"""You are a travel expert for {city}. Generate specific, real activities based on traveler preferences.

Respond with valid JSON array of activities, each with:
{{
  "name": "Specific activity name (e.g., 'Senso-ji Temple', not 'Morning activity')",
  "type": "temple|food|museum|nature|shopping|entertainment|transport|other",
  "estimated_duration_hours": number (0.5-4.0),
  "crowd_level": "low|medium|high",
  "cost_band": "budget|moderate|expensive|luxury",
  "must_do": boolean (true if essential for this destination),
  "rationale": "Why this activity matches preferences",
  "best_time": "Specific timing (e.g., 'Before 8 AM to avoid crowds')",
  "address": "Location or area",
  "tags": ["relevant", "keywords"]
}}

Rules:
- Use REAL, specific place names (no generic labels)
- Include crowd avoidance timing if user hates crowds
- Suggest specific neighborhoods for food/activities
- Duration should be realistic (not just 1 hour for everything)
- Include best time to visit (especially for crowd avoidance)
- Keep descriptions concise (under 200 chars)"""

        user_prompt = f"""Generate 15-20 specific activities for {city} based on:
- Preferences: {', '.join(constraints.preferences)}
- Avoidances: {', '.join(constraints.avoidances)}
- Duration: {constraints.duration_days} days total
- Budget: ${constraints.budget_total} {constraints.currency}

Focus on:
1. Specific temple/shrine names (not just "visit a temple")
2. Specific food streets or restaurant types
3. Specific neighborhoods to explore
4. Crowd avoidance timing if relevant
5. Practical tips embedded in rationale/best_time
6. Include variety: different temples, different food areas, different neighborhoods"""

        try:
            # Use direct LLM call with JSON response format (synchronous)
            response = self.llm_client._client.chat.completions.create(
                model=self.llm_client.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.llm_client.temperature,
                max_tokens=3000,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            data = json.loads(content)
            
            # Handle both array and wrapped object formats
            if isinstance(data, dict) and "activities" in data:
                activities_data = data["activities"]
            elif isinstance(data, list):
                activities_data = data
            else:
                activities_data = []
            
            activities = []
            for i, item in enumerate(activities_data):
                # Truncate long strings to match model constraints
                name = str(item.get("name", ""))[:100]
                rationale = str(item.get("rationale", ""))[:200]
                best_time = str(item.get("best_time", ""))[:50]  # Activity.best_time max 50
                address = str(item.get("address", ""))[:100]
                
                # Sanitize activity ID: remove spaces, apostrophes, quotes, and special chars
                name_part = name.lower().replace(' ', '-').replace("'", '').replace('"', '').replace('(', '').replace(')', '').replace('&', 'and').replace(',', '')[:30]
                activity_id = f"{city.lower().replace(' ', '-')}-{name_part}-{i}"
                
                # Map string types to enum
                type_mapping = {
                    "temple": ActivityType.TEMPLE,
                    "food": ActivityType.FOOD,
                    "museum": ActivityType.MUSEUM,
                    "nature": ActivityType.NATURE,
                    "shopping": ActivityType.SHOPPING,
                    "entertainment": ActivityType.ENTERTAINMENT,
                    "transport": ActivityType.TRANSPORT,
                    "other": ActivityType.OTHER
                }
                
                from ..models import CrowdLevel, CostBand
                crowd_mapping = {
                    "low": CrowdLevel.LOW,
                    "medium": CrowdLevel.MEDIUM,
                    "high": CrowdLevel.HIGH
                }
                cost_mapping = {
                    "budget": CostBand.BUDGET,
                    "moderate": CostBand.MODERATE,
                    "expensive": CostBand.EXPENSIVE,
                    "luxury": CostBand.LUXURY
                }
                
                activity = Activity(
                    id=activity_id,
                    name=name,
                    city=city,
                    type=type_mapping.get(item.get("type"), ActivityType.OTHER),
                    estimated_duration_hours=float(item.get("estimated_duration_hours", 2.0)),
                    cost_band=cost_mapping.get(item.get("cost_band"), CostBand.MODERATE),
                    crowd_level=crowd_mapping.get(item.get("crowd_level"), CrowdLevel.MEDIUM),
                    must_do=bool(item.get("must_do", False)),
                    rationale=rationale,
                    address=address,
                    best_time=best_time,
                    tags=item.get("tags", [])[:5]
                )
                activities.append(activity)
            
            return activities
            
        except Exception as e:
            print(f"LLM activity generation error: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _build_search_queries(self, city: str, preferences: List[str]) -> List[str]:
        """Build search queries based on preferences."""
        queries = []
        
        # Default queries for any city
        queries.append(f"best things to do in {city}")
        
        # Preference-specific queries
        for pref in preferences:
            pref_lower = pref.lower()
            if any(word in pref_lower for word in ["temple", "shrine", "history", "culture"]):
                queries.append(f"temples and shrines in {city}")
            if any(word in pref_lower for word in ["food", "eat", "restaurant", "cuisine"]):
                queries.append(f"best food in {city}")
                queries.append(f"restaurants in {city}")
            if any(word in pref_lower for word in ["nature", "park", "outdoor", "hike"]):
                queries.append(f"parks and nature in {city}")
            if any(word in pref_lower for word in ["art", "museum", "gallery"]):
                queries.append(f"museums in {city}")
        
        return queries
    
    def _search_result_to_activity(
        self,
        result: dict,
        city: str,
        preferences: List[str],
        avoidances: List[str]
    ) -> Optional[Activity]:
        """Convert a search result to an Activity object."""
        title = result.get("title", "")
        snippet = result.get("snippet", "")
        
        # Generate a stable ID (sanitized - no spaces or special chars)
        title_part = title.lower().replace(' ', '-').replace("'", '').replace('"', '').replace('(', '').replace(')', '').replace('&', 'and').replace(',', '')[:30]
        activity_id = f"{city.lower().replace(' ', '-')}-{title_part}"
        
        # Determine activity type based on keywords
        activity_type = self._determine_activity_type(title + " " + snippet)
        
        # Determine crowd level (Phase 4a: static assignment)
        crowd_level = self._estimate_crowd_level(title + " " + snippet, avoidances)
        
        # Determine cost band
        cost_band = self._estimate_cost_band(title + " " + snippet)
        
        # Determine if must-do based on preferences alignment
        is_must_do = self._is_must_do_activity(title + " " + snippet, preferences)
        
        # Estimate duration based on activity type
        duration = self._estimate_duration(activity_type)
        
        return Activity(
            id=activity_id,
            name=title,
            city=city,
            type=activity_type,
            estimated_duration_hours=duration,
            cost_band=cost_band,
            crowd_level=crowd_level,
            must_do=is_must_do,
            rationale=f"Matched to preferences: {', '.join(preferences[:2])}" if preferences else "Popular attraction",
            tags=self._extract_tags(title + " " + snippet, preferences),
            address=result.get("url", "")  # Using URL as placeholder
        )
    
    def _get_static_activities_for_city(
        self,
        city: str,
        constraints: TravelConstraints
    ) -> List[Activity]:
        """Return static activities when ToolRouter is not available."""
        city_lower = city.lower()
        activities = []
        
        # Japan cities
        if city_lower == "tokyo":
            activities = [
                Activity(
                    id="tokyo-sensoji-temple",
                    name="Senso-ji Temple",
                    city="Tokyo",
                    type=ActivityType.TEMPLE,
                    estimated_duration_hours=2.0,
                    cost_band=CostBand.BUDGET,
                    crowd_level=CrowdLevel.HIGH,
                    must_do=True,
                    rationale="Tokyo's oldest temple, iconic red lantern",
                    tags=["temple", "history", "asakusa", "must-do"],
                    address="2-3-1 Asakusa, Taito City, Tokyo"
                ),
                Activity(
                    id="tokyo-team-borderless",
                    name="TeamLab Borderless",
                    city="Tokyo",
                    type=ActivityType.MUSEUM,
                    estimated_duration_hours=3.0,
                    cost_band=CostBand.EXPENSIVE,
                    crowd_level=CrowdLevel.HIGH,
                    must_do=True,
                    rationale="Digital art museum, immersive experience",
                    tags=["art", "digital", "immersive", "popular"],
                    address="Odaiba, Tokyo"
                ),
                Activity(
                    id="tokyo-meiji-shrine",
                    name="Meiji Shrine",
                    city="Tokyo",
                    type=ActivityType.TEMPLE,
                    estimated_duration_hours=1.5,
                    cost_band=CostBand.BUDGET,
                    crowd_level=CrowdLevel.MEDIUM,
                    must_do=False,
                    rationale="Peaceful shrine in forest setting",
                    tags=["shrine", "nature", "peaceful"],
                    address="1-1 Yoyogi Kamizonocho, Shibuya"
                ),
                Activity(
                    id="tokyo-tsukiji-food",
                    name="Tsukiji Outer Market",
                    city="Tokyo",
                    type=ActivityType.FOOD,
                    estimated_duration_hours=2.0,
                    cost_band=CostBand.MODERATE,
                    crowd_level=CrowdLevel.HIGH,
                    must_do=True,
                    rationale="Fresh sushi and street food",
                    tags=["food", "sushi", "market", "street food"],
                    address="Tsukiji, Chuo City, Tokyo"
                ),
            ]
        elif city_lower == "kyoto":
            activities = [
                Activity(
                    id="kyoto-kinkakuji",
                    name="Kinkaku-ji (Golden Pavilion)",
                    city="Kyoto",
                    type=ActivityType.TEMPLE,
                    estimated_duration_hours=1.5,
                    cost_band=CostBand.BUDGET,
                    crowd_level=CrowdLevel.HIGH,
                    must_do=True,
                    rationale="Iconic Zen temple covered in gold leaf",
                    tags=["temple", "zen", "gold", "iconic", "must-do"],
                    address="1 Kinkakujicho, Kita Ward, Kyoto"
                ),
                Activity(
                    id="kyoto-fushimi",
                    name="Fushimi Inari Shrine",
                    city="Kyoto",
                    type=ActivityType.TEMPLE,
                    estimated_duration_hours=2.5,
                    cost_band=CostBand.BUDGET,
                    crowd_level=CrowdLevel.HIGH,
                    must_do=True,
                    rationale="Famous thousands of vermillion torii gates",
                    tags=["shrine", "torii", "hiking", "iconic", "must-do"],
                    address="68 Fukakusa Yabunouchicho, Fushimi Ward"
                ),
                Activity(
                    id="kyoto-kiyomizu",
                    name="Kiyomizu-dera",
                    city="Kyoto",
                    type=ActivityType.TEMPLE,
                    estimated_duration_hours=2.0,
                    cost_band=CostBand.MODERATE,
                    crowd_level=CrowdLevel.HIGH,
                    must_do=True,
                    rationale="Historic wooden temple with city views",
                    tags=["temple", "views", "historic", "must-do"],
                    address="1-294 Kiyomizu, Higashiyama Ward"
                ),
                Activity(
                    id="kyoto-arashiyama",
                    name="Arashiyama Bamboo Grove",
                    city="Kyoto",
                    type=ActivityType.NATURE,
                    estimated_duration_hours=2.0,
                    cost_band=CostBand.BUDGET,
                    crowd_level=CrowdLevel.MEDIUM,
                    must_do=False,
                    rationale="Beautiful bamboo forest walk",
                    tags=["nature", "bamboo", "walking", "peaceful"],
                    address="Arashiyama, Ukyo Ward, Kyoto"
                ),
            ]
        elif city_lower == "osaka":
            activities = [
                Activity(
                    id="osaka-castle",
                    name="Osaka Castle",
                    city="Osaka",
                    type=ActivityType.TEMPLE,
                    estimated_duration_hours=2.0,
                    cost_band=CostBand.MODERATE,
                    crowd_level=CrowdLevel.MEDIUM,
                    must_do=True,
                    rationale="Historic castle with museum and park",
                    tags=["castle", "history", "museum", "park"],
                    address="1-1 Osakajo, Chuo Ward, Osaka"
                ),
                Activity(
                    id="osaka-dotonbori",
                    name="Dotonbori District",
                    city="Osaka",
                    type=ActivityType.FOOD,
                    estimated_duration_hours=3.0,
                    cost_band=CostBand.MODERATE,
                    crowd_level=CrowdLevel.HIGH,
                    must_do=True,
                    rationale="Famous food street with neon lights",
                    tags=["food", "nightlife", "neon", "street food"],
                    address="Dotonbori, Chuo Ward, Osaka"
                ),
            ]
        
        # If no specific city data, generate generic activities
        if not activities:
            activities = self._generate_generic_activities(city, constraints)
        
        # Filter by avoidances
        if constraints.avoidances:
            activities = self._filter_avoidances(activities, constraints.avoidances)
        
        return activities
    
    def _generate_generic_activities(
        self,
        city: str,
        constraints: TravelConstraints
    ) -> List[Activity]:
        """Generate generic activities for any city when no specific data exists."""
        city_clean = city.lower().replace(' ', '-')
        return [
            Activity(
                id=f"{city_clean}-city-center",
                name=f"Explore {city} City Center",
                city=city,
                type=ActivityType.OTHER,
                estimated_duration_hours=3.0,
                cost_band=CostBand.BUDGET,
                crowd_level=CrowdLevel.MEDIUM,
                must_do=True,
                rationale=f"Central area with main attractions and landmarks in {city}",
                tags=["sightseeing", "walking", "downtown"],
                address=f"City Center, {city}"
            ),
            Activity(
                id=f"{city_clean}-local-food",
                name=f"Try Local Cuisine in {city}",
                city=city,
                type=ActivityType.FOOD,
                estimated_duration_hours=2.0,
                cost_band=CostBand.MODERATE,
                crowd_level=CrowdLevel.MEDIUM,
                must_do=True,
                rationale=f"Experience authentic local food and dining scene",
                tags=["food", "local", "dining"],
                address=f"Downtown {city}"
            ),
            Activity(
                id=f"{city_clean}-main-park",
                name=f"Visit {city} Main Park/Garden",
                city=city,
                type=ActivityType.NATURE,
                estimated_duration_hours=2.0,
                cost_band=CostBand.BUDGET,
                crowd_level=CrowdLevel.LOW,
                must_do=False,
                rationale="Relax in green space and enjoy outdoor atmosphere",
                tags=["nature", "park", "relaxing"],
                address=f"Central Park, {city}"
            ),
            Activity(
                id=f"{city_clean}-museum",
                name=f"{city} Museum or Gallery",
                city=city,
                type=ActivityType.MUSEUM,
                estimated_duration_hours=2.5,
                cost_band=CostBand.MODERATE,
                crowd_level=CrowdLevel.MEDIUM,
                must_do=False,
                rationale="Learn about local history, art, and culture",
                tags=["museum", "culture", "history"],
                address=f"Museum District, {city}"
            ),
            Activity(
                id=f"{city_clean}-shopping",
                name=f"Shopping in {city}",
                city=city,
                type=ActivityType.SHOPPING,
                estimated_duration_hours=3.0,
                cost_band=CostBand.MODERATE,
                crowd_level=CrowdLevel.MEDIUM,
                must_do=False,
                rationale="Explore local shops, markets, and boutiques",
                tags=["shopping", "markets", "souvenirs"],
                address=f"Main Shopping Area, {city}"
            ),
            Activity(
                id=f"{city_clean}-nightlife",
                name=f"{city} Nightlife Experience",
                city=city,
                type=ActivityType.ENTERTAINMENT,
                estimated_duration_hours=3.0,
                cost_band=CostBand.MODERATE,
                crowd_level=CrowdLevel.HIGH,
                must_do=False,
                rationale="Experience evening entertainment and local nightlife",
                tags=["nightlife", "entertainment", "evening"],
                address=f"Entertainment District, {city}"
            ),
        ]
    
    def _filter_avoidances(
        self,
        activities: List[Activity],
        avoidances: List[str]
    ) -> List[Activity]:
        """Filter out activities matching avoidances."""
        filtered = []
        for activity in activities:
            should_include = True
            for avoidance in avoidances:
                avoidance_lower = avoidance.lower()
                # Check tags
                if any(avoidance_lower in tag.lower() for tag in activity.tags):
                    should_include = False
                    break
                # Check crowd level
                if avoidance_lower in ["crowd", "crowds"] and activity.crowd_level == CrowdLevel.HIGH:
                    should_include = False
                    break
            if should_include:
                filtered.append(activity)
        return filtered
    
    def _determine_activity_type(self, text: str) -> ActivityType:
        """Determine activity type from keywords."""
        text_lower = text.lower()
        if any(word in text_lower for word in ["temple", "shrine", "castle", "historic", "museum"]):
            return ActivityType.TEMPLE
        if any(word in text_lower for word in ["food", "restaurant", "market", "eat", "cuisine", "sushi"]):
            return ActivityType.FOOD
        if any(word in text_lower for word in ["art", "gallery", "digital", "immersive", "museum"]):
            return ActivityType.MUSEUM
        if any(word in text_lower for word in ["park", "nature", "bamboo", "garden", "hike"]):
            return ActivityType.NATURE
        if any(word in text_lower for word in ["shop", "mall", "market", "buy"]):
            return ActivityType.SHOPPING
        return ActivityType.OTHER
    
    def _estimate_crowd_level(self, text: str, avoidances: List[str]) -> CrowdLevel:
        """Estimate crowd level from keywords."""
        text_lower = text.lower()
        if any(word in text_lower for word in ["popular", "famous", "iconic", "must-see"]):
            return CrowdLevel.HIGH
        if any(word in text_lower for word in ["peaceful", "quiet", "hidden", "secret", "local"]):
            return CrowdLevel.LOW
        return CrowdLevel.MEDIUM
    
    def _estimate_cost_band(self, text: str) -> CostBand:
        """Estimate cost band from keywords."""
        text_lower = text.lower()
        if any(word in text_lower for word in ["free", "temple", "shrine", "park", "garden"]):
            return CostBand.BUDGET
        if any(word in text_lower for word in ["luxury", "michelin", "exclusive", "private"]):
            return CostBand.LUXURY
        if any(word in text_lower for word in ["expensive", "premium", "high-end"]):
            return CostBand.EXPENSIVE
        return CostBand.MODERATE
    
    def _estimate_duration(self, activity_type: ActivityType) -> float:
        """Estimate duration based on activity type."""
        durations = {
            ActivityType.TEMPLE: 2.0,
            ActivityType.FOOD: 2.0,
            ActivityType.MUSEUM: 2.5,
            ActivityType.NATURE: 2.0,
            ActivityType.SHOPPING: 3.0,
            ActivityType.OTHER: 1.5,
        }
        return durations.get(activity_type, 1.5)
    
    def _is_must_do_activity(self, text: str, preferences: List[str]) -> bool:
        """Determine if this is a must-do activity based on preferences."""
        text_lower = text.lower()
        # Iconic attractions are must-do
        if any(word in text_lower for word in ["iconic", "famous", "must-see", "world-famous"]):
            return True
        # Check if it aligns with preferences
        for pref in preferences:
            if pref.lower() in text_lower:
                return True
        return False
    
    def _extract_tags(self, text: str, preferences: List[str]) -> List[str]:
        """Extract relevant tags from text and preferences."""
        tags = set()
        text_lower = text.lower()
        
        # Extract from text
        keywords = ["temple", "shrine", "food", "art", "nature", "history", "culture", 
                   "museum", "park", "walking", "views", "traditional", "modern"]
        for kw in keywords:
            if kw in text_lower:
                tags.add(kw)
        
        # Add from preferences
        for pref in preferences:
            tags.add(pref.lower())
        
        return list(tags)[:10]  # Max 10 tags
    
    def _extract_neighborhoods(self, activities: List[Activity]) -> List[str]:
        """Extract neighborhood names from activity addresses."""
        neighborhoods = set()
        for activity in activities:
            if activity.address:
                # Extract district/ward from address
                parts = activity.address.split(",")
                if len(parts) >= 2:
                    ward = parts[-2].strip() if len(parts) > 2 else parts[-1].strip()
                    neighborhoods.add(ward)
        return list(neighborhoods)[:5]  # Top 5 neighborhoods
    
    def _create_neighborhood_notes(self, activities: List[Activity]) -> Dict[str, str]:
        """Create neighborhood notes from activity addresses."""
        notes = {}
        for activity in activities:
            if activity.address:
                # Extract city/ward info
                parts = activity.address.split(",")
                if len(parts) >= 2:
                    ward = parts[-2].strip() if len(parts) > 2 else parts[-1].strip()
                    if ward not in notes:
                        notes[ward] = f"Area with {activity.type.value} attractions"
        return notes
    
    def _get_static_catalog_for_constraints(
        self,
        constraints: TravelConstraints
    ) -> ActivityCatalog:
        """Create a static ActivityCatalog for fallback when LLM fails."""
        per_city_catalogs: Dict[str, List[str]] = {}
        all_activities: List[Activity] = []
        
        for city in constraints.cities:
            city_activities = self._get_static_activities_for_city(city, constraints)
            per_city_catalogs[city] = [a.id for a in city_activities]
            all_activities.extend(city_activities)
        
        return ActivityCatalog(
            activities=all_activities,
            per_city=per_city_catalogs,
            neighborhood_notes=self._create_neighborhood_notes(all_activities)
        )
    
    def _map_preferences_to_categories(self, preferences: List[str]) -> List[str]:
        """Map user preferences to activity categories."""
        categories = set()
        for pref in preferences:
            pref_lower = pref.lower()
            if any(word in pref_lower for word in ["temple", "shrine", "culture", "history"]):
                categories.add("Culture & History")
            if any(word in pref_lower for word in ["food", "eat", "cuisine", "restaurant"]):
                categories.add("Food & Dining")
            if any(word in pref_lower for word in ["nature", "park", "outdoor"]):
                categories.add("Nature & Outdoors")
            if any(word in pref_lower for word in ["art", "museum", "gallery"]):
                categories.add("Art & Museums")
        return list(categories) if categories else ["General Sightseeing"]
