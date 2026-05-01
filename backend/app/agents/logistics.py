"""
Logistics Agent - Phase 4b.
Handles practical side of moving and staying.
"""

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
    
    Inputs: TravelConstraints + optional geo/transit tools
    Output: LogisticsOutput (LodgingPlan, MovementPlan, DaySkeleton[])
    
    Responsibilities:
    - Suggest where to stay in each city
    - Estimate travel time between locations
    - Recommend inter-city transport (e.g., Shinkansen)
    - Build realistic day sequences reducing backtracking
    """
    
    def __init__(self, tool_router=None, llm_client=None):
        self.tool_router = tool_router
        self.llm_client = llm_client
    
    async def plan(
        self,
        constraints: TravelConstraints,
        activity_catalog: Optional[any] = None
    ) -> LogisticsOutput:
        """
        Phase 4b: Generate logistics plan from constraints.
        
        Creates lodging plan, movement plan between cities, and day skeletons
        with travel-time estimates.
        
        **Phase 4b**: Uses ToolRouter.geo_estimate for distances (no LLM calls).
        **Phase 8**: Could add LLM for optimal day structuring.
        
        Args:
            constraints: TravelConstraints with cities, duration
            activity_catalog: Optional ActivityCatalog for neighborhood alignment
            
        Returns:
            LogisticsOutput with lodging, movement, and day skeletons
        """
        cities = constraints.cities
        duration = constraints.duration_days
        
        # 1. Allocate nights per city
        night_allocation = self._allocate_nights(cities, duration)
        
        # 2. Create lodging plans for each city
        lodging_plans = await self._create_lodging_plans(
            cities, night_allocation, constraints, activity_catalog
        )
        
        # 3. Plan inter-city movements
        movement_plans = await self._create_movement_plans(cities, constraints)
        
        # 4. Build day skeletons
        day_skeletons = self._build_day_skeletons(
            night_allocation, lodging_plans, movement_plans, constraints, activity_catalog
        )
        
        # Calculate total transit hours
        total_transit_hours = sum(m.duration_hours for m in movement_plans)
        
        return LogisticsOutput(
            lodging_plans=lodging_plans,
            movement_plans=movement_plans,
            day_skeletons=day_skeletons,
            total_estimated_transit_hours=total_transit_hours,
            route_description=self._generate_route_description(constraints) if constraints.is_road_trip else None,
            logistics_summary=self._generate_summary(movement_plans)
        )
    
    def _allocate_nights(self, cities: List[str], duration_days: int) -> Dict[str, int]:
        """
        Distribute nights across cities based on duration.
        
        Simple allocation: first city gets remainder nights.
        Phase 8: Could use LLM or scoring for smarter allocation.
        """
        if not cities:
            return {}
            
        base_nights = duration_days // len(cities)
        remainder = duration_days % len(cities)
        
        allocation = {}
        for i, city in enumerate(cities):
            # First cities get extra nights if there's remainder
            allocation[city] = base_nights + (1 if i < remainder else 0)
        
        return allocation
    
    async def _create_lodging_plans(
        self,
        cities: List[str],
        night_allocation: Dict[str, int],
        constraints: TravelConstraints,
        activity_catalog: Optional[any]
    ) -> List[LodgingPlan]:
        """Create lodging plans for each city."""
        plans = []
        
        for city in cities:
            nights = night_allocation.get(city, 1)
            
            # Determine preferred neighborhoods based on activity catalog
            neighborhoods = []
            # For now, use default neighborhoods (could be enhanced with activity analysis)
            if not neighborhoods:
                # Default neighborhoods based on city
                neighborhoods = self._get_default_neighborhoods(city)
            
            plan = LodgingPlan(
                city=city,
                nights=nights,
                suggested_neighborhoods=neighborhoods[:3] if neighborhoods else [f"Central {city}"],
                neighborhood_rationale=f"Selected based on proximity to activities in {city}",
                estimated_cost_per_night=CostBand.MODERATE
            )
            plans.append(plan)
        
        return plans
    
    def _get_default_neighborhoods(self, city: str) -> List[str]:
        """Get default neighborhoods for a city."""
        defaults = {
            # Japan
            "tokyo": ["Shinjuku", "Shibuya", "Asakusa"],
            "kyoto": ["Gion", "Higashiyama", "Kawaramachi"],
            "osaka": ["Dotonbori", "Umeda", "Shinsekai"],
            # Europe
            "paris": ["Marais", "Saint-Germain", "Montmartre"],
            "rome": ["Trastevere", "Centro Storico", "Monti"],
            "barcelona": ["Gothic Quarter", "Eixample", "Gracia"],
            "amsterdam": ["Jordaan", "De Pijp", "Centrum"],
            "berlin": ["Mitte", "Prenzlauer Berg", "Kreuzberg"],
            "london": ["Soho", "Shoreditch", "South Bank"],
            "prague": ["Old Town", "Mala Strana", "Vinohrady"],
            "vienna": ["Innere Stadt", "Mariahilf", "Naschmarkt"],
            "lisbon": ["Alfama", "Chiado", "Belem"],
            "madrid": ["Malasana", "La Latina", "Retiro"],
            # Scandinavia
            "stockholm": ["Gamla Stan", "Sodermalm", "Ostermalm"],
            "gothenburg": ["Haga", "Linne", "Avenyn"],
            "malmo": ["Gamla Staden", "Sodermalm", "Vastra Hamnen"],
            "oslo": ["Aker Brygge", "Grunerlokka", "Frogner"],
            "bergen": ["Bryggen", "Nordnes", "Sandviken"],
            "copenhagen": ["Nyhavn", "Vesterbro", "Frederiksberg"],
            "helsinki": ["Kamppi", "Kallio", "Ullanlinna"],
            "reykjavik": ["Downtown", "Laugardalur", "Hafnarfjordur"],
            "sweden": ["Gamla Stan", "Sodermalm", "Ostermalm"],
            "norway": ["Aker Brygge", "Grunerlokka", "Frogner"],
            # SE Asia
            "bangkok": ["Silom", "Sukhumvit", "Rattanakosin"],
            "phuket": ["Patong", "Kata", "Kamala"],
            "singapore": ["Marina Bay", "Chinatown", "Orchard"],
            "bali": ["Seminyak", "Ubud", "Canggu"],
            "kuala lumpur": ["Bukit Bintang", "KLCC", "Bangsar"],
            "hanoi": ["Old Quarter", "Hoan Kiem", "Tay Ho"],
            "ho chi minh city": ["District 1", "District 3", "Phu My Hung"],
            "jakarta": ["Menteng", "Kemang", "Sudirman"],
            # Americas
            "new york": ["Midtown", "Brooklyn", "West Village"],
            "los angeles": ["Santa Monica", "Silver Lake", "Venice"],
            "chicago": ["The Loop", "Lincoln Park", "Wicker Park"],
            "miami": ["South Beach", "Wynwood", "Brickell"],
            "san francisco": ["Mission District", "Nob Hill", "Fisherman's Wharf"],
            "mexico city": ["Condesa", "Roma Norte", "Polanco"],
            "toronto": ["Kensington Market", "Distillery District", "Yorkville"],
            "buenos aires": ["Palermo", "San Telmo", "Recoleta"],
            # Middle East
            "dubai": ["Downtown Dubai", "Jumeirah", "Dubai Marina"],
            "istanbul": ["Sultanahmet", "Beyoglu", "Kadikoy"],
            # Africa
            "cape town": ["V&A Waterfront", "Gardens", "Sea Point"],
            "marrakech": ["Medina", "Gueliz", "Hivernage"],
            "nairobi": ["Westlands", "Karen", "Kileleshwa"],
            # South Asia
            "mumbai": ["Colaba", "Bandra", "Marine Drive"],
            "delhi": ["Connaught Place", "Hauz Khas", "Lodi Colony"],
            "bangalore": ["Indiranagar", "Koramangala", "MG Road"],
            # Iceland Regions
            "reykjavik": ["Downtown", "Laugardalur", "Hafnarfjordur"],
            "vik": ["South Coast", "Skogar", "Vik Village"],
            "hofn": ["Diamond Beach", "Glacier Lagoon", "Hofn Harbor"],
            "egilsstadir": ["East Fjords", "Seydisfjordur", "Lagarfljot"],
            "akureyri": ["North Iceland", "Lake Myvatn", "Hsavik"],
            "borgarnes": ["Snaefellsnes Peninsula", "Kirkjufell", "Stykkisholmur"],
        }
        return defaults.get(city.lower(), [f"{city} City Centre", f"Central {city}"])

    async def _create_movement_plans(
        self,
        cities: List[str],
        constraints: TravelConstraints
    ) -> List[MovementPlan]:

        """Create inter-city movement plans using ToolRouter."""
        if len(cities) < 2:
            return []
        
        movements = []
        trace_id = getattr(constraints, 'trace_id', None)
        
        for i in range(len(cities) - 1):
            from_city = cities[i]
            to_city = cities[i + 1]
            
            # Use ToolRouter to get transit estimates
            if self.tool_router:
                try:
                    geo_result = await self.tool_router.geo_estimate(
                        from_location=from_city,
                        to_location=to_city,
                        trace_id=trace_id
                    )
                    
                    movement = MovementPlan(
                        from_city=from_city,
                        to_city=to_city,
                        mode=geo_result.get("mode", "unknown"),
                        duration_hours=geo_result.get("duration_minutes", 120) / 60,
                        cost_band=CostBand.MODERATE,
                        booking_notes=geo_result.get("notes", "")
                    )
                    movements.append(movement)
                    
                except Exception as e:
                    # Fallback to generic estimate
                    print(f"Geo estimate failed for {from_city}->{to_city}: {e}")
                    movements.append(self._create_fallback_movement(from_city, to_city))
            else:
                movements.append(self._create_fallback_movement(from_city, to_city))
        
        return movements
    
    def _create_fallback_movement(self, from_city: str, to_city: str) -> MovementPlan:
        """Create a fallback movement plan when ToolRouter unavailable."""
        return MovementPlan(
            from_city=from_city,
            to_city=to_city,
            mode="transit",
            duration_hours=2.0,
            cost_band=CostBand.MODERATE,
            booking_notes="Generic estimate - check local transit options"
        )
    
    def _build_day_skeletons(
        self,
        night_allocation: Dict[str, int],
        lodging_plans: List[LodgingPlan],
        movement_plans: List[MovementPlan],
        constraints: TravelConstraints,
        activity_catalog: Optional[any] = None
    ) -> List[DaySkeleton]:
        """Create day-by-day structure with travel time buffers."""
        skeletons = []
        cities = constraints.cities
        
        if not cities:
            return skeletons
        
        current_day = 1
        current_city_idx = 0
        
        while current_day <= constraints.duration_days and current_city_idx < len(cities):
            city = cities[current_city_idx]
            nights_in_city = night_allocation.get(city, 1)
            
            # Check if there's a movement to next city
            is_travel_day = False
            travel_buffer_minutes = 0
            
            if current_city_idx < len(cities) - 1:
                # Check if this is the last day in current city
                days_remaining = sum(night_allocation.get(cities[i], 1) 
                                   for i in range(current_city_idx, len(cities)))
                
                if current_day == constraints.duration_days - days_remaining + nights_in_city:
                    # This is the travel day
                    is_travel_day = True
                    if current_city_idx < len(movement_plans):
                        travel_buffer_minutes = int(movement_plans[current_city_idx].duration_hours * 60) + 60  # +1h buffer
            
            # Create day skeleton
            travel_hours = travel_buffer_minutes / 60
            if is_travel_day:
                slots = [
                    DaySlot(
                        slot_index=0,
                        start_time="09:00",
                        end_time="10:00",
                        activity_type="checkout",
                        city=city,
                        notes=f"Check out and travel to {cities[current_city_idx + 1]}"
                    ),
                    DaySlot(
                        slot_index=1,
                        start_time="10:00",
                        end_time=f"{10 + int(travel_hours):02d}:00",
                        activity_type="travel",
                        city=city,
                        notes="Inter-city travel"
                    ),
                    DaySlot(
                        slot_index=2,
                        start_time=f"{10 + int(travel_hours):02d}:00",
                        end_time=f"{11 + int(travel_hours):02d}:00",
                        activity_type="checkin",
                        city=cities[current_city_idx + 1],
                        notes=f"Arrive and check in to {cities[current_city_idx + 1]}"
                    )
                ]
            else:
                # Regular exploration day - generate specific slot notes
                slots = self._generate_day_slots(city, constraints, activity_catalog)
            
            skeleton = DaySkeleton(
                day_number=current_day,
                city=city,
                slots=slots,
                total_travel_time_hours=travel_hours,
                pacing_notes=f"Day in {city}" if not is_travel_day else f"Travel day: {city} -> {cities[current_city_idx + 1] if current_city_idx + 1 < len(cities) else 'next'}"
            )
            skeletons.append(skeleton)
            
            # Move to next city after travel day or after last night
            if is_travel_day or (not is_travel_day and current_day >= sum(night_allocation.get(cities[i], 1) for i in range(current_city_idx + 1))):
                current_city_idx += 1
            
            current_day += 1
        
        return skeletons
    
    def _generate_day_slots(
        self,
        city: str,
        constraints: TravelConstraints,
        activity_catalog: Optional[any] = None
    ) -> List[DaySlot]:
        """Generate day slots with specific activity descriptions."""
        # Get city-specific activity suggestions
        city_activities = []
        if activity_catalog and hasattr(activity_catalog, 'activities'):
            city_activities = [a for a in activity_catalog.activities if a.city == city]
        
        # Build rich narrative slot notes based on preferences and available activities
        prefs = [p.lower() for p in constraints.preferences] if constraints.preferences else []
        avoids = [a.lower() for a in constraints.avoidances] if constraints.avoidances else []
        
        # Check for crowd avoidance
        crowd_avoid = any("crowd" in a for a in avoids)
        
        # Get specific activity names if available
        must_do = []
        if city_activities:
            must_do = [a for a in city_activities if a.must_do][:2]
        
        # Morning slot - rich narrative
        if must_do:
            morning_note = f"Wake up to a pleasant morning and visit {must_do[0].name}. This iconic attraction offers a perfect start to your day in {city}."
            if crowd_avoid:
                morning_note += " Arrive early (before 8 AM) to avoid crowds and enjoy a peaceful experience."
        else:
            morning_note = f"Wake up to a pleasant morning in {city}. Begin your day exploring the city's iconic landmarks and cultural sites."
            if crowd_avoid:
                morning_note += " Start early (before 8 AM) to avoid crowds at popular attractions."
        
        # Lunch slot - narrative style
        if any("food" in p or "eat" in p or "cuisine" in p for p in prefs):
            lunch_note = f"Enjoy lunch at a local restaurant featuring authentic {city} cuisine. Try the regional specialties and local flavors."
        else:
            lunch_note = f"Take a lunch break at a nearby restaurant. Enjoy local flavors and recharge for the afternoon activities."
        
        # Afternoon slot - rich narrative
        if len(must_do) > 1:
            afternoon_note = f"Continue your exploration at {must_do[1].name}. Soak in the atmosphere and capture memorable photos."
            if crowd_avoid:
                afternoon_note += " Late afternoon timing helps avoid peak crowds."
        elif any("nature" in p or "park" in p for p in prefs):
            afternoon_note = f"Spend your afternoon enjoying nature walks and parks. Experience the scenic beauty and peaceful surroundings of {city}."
        elif any("shopping" in p or "market" in p for p in prefs):
            afternoon_note = f"Explore local markets and shopping districts. Discover unique souvenirs and experience the vibrant local culture."
        else:
            afternoon_note = f"Continue exploring {city}'s attractions. Visit museums, cultural sites, or simply wander through charming neighborhoods."
        
        # Dinner slot - narrative style
        dinner_note = f"Evening in {city}. Enjoy dinner at a local restaurant and take a leisurely walk to experience the city's nightlife. Return to your hotel for overnight stay."
        
        return [
            DaySlot(
                slot_index=0,
                start_time="09:00",
                end_time="12:00",
                activity_type="morning",
                city=city,
                notes=morning_note
            ),
            DaySlot(
                slot_index=1,
                start_time="12:00",
                end_time="13:30",
                activity_type="lunch",
                city=city,
                notes=lunch_note
            ),
            DaySlot(
                slot_index=2,
                start_time="14:00",
                end_time="17:00",
                activity_type="afternoon",
                city=city,
                notes=afternoon_note
            ),
            DaySlot(
                slot_index=3,
                start_time="18:00",
                end_time="20:00",
                activity_type="dinner",
                city=city,
                notes=dinner_note
            )
        ]
    
    def _generate_summary(self, movement_plans: List[MovementPlan]) -> str:
        """Generate a human-readable logistics summary."""
        if not movement_plans:
            return "Single city stay - no inter-city travel"
        
        parts = []
        for move in movement_plans:
            parts.append(f"{move.from_city} → {move.to_city} ({move.mode}, {move.duration_hours}h)")
        
        return " | ".join(parts)

    def _generate_route_description(self, constraints: TravelConstraints) -> str:
        """Generate a narrative overview of the road trip route."""
        dest = constraints.destination_region.lower()
        if "iceland" in dest:
            return "This itinerary follows the legendary Ring Road (Route 1) counter-clockwise: covering the South Coast waterfalls, Jökulsárlón glacier lagoon, the dramatic East Fjords, North Iceland's volcanic landscapes, and the Snæfellsnes Peninsula."
        elif "norway" in dest:
            return "A scenic drive through the Western Fjords, including the Atlantic Ocean Road, Geirangerfjord, and the dramatic coastal mountains."
        elif "japan" in dest:
            return "A journey through the Japanese Alps and coastal regions, connecting Tokyo, Hakone, Takayama, and Kanazawa."
        return f"A comprehensive road trip route through {constraints.destination_region}, optimized for scenic driving and balanced pacing across all major regions."
