"""
Budget Agent - Phase 4c.
Ensures plan stays within budget constraints.
"""

from typing import List, Optional

from ..models import (
    TravelConstraints,
    BudgetBreakdown,
    BudgetCategory,
    BudgetViolation,
    SuggestedSwap,
    CostBand,
)


class BudgetAgent:
    """
    Analyzes costs and ensures budget compliance.
    
    Inputs: TravelConstraints + static price bands + FX rates
    Output: BudgetBreakdown with flags and suggested swaps
    
    Responsibilities:
    - Break budget into categories (stay, transport, food, activities)
    - Flag when plan exceeds budget
    - Suggest cheaper alternatives
    """
    
    def __init__(self, tool_router=None, llm_client=None):
        self.tool_router = tool_router
        self.llm_client = llm_client
        # Static price bands until real APIs are available
        self.price_bands = self._load_static_price_bands()
    
    async def analyze(self, constraints: TravelConstraints) -> BudgetBreakdown:
        """
        Phase 4c: Generate budget breakdown from constraints.
        
        Uses ToolRouter.price_band and ToolRouter.fx_convert to estimate
        costs and check against budget constraints.
        
        **Phase 4c**: Uses static ToolRouter data (no LLM calls).
        **Phase 8**: Could add LLM for intelligent swap suggestions.
        
        Args:
            constraints: TravelConstraints with cities, duration, budget
            
        Returns:
            BudgetBreakdown with categories, violations, and suggested swaps
        """
        categories = []
        violations = []
        suggested_swaps = []
        total_cost = 0.0
        
        # Determine price band based on budget level
        price_band = self._determine_price_band(constraints)
        
        # Estimate costs for each category
        for city in constraints.cities:
            # Get price data from ToolRouter
            stay_cost = await self._estimate_stay_cost(city, constraints, price_band)
            food_cost = await self._estimate_food_cost(city, constraints, price_band)
            transport_cost = await self._estimate_transport_cost(city, constraints)
            activity_cost = await self._estimate_activity_cost(city, constraints, price_band)
            
            # Add to categories
            categories.extend([
                stay_cost,
                food_cost,
                transport_cost,
                activity_cost
            ])
            
            total_cost += sum([
                stay_cost.estimated_total,
                food_cost.estimated_total,
                transport_cost.estimated_total,
                activity_cost.estimated_total
            ])
        
        # Check if over budget
        within_budget = total_cost <= constraints.budget_total
        
        if not within_budget:
            over_by = total_cost - constraints.budget_total
            violations.append(BudgetViolation(
                category="total",
                estimated=total_cost,
                limit=constraints.budget_total,
                over_by=over_by
            ))
            
            # Generate swap suggestions
            suggested_swaps = self._generate_swap_suggestions(
                categories, over_by, constraints, price_band
            )
        
        return BudgetBreakdown(
            categories=categories,
            grand_total=round(total_cost, 2),
            currency=constraints.currency,
            within_budget=within_budget,
            remaining_buffer=round(max(0, constraints.budget_total - total_cost), 2),
            violations=violations,
            suggested_swaps=suggested_swaps
        )
    
    def _determine_price_band(self, constraints: TravelConstraints) -> str:
        """Determine appropriate price band based on budget level."""
        # Simple heuristic: budget per day
        if constraints.duration_days == 0:
            return "moderate"
        
        daily_budget = constraints.budget_total / constraints.duration_days
        
        if daily_budget < 100:
            return "budget"
        elif daily_budget < 200:
            return "moderate"
        elif daily_budget < 400:
            return "expensive"
        else:
            return "luxury"
    
    async def _estimate_stay_cost(
        self,
        city: str,
        constraints: TravelConstraints,
        price_band: str
    ) -> any:  # BudgetCategory
        """Estimate accommodation cost for a city."""
        from ..models import BudgetCategory
        
        # Estimate nights in this city
        nights = max(1, constraints.duration_days // len(constraints.cities))
        
        # Get price from ToolRouter
        if self.tool_router:
            try:
                price_result = await self.tool_router.price_band(
                    category="hotel",
                    city=city,
                    band=price_band
                )
                cost_per_night = price_result.get("estimate_usd", 100)
            except Exception:
                cost_per_night = 100  # Fallback
        else:
            cost_per_night = self.price_bands.get("japan", {}).get("stay", {}).get(price_band, 100)
        
        total_cost = cost_per_night * nights
        
        return BudgetCategory(
            category="stay",
            estimated_total=round(total_cost, 2),
            currency=constraints.currency,
            notes=f"{nights} nights in {city} ({price_band} hotel)"
        )
    
    async def _estimate_food_cost(
        self,
        city: str,
        constraints: TravelConstraints,
        price_band: str
    ) -> any:  # BudgetCategory
        """Estimate food/dining cost for a city."""
        from ..models import BudgetCategory
        
        # Estimate days in this city
        days = max(1, constraints.duration_days // len(constraints.cities))
        
        # Get price from ToolRouter
        if self.tool_router:
            try:
                price_result = await self.tool_router.price_band(
                    category="food",
                    city=city,
                    band=price_band
                )
                cost_per_day = price_result.get("estimate_usd", 40)
            except Exception:
                cost_per_day = 40  # Fallback
        else:
            cost_per_day = self.price_bands.get("japan", {}).get("food", {}).get(price_band, 40)
        
        total_cost = cost_per_day * days
        
        return BudgetCategory(
            category="food",
            estimated_total=round(total_cost, 2),
            currency=constraints.currency,
            notes=f"{days} days of meals in {city} ({price_band} dining)"
        )
    
    async def _estimate_transport_cost(
        self,
        city: str,
        constraints: TravelConstraints
    ) -> any:  # BudgetCategory
        """Estimate transport cost for a city."""
        from ..models import BudgetCategory
        
        # Check if this city involves inter-city travel
        city_idx = constraints.cities.index(city) if city in constraints.cities else -1
        transport_cost = 0
        
        if city_idx > 0 and self.tool_router:
            # Get inter-city transport cost
            try:
                prev_city = constraints.cities[city_idx - 1]
                geo_result = await self.tool_router.geo_estimate(
                    from_location=prev_city,
                    to_location=city
                )
                transport_cost = geo_result.get("estimated_cost_usd", 50)
            except Exception:
                transport_cost = 50
        
        # Add local transport estimate
        days = max(1, constraints.duration_days // len(constraints.cities))
        local_transport = 10 * days  # ~$10 per day for local transport
        
        total_cost = transport_cost + local_transport
        
        return BudgetCategory(
            category="transport",
            estimated_total=round(total_cost, 2),
            currency=constraints.currency,
            notes=f"Transport to/from and within {city}"
        )
    
    async def _estimate_activity_cost(
        self,
        city: str,
        constraints: TravelConstraints,
        price_band: str
    ) -> any:  # BudgetCategory
        """Estimate activity/attraction cost for a city."""
        from ..models import BudgetCategory
        
        # Estimate activities per day
        days = max(1, constraints.duration_days // len(constraints.cities))
        
        # Get price from ToolRouter
        if self.tool_router:
            try:
                price_result = await self.tool_router.price_band(
                    category="activity",
                    city=city,
                    band=price_band
                )
                cost_per_day = price_result.get("estimate_usd", 20)
            except Exception:
                cost_per_day = 20  # Fallback
        else:
            cost_per_day = self.price_bands.get("japan", {}).get("activities", {}).get(price_band, 20)
        
        total_cost = cost_per_day * days
        
        return BudgetCategory(
            category="activities",
            estimated_total=round(total_cost, 2),
            currency=constraints.currency,
            notes=f"Activities and attractions in {city} ({price_band})"
        )
    
    def _generate_swap_suggestions(
        self,
        categories: List[any],
        over_by: float,
        constraints: TravelConstraints,
        current_band: str
    ) -> List[any]:  # List[SuggestedSwap]
        """Generate suggestions to reduce budget."""
        from ..models import SuggestedSwap
        
        swaps = []
        
        # Suggest downgrading hotel
        hotel_cat = next((c for c in categories if c.category == "stay"), None)
        if hotel_cat and current_band in ["expensive", "luxury"]:
            potential_savings = hotel_cat.estimated_total * 0.3
            swaps.append(SuggestedSwap(
                original_item=f"{current_band} hotel",
                suggested_alternative="Moderate 3-star hotel or Airbnb",
                savings_estimate=round(potential_savings, 2),
                rationale="Comfortable but less luxurious"
            ))
        
        # Suggest reducing dining costs
        food_cat = next((c for c in categories if c.category == "food"), None)
        if food_cat and current_band in ["expensive", "luxury"]:
            potential_savings = food_cat.estimated_total * 0.4
            swaps.append(SuggestedSwap(
                original_item=f"{current_band} dining",
                suggested_alternative="Mix of casual restaurants and convenience stores",
                savings_estimate=round(potential_savings, 2),
                rationale="Still good food, less fancy settings"
            ))
        
        # Suggest cutting expensive activities
        activity_cat = next((c for c in categories if c.category == "activities"), None)
        if activity_cat:
            potential_savings = activity_cat.estimated_total * 0.5
            swaps.append(SuggestedSwap(
                original_item="Paid attractions and tours",
                suggested_alternative="Focus on free temples, parks, and walking tours",
                savings_estimate=round(potential_savings, 2),
                rationale="More self-guided exploration, fewer organized tours"
            ))
        
        # If still way over budget, suggest fewer cities
        if over_by > constraints.budget_total * 0.5 and len(constraints.cities) > 1:
            swaps.append(SuggestedSwap(
                original_item=f"Visit {len(constraints.cities)} cities",
                suggested_alternative=f"Focus on {len(constraints.cities) - 1} cities to reduce transport costs",
                savings_estimate=round(over_by * 0.6, 2),
                rationale="Less travel time, more depth in fewer locations"
            ))
        
        return swaps
    
    def _load_static_price_bands(self) -> dict:
        """Load illustrative price bands for common destinations (fallback)."""
        return {
            "japan": {
                "stay": {"budget": 50, "moderate": 120, "expensive": 250, "luxury": 500},
                "food": {"budget": 20, "moderate": 50, "expensive": 100, "luxury": 200},
                "transport": {"local": 10, "intercity": 100},
                "activities": {"budget": 0, "moderate": 20, "expensive": 50, "luxury": 100}
            },
            "europe": {
                "stay": {"budget": 60, "moderate": 150, "expensive": 300, "luxury": 600},
                "food": {"budget": 25, "moderate": 60, "expensive": 120, "luxury": 250},
                "transport": {"local": 15, "intercity": 80},
                "activities": {"budget": 0, "moderate": 25, "expensive": 60, "luxury": 150}
            }
        }
