"""Pydantic models for agent communication."""

from .schemas import (
    # Core constraints
    TravelConstraints,
    
    # Destination outputs
    Activity,
    ActivityType,
    ActivityCatalog,
    CrowdLevel,
    CostBand,
    
    # Logistics outputs
    LodgingPlan,
    MovementPlan,
    DaySlot,
    DaySkeleton,
    LogisticsOutput,
    
    # Budget outputs
    BudgetCategory,
    BudgetViolation,
    SuggestedSwap,
    BudgetBreakdown,
    
    # Merge outputs
    DayItineraryItem,
    DayItinerary,
    DraftItinerary,
    
    # Review outputs
    ChecklistItem,
    RepairHint,
    ReviewReport,
    ReviewSeverity,
    ReviewStatus,
    
    # Final output
    FinalItinerary,
    
    # API models
    PlanRequest,
    PlanResponse,
    HealthResponse,
    
    # Test fixtures
    JAPAN_5D_TOKYO_KYOTO_3000_CONSTRAINTS,
)

__all__ = [
    "TravelConstraints",
    "Activity",
    "ActivityType",
    "ActivityCatalog",
    "CrowdLevel",
    "CostBand",
    "LodgingPlan",
    "MovementPlan",
    "DaySlot",
    "DaySkeleton",
    "LogisticsOutput",
    "BudgetCategory",
    "BudgetViolation",
    "SuggestedSwap",
    "BudgetBreakdown",
    "DayItineraryItem",
    "DayItinerary",
    "DraftItinerary",
    "ChecklistItem",
    "RepairHint",
    "ReviewReport",
    "ReviewSeverity",
    "ReviewStatus",
    "FinalItinerary",
    "PlanRequest",
    "PlanResponse",
    "HealthResponse",
    "JAPAN_5D_TOKYO_KYOTO_3000_CONSTRAINTS",
]
