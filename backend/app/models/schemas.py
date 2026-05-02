"""
Shared Data Models for AI Travel Planner
Pydantic schemas defining contracts between all agents.
Based on Architecture.md and ImplementationPlan.md Phase 1.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ============================================================================
# Enums and Constants
# ============================================================================

class ActivityType(str, Enum):
    TEMPLE = "temple"
    FOOD = "food"
    MUSEUM = "museum"
    NATURE = "nature"
    SHOPPING = "shopping"
    ENTERTAINMENT = "entertainment"
    TRANSPORT = "transport"
    OTHER = "other"


class CrowdLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class CostBand(str, Enum):
    BUDGET = "budget"      # $: < $20
    MODERATE = "moderate"  # $$: $20-50
    EXPENSIVE = "expensive" # $$$: $50-100
    LUXURY = "luxury"      # $$$$: > $100


class ReviewSeverity(str, Enum):
    BLOCKING = "blocking"
    ADVISORY = "advisory"


class ReviewStatus(str, Enum):
    PASS = "pass"
    WARNINGS = "warnings"
    FAIL = "fail"


# ============================================================================
# Core Input/Constraint Models (Orchestrator Output, Worker Input)
# ============================================================================

class TravelConstraints(BaseModel):
    """
    Extracted from natural language request by Orchestrator.
    Shared read-only input to all worker agents.
    """
    destination_region: str = Field(..., min_length=1, max_length=100, description="Primary region/country")
    cities: List[str] = Field(..., min_length=1, max_length=10, description="Target cities to visit")
    duration_days: int = Field(..., ge=1, le=90, description="Trip duration in days")
    budget_total: float = Field(..., gt=0, le=100000000, description="Total budget in specified currency (supports INR and large amounts)")
    currency: str = Field(default="INR", min_length=3, max_length=3, description="Currency code (ISO 4217)")
    preferences: List[str] = Field(default_factory=list, description="What the user wants (e.g., 'food', 'temples')")
    avoidances: List[str] = Field(default_factory=list, description="What the user wants to avoid (e.g., 'crowds')")
    hard_requirements: List[str] = Field(default_factory=list, description="Must-haves inferred from request")
    soft_preferences: List[str] = Field(default_factory=list, description="Nice-to-haves inferred from request")
    is_road_trip: bool = Field(default=False, description="Whether the user wants a road trip (e.g., Iceland Ring Road)")
    
    # Trace ID for observability
    trace_id: UUID = Field(default_factory=uuid4, description="Unique request trace ID")
    
    @field_validator("destination_region")
    @classmethod
    def validate_destination_not_empty(cls, v: str) -> str:
        """Ensure destination is not just whitespace."""
        if v is None or not v or not v.strip():
            raise ValueError("Destination region cannot be empty or whitespace")
        return v.strip()
    
    @field_validator("cities")
    @classmethod
    def validate_cities_unique(cls, v: List[str]) -> List[str]:
        """Ensure no duplicate cities."""
        seen = set()
        for city in v:
            city_lower = city.lower().strip()
            if city_lower in seen:
                raise ValueError(f"Duplicate city: {city}")
            seen.add(city_lower)
        return v
    
    @field_validator("currency")
    @classmethod
    def validate_currency_uppercase(cls, v: str) -> str:
        """Ensure currency is uppercase."""
        return v.upper()
    
    @field_validator("budget_total")
    @classmethod
    def validate_budget_reasonable(cls, v: float) -> float:
        """Warn about potentially unreasonable budgets (but allow)."""
        if v > 100000:
            # Still valid but could be a typo - logged at usage level
            pass
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "destination_region": "Japan",
                "cities": ["Tokyo", "Kyoto"],
                "duration_days": 5,
                "budget_total": 3000,
                "currency": "INR",
                "preferences": ["food", "temples"],
                "avoidances": ["crowds"],
                "hard_requirements": ["visit both Tokyo and Kyoto"],
                "soft_preferences": ["authentic local food"]
            }
        }
    )

class Region(BaseModel):
    """A geographic region/segment of a trip."""
    name: str = Field(..., description="Region name (e.g., 'South Coast')")
    base_location: str = Field(..., description="Primary town/city for lodging")
    days: int = Field(..., ge=1, description="Number of days allocated")
    highlights: List[str] = Field(default_factory=list, description="Key attractions in this region")


class TripStructure(BaseModel):
    """Output of TripStructuringAgent — defines trip skeleton before execution."""
    trip_type: str = Field(..., description="city_trip | road_trip | multi_region")
    regions: List[Region] = Field(..., min_length=1, description="Ordered list of regions to visit")
    route: List[str] = Field(..., description="Ordered route of location names")
    pace: str = Field(default="balanced", description="relaxed | balanced | aggressive")




# ============================================================================
# Destination Research Agent Output
# ============================================================================

class Activity(BaseModel):
    """Single activity item in the catalog."""
    id: str = Field(..., min_length=1, max_length=50, description="Stable unique ID for merge/re-review")
    name: str = Field(..., min_length=1, max_length=200)
    city: str = Field(..., min_length=1, max_length=100)
    type: ActivityType
    estimated_duration_hours: float = Field(..., gt=0, le=24, description="Duration in hours, max 24")
    crowd_level: CrowdLevel = CrowdLevel.UNKNOWN
    cost_band: CostBand
    must_do: bool = Field(default=False, description="High priority item")
    rationale: str = Field(..., min_length=1, max_length=500, description="Why this matches preferences")
    address: Optional[str] = Field(default=None, max_length=300)
    best_time: Optional[str] = Field(default=None, max_length=50)  # e.g., "morning", "evening"
    less_crowded_alternative: Optional[str] = Field(default=None, max_length=50)  # ID of alternative activity
    tags: List[str] = Field(default_factory=list, max_length=20)
    
    @field_validator("id")
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        """Ensure ID has no spaces and is URL-safe."""
        if ' ' in v or '/' in v or '\\' in v:
            raise ValueError("Activity ID cannot contain spaces or slashes")
        return v.lower().strip()
    
    @field_validator("estimated_duration_hours")
    @classmethod
    def validate_duration_precision(cls, v: float) -> float:
        """Round to nearest 0.5 hour for consistency."""
        return round(v * 2) / 2
    
    @field_validator("tags")
    @classmethod
    def validate_tags_unique(cls, v: List[str]) -> List[str]:
        """Ensure no duplicate tags."""
        seen = set()
        result = []
        for tag in v:
            tag_lower = tag.lower().strip()
            if tag_lower not in seen:
                seen.add(tag_lower)
                result.append(tag)
        return result
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "tokyo-temple-001",
                "name": "Senso-ji Temple",
                "city": "Tokyo",
                "type": "temple",
                "estimated_duration_hours": 2,
                "crowd_level": "high",
                "cost_band": "budget",
                "must_do": True,
                "rationale": "Tokyo's oldest temple, aligns with temple preference",
                "less_crowded_alternative": "tokyo-temple-002"
            }
        }
    )


class ActivityCatalog(BaseModel):
    """
    Output from Destination Research Agent.
    Curated activities per city matching user preferences.
    """
    activities: List[Activity] = Field(..., min_length=1, description="All recommended activities")
    per_city: Dict[str, List[str]] = Field(
        ..., 
        description="Activity IDs grouped by city"
    )
    neighborhood_notes: Dict[str, str] = Field(
        default_factory=dict,
        description="Notes about areas/neighborhoods per city"
    )
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    @field_validator("per_city")
    @classmethod
    def validate_all_activities_in_catalog(cls, v: Dict[str, List[str]], values) -> Dict[str, List[str]]:
        """Ensure all activity IDs in per_city exist in activities list."""
        if "activities" in values.data:
            all_ids = {a.id for a in values.data["activities"]}
            for city, ids in v.items():
                for aid in ids:
                    if aid not in all_ids:
                        raise ValueError(f"Activity ID '{aid}' in city '{city}' not found in catalog")
        return v


# ============================================================================
# Logistics Agent Output
# ============================================================================

class LodgingPlan(BaseModel):
    """Where to stay per city/area."""
    city: str
    nights: int = Field(..., ge=0)
    suggested_neighborhoods: List[str]
    neighborhood_rationale: str  # Why these areas align with preferences
    estimated_cost_per_night: CostBand


class MovementPlan(BaseModel):
    """Inter-city and intra-city transport."""
    from_city: str
    to_city: str
    mode: str = Field(..., description="e.g., 'Shinkansen', 'flight', 'bus'")
    duration_hours: float
    frequency: Optional[str] = None  # e.g., "every 30 min"
    cost_band: CostBand
    booking_notes: Optional[str] = None


class DaySlot(BaseModel):
    """Single time slot in a day skeleton."""
    slot_index: int
    start_time: str  # e.g., "09:00"
    end_time: str    # e.g., "12:00"
    activity_type: str  # e.g., "temple_visit", "lunch", "transit"
    city: str
    travel_time_to_next_minutes: Optional[int] = None
    notes: Optional[str] = None


class DaySkeleton(BaseModel):
    """Structure for one day of the trip."""
    day_number: int = Field(..., ge=1)
    city: str
    slots: List[DaySlot]
    total_travel_time_hours: float = 0.0
    pacing_notes: Optional[str] = None  # e.g., "relaxed", "busy"


class LogisticsOutput(BaseModel):
    """
    Combined output from Logistics Agent.
    """
    lodging_plans: List[LodgingPlan]
    movement_plans: List[MovementPlan]  # Between cities
    day_skeletons: List[DaySkeleton]  # Day-by-day structure
    backtracking_minimized: bool = True
    total_estimated_transit_hours: float
    route_description: Optional[str] = Field(default=None, description="Overview of the road trip route if applicable")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================================
# Budget Agent Output
# ============================================================================

class BudgetCategory(BaseModel):
    """Budget for a single category."""
    category: Literal["stay", "transport", "food", "activities", "buffer"]
    estimated_total: float = Field(..., ge=0, description="Estimated total cost (cannot be negative)")
    currency: str
    breakdown: Optional[Dict[str, float]] = None  # e.g., {"hotels": 800, "ryokan": 400}
    notes: Optional[str] = None


class BudgetViolation(BaseModel):
    """When budget exceeds constraints."""
    category: str
    estimated: float
    limit: float
    over_by: float


class SuggestedSwap(BaseModel):
    """Cheaper alternative suggestion."""
    original_item: str  # Activity ID or description
    suggested_alternative: str
    savings_estimate: float
    rationale: str


class BudgetBreakdown(BaseModel):
    """
    Output from Budget Agent.
    Category split with flags and suggestions.
    """
    categories: List[BudgetCategory] = Field(..., min_length=1)
    grand_total: float = Field(..., ge=0)
    currency: str = Field(..., min_length=3, max_length=3)
    within_budget: bool
    remaining_buffer: float
    violations: List[BudgetViolation] = Field(default_factory=list, max_length=50)
    suggested_swaps: List[SuggestedSwap] = Field(default_factory=list, max_length=50)
    flags: List[str] = Field(default_factory=list, max_length=20)  # Warning strings
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    @field_validator("grand_total")
    @classmethod
    def validate_total_matches_sum(cls, v: float, values) -> float:
        """Ensure grand_total equals sum of category totals."""
        if "categories" in values.data:
            calculated = sum(c.estimated_total for c in values.data["categories"])
            if abs(v - calculated) > 0.01:
                raise ValueError(f"Grand total {v} doesn't match sum of categories {calculated}")
        return v
    
    @field_validator("currency")
    @classmethod
    def validate_currency_uppercase(cls, v: str) -> str:
        """Ensure currency is uppercase."""
        return v.upper()
    
    @field_validator("categories")
    @classmethod
    def validate_single_currency(cls, v: List[BudgetCategory]) -> List[BudgetCategory]:
        """Ensure all categories use the same currency."""
        if len(v) > 1:
            currencies = {c.currency.upper() for c in v}
            if len(currencies) > 1:
                raise ValueError(f"All categories must use the same currency, found: {currencies}")
        return v
    
    @field_validator("violations")
    @classmethod
    def validate_violations_have_positive_over_by(cls, v: List[BudgetViolation]) -> List[BudgetViolation]:
        """Ensure violations have positive 'over_by' amounts."""
        for violation in v:
            if violation.over_by <= 0:
                raise ValueError(f"Budget violation 'over_by' must be positive, got {violation.over_by}")
        return v
    
    @field_validator("suggested_swaps")
    @classmethod
    def validate_swaps_have_positive_savings(cls, v: List[SuggestedSwap]) -> List[SuggestedSwap]:
        """Ensure suggested swaps have positive savings."""
        for swap in v:
            if swap.savings_estimate <= 0:
                raise ValueError(f"Suggested swap 'savings_estimate' must be positive, got {swap.savings_estimate}")
        return v


# ============================================================================
# Orchestrator Merge Output
# ============================================================================

class DayItineraryItem(BaseModel):
    """A concrete item in the day-by-day plan."""
    slot_index: int = Field(..., ge=0, le=20, description="Slot position in day, 0-20")
    time: str = Field(..., max_length=30, description="e.g., '09:00 - 11:00'")
    activity_id: Optional[str] = Field(default=None, max_length=50)  # Links to ActivityCatalog
    activity_name: str = Field(..., min_length=1, max_length=200)
    city: str = Field(..., min_length=1, max_length=100)
    type: ActivityType
    cost_estimate: float = Field(..., ge=0, description="Cost must be non-negative")
    travel_time_from_prev: Optional[str] = Field(default=None, max_length=50)
    notes: Optional[str] = Field(default=None, max_length=500)
    
    @field_validator("slot_index")
    @classmethod
    def validate_slot_index_reasonable(cls, v: int) -> int:
        """Prevent excessive slots in a single day."""
        if v > 15:
            raise ValueError(f"Day cannot have more than 15 slots (got slot_index={v})")
        return v


class DayItinerary(BaseModel):
    """Full day in the merged itinerary."""
    day_number: int = Field(..., ge=1, le=365, description="Day number in trip, 1-365")
    city: str = Field(..., min_length=1, max_length=100)
    items: List[DayItineraryItem] = Field(..., max_length=15, description="Activities in this day")
    day_summary: str = Field(..., min_length=1, max_length=500)
    day_cost: float = Field(..., ge=0)
    lodging_area: Optional[str] = Field(default=None, max_length=100)
    
    @field_validator("items")
    @classmethod
    def validate_unique_slot_indices(cls, v: List[DayItineraryItem]) -> List[DayItineraryItem]:
        """Ensure no duplicate slot indices within a day."""
        indices = [item.slot_index for item in v]
        if len(indices) != len(set(indices)):
            raise ValueError("Duplicate slot indices found in day")
        return v
    
    @field_validator("day_cost")
    @classmethod
    def validate_day_cost_matches_items(cls, v: float, values) -> float:
        """Warn if day_cost doesn't match sum of item costs (within $1 tolerance)."""
        if "items" in values.data:
            calculated = sum(item.cost_estimate for item in values.data["items"])
            if abs(v - calculated) > 1.0:
                raise ValueError(f"Day cost {v} doesn't match sum of items {calculated}")
        return v


class DraftItinerary(BaseModel):
    """
    Merged output from Orchestrator combining all agent outputs.
    """
    constraints: TravelConstraints  # Reference to original constraints
    days: List[DayItinerary]
    total_estimated_cost: float
    currency: str
    budget_summary: BudgetBreakdown  # Embedded or referenced
    catalog_references: List[str] = Field(
        default_factory=list,
        description="Activity IDs used in this itinerary"
    )
    merged_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1  # For re-review cycles


# ============================================================================
# Review Agent Output
# ============================================================================

class ChecklistItem(BaseModel):
    """Single validation check result."""
    check: str  # e.g., "days_match_duration"
    passed: bool
    expected: Any
    actual: Any
    severity: ReviewSeverity
    message: str


class RepairHint(BaseModel):
    """Suggested fix for a failing check."""
    issue: str
    suggested_action: str  # e.g., "remove one full-day Kyoto block"
    priority: int = Field(..., ge=1, le=10)


class ReviewReport(BaseModel):
    """
    Output from Review Agent.
    Quality gate before user delivery.
    """
    draft_version: int
    overall_status: ReviewStatus
    checklist: List[ChecklistItem] = Field(
        default_factory=list,
        description="All validation checks performed"
    )
    blocking_issues: List[str] = Field(default_factory=list)
    advisory_warnings: List[str] = Field(default_factory=list)
    repair_hints: List[RepairHint] = Field(default_factory=list)
    qualitative_assessment: Optional[str] = None  # LLM narrative assessment
    reviewed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def can_deliver(self) -> bool:
        """True if no blocking issues."""
        return len(self.blocking_issues) == 0 and self.overall_status != ReviewStatus.FAIL


# ============================================================================
# Final Output Models
# ============================================================================

class FinalItinerary(BaseModel):
    """
    User-facing final output.
    """
    id: UUID = Field(default_factory=uuid4)
    constraints: TravelConstraints
    days: List[DayItinerary]
    neighborhoods: Dict[str, List[str]]  # City -> neighborhood suggestions
    logistics_summary: str  # Inter-city transport overview
    strategic_insight: Optional[str] = Field(default=None, description="Why this itinerary works (strategic pacing, etc.)")
    budget_analysis: Optional[str] = Field(default=None, description="Reality check and budget strategy")
    cost_optimization_tips: List[str] = Field(default_factory=list, description="Practical ways to save money")
    budget_rollup: BudgetBreakdown
    review_status: ReviewStatus
    review_warnings: List[str] = Field(default_factory=list)
    disclaimer: str = Field(
        default="This plan is illustrative. Prices and availability are estimates only. Verify before booking.",
        description="Safety disclaimer"
    )
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PlanInsights(BaseModel):
    """LLM-generated insights for the final itinerary."""
    strategic_insight: str
    budget_analysis: str
    cost_optimization_tips: List[str]
    
    @field_validator("strategic_insight", "budget_analysis", mode="before")
    @classmethod
    def coerce_to_string(cls, v):
        """LLMs sometimes return a dict/list instead of a string. Coerce gracefully."""
        if isinstance(v, dict):
            import json
            return json.dumps(v, indent=2)
        if isinstance(v, list):
            return "; ".join(str(item) for item in v)
        return v
    
    @field_validator("cost_optimization_tips", mode="before")
    @classmethod
    def coerce_tips_to_list(cls, v):
        """Ensure tips is always a list of strings."""
        if isinstance(v, str):
            return [v]
        if isinstance(v, dict):
            return [f"{k}: {val}" for k, val in v.items()]
        return v


# ============================================================================
# API Request/Response Models
# ============================================================================

class PlanRequest(BaseModel):
    """POST /api/plan request body."""
    request: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Natural language travel request"
    )
    flags: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional flags for debugging/feature toggles"
    )


class PlanResponse(BaseModel):
    """POST /api/plan response body."""
    final_itinerary: FinalItinerary
    constraints: TravelConstraints
    review_summary: ReviewStatus
    trace_id: UUID
    processing_time_ms: Optional[int] = None
    used_stub_mode: bool = Field(
        default=False,
        description="True if stub fallback was used (no LLM available)"
    )


class HealthResponse(BaseModel):
    """GET /health response."""
    status: Literal["healthy", "degraded", "unhealthy"] = "healthy"
    version: str = "0.1.0"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tokens: Optional[Dict[str, Any]] = None  # Token budget status
    llm_provider: str = "groq"  # Current LLM provider
    llm_available: bool = False  # Whether LLM is configured and ready


# ============================================================================
# Golden Fixtures for Testing (Phase 1 Exit Criteria)
# ============================================================================

JAPAN_5D_TOKYO_KYOTO_3000_CONSTRAINTS = TravelConstraints(
    destination_region="Japan",
    cities=["Tokyo", "Kyoto"],
    duration_days=5,
    budget_total=3000,
    currency="INR",
    preferences=["food", "temples"],
    avoidances=["crowds"],
    hard_requirements=["visit both Tokyo and Kyoto"],
    soft_preferences=["authentic local food", "quiet temple experiences"]
)
