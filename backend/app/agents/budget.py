"""
Budget Agent - Phase 4c.
Ensures plan stays within budget constraints.
Uses LLM for city-specific cost estimation instead of static price bands.
"""

import json
from typing import List, Optional, Dict

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
    Uses LLM knowledge for city-specific pricing estimates.
    """

    def __init__(self, tool_router=None, llm_client=None):
        self.tool_router = tool_router
        self.llm_client = llm_client

    async def analyze(self, constraints: TravelConstraints) -> BudgetBreakdown:
        """Generate budget breakdown from constraints."""
        if self.llm_client:
            try:
                return await self._llm_analyze(constraints)
            except Exception as e:
                print(f"LLM budget analysis failed: {e}")

        return await self._fallback_analyze(constraints)

    async def _llm_analyze(self, constraints: TravelConstraints) -> BudgetBreakdown:
        """Use LLM to generate city-specific budget estimates."""
        system_prompt = f"""You are a travel budget expert. Estimate realistic costs for a trip.

Respond with valid JSON:
{{
  "categories": [
    {{
      "category": "stay|food|transport|activities",
      "city": "city name",
      "estimated_total": number in {constraints.currency},
      "notes": "brief explanation"
    }}
  ],
  "grand_total": number in {constraints.currency},
  "within_budget": boolean,
  "swap_suggestions": [
    {{
      "original_item": "what to change",
      "suggested_alternative": "cheaper option",
      "savings_estimate": number in {constraints.currency},
      "rationale": "why this works"
    }}
  ]
}}

Rules:
- All amounts in {constraints.currency}
- For each city, provide stay, food, transport, and activities categories
- Use realistic local prices for {constraints.currency}
- If over budget, suggest specific swaps
- Be specific in notes (mention real hotel tiers, food types, transport modes)"""

        user_prompt = f"""Estimate costs for:
- Destination: {constraints.destination_region}
- Cities: {', '.join(constraints.cities)}
- Duration: {constraints.duration_days} days
- Budget: {constraints.budget_total} {constraints.currency}
- Preferences: {', '.join(constraints.preferences) if constraints.preferences else 'general'}"""

        content = await self.llm_client.chat_with_retry(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=900,
            response_format={"type": "json_object"}
        )

        data = json.loads(content)

        categories = []
        for cat in data.get("categories", []):
            categories.append(BudgetCategory(
                category=cat["category"],
                estimated_total=round(float(cat["estimated_total"]), 2),
                currency=constraints.currency,
                notes=cat.get("notes", "")
            ))

        grand_total = float(data.get("grand_total", sum(c.estimated_total for c in categories)))
        within_budget = grand_total <= constraints.budget_total

        violations = []
        if not within_budget:
            over_by = grand_total - constraints.budget_total
            violations.append(BudgetViolation(
                category="total", estimated=grand_total,
                limit=constraints.budget_total, over_by=over_by
            ))

        suggested_swaps = []
        for swap in data.get("swap_suggestions", []):
            suggested_swaps.append(SuggestedSwap(
                original_item=swap.get("original_item", ""),
                suggested_alternative=swap.get("suggested_alternative", ""),
                savings_estimate=round(float(swap.get("savings_estimate", 0)), 2),
                rationale=swap.get("rationale", "")
            ))

        return BudgetBreakdown(
            categories=categories,
            grand_total=round(grand_total, 2),
            currency=constraints.currency,
            within_budget=within_budget,
            remaining_buffer=round(max(0, constraints.budget_total - grand_total), 2),
            violations=violations,
            suggested_swaps=suggested_swaps
        )

    async def _fallback_analyze(self, constraints: TravelConstraints) -> BudgetBreakdown:
        """Simple fallback when LLM is unavailable."""
        categories = []
        total_cost = 0.0

        daily_budget = constraints.budget_total / max(1, constraints.duration_days)
        stay_pct, food_pct, transport_pct, activity_pct = 0.35, 0.25, 0.20, 0.20

        for city in constraints.cities:
            days = max(1, constraints.duration_days // len(constraints.cities))
            city_budget = daily_budget * days

            stay_cost = round(city_budget * stay_pct, 2)
            food_cost = round(city_budget * food_pct, 2)
            transport_cost = round(city_budget * transport_pct, 2)
            activity_cost = round(city_budget * activity_pct, 2)

            categories.extend([
                BudgetCategory(category="stay", estimated_total=stay_cost,
                               currency=constraints.currency, notes=f"{days} nights in {city}"),
                BudgetCategory(category="food", estimated_total=food_cost,
                               currency=constraints.currency, notes=f"{days} days of meals in {city}"),
                BudgetCategory(category="transport", estimated_total=transport_cost,
                               currency=constraints.currency, notes=f"Local + inter-city transport from {city}"),
                BudgetCategory(category="activities", estimated_total=activity_cost,
                               currency=constraints.currency, notes=f"Activities and attractions in {city}"),
            ])
            total_cost += stay_cost + food_cost + transport_cost + activity_cost

        within_budget = total_cost <= constraints.budget_total
        violations = []
        if not within_budget:
            violations.append(BudgetViolation(
                category="total", estimated=total_cost,
                limit=constraints.budget_total, over_by=total_cost - constraints.budget_total
            ))

        return BudgetBreakdown(
            categories=categories,
            grand_total=round(total_cost, 2),
            currency=constraints.currency,
            within_budget=within_budget,
            remaining_buffer=round(max(0, constraints.budget_total - total_cost), 2),
            violations=violations,
            suggested_swaps=[]
        )
