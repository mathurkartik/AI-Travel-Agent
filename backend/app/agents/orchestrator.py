"""
Orchestrator Agent - Phase 2: Constraint extraction with Groq.
Phase 5: Full orchestration with parallel workers.
Phase 7: Repair loop implementation.
Phase 8: Timeouts, observability, and partial failure handling.
"""

import asyncio
import time
from typing import Optional, List, Dict, Any

from ..models import (
    TravelConstraints, DraftItinerary, FinalItinerary, ReviewReport,
    ActivityCatalog, LogisticsOutput, BudgetBreakdown, DayItinerary,
    DayItineraryItem, BudgetCategory, ActivityType, PlanInsights,
    TripStructure, Region
)
from ..config import get_settings
from .destination import DestinationAgent
from .logistics import LogisticsAgent
from .budget import BudgetAgent
from .review import ReviewAgent
from .trip_structuring import TripStructuringAgent
from ..tools import ToolRouter
from ..utils.observability import ObservabilityLogger


class OrchestratorAgent:
    """
    Central coordinator for the travel planning pipeline.
    
    Responsibilities:
    1. Parse NL request → TravelConstraints (Phase 2) with Groq LLM
    2. Dispatch parallel workers with constraints (Phase 5)
    3. Merge agent outputs → DraftItinerary (Phase 5)
    4. Manage Review → Repair loop (Phase 7)
    5. Produce FinalItinerary for user
    
    Token Management:
    - Uses Groq client with 100k tokens/day limit
    - Tracks usage per request
    - Caches responses to reduce consumption
    """
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self._settings = get_settings()
        
        # Lazy-load Groq client if not provided and Groq is configured
        if self.llm_client is None and self._settings.llm_provider == "groq":
            try:
                from ..llm import get_groq_client
                self.llm_client = get_groq_client()
            except Exception as e:
                # Log warning but don't fail - stub mode available
                print(f"Warning: Could not initialize Groq client: {e}")
        
        # Phase 5: Initialize worker agents with shared ToolRouter
        tool_router = ToolRouter()
        self.destination_agent = DestinationAgent(tool_router=tool_router, llm_client=self.llm_client)
        self.logistics_agent = LogisticsAgent(tool_router=tool_router, llm_client=self.llm_client)
        self.budget_agent = BudgetAgent(tool_router=tool_router, llm_client=self.llm_client)
        self.review_agent = ReviewAgent(llm_client=self.llm_client)  # Phase 6
        self.trip_structuring_agent = TripStructuringAgent(llm_client=self.llm_client)
    
    async def extract_constraints(self, natural_language_request: str) -> TravelConstraints:
        """
        Phase 2: Extract structured constraints from NL request using Groq LLM.
        
        Uses structured JSON output for reliable parsing:
        - destination_region, cities[], duration_days
        - budget_total, currency
        - preferences[], avoidances[]
        - hard_requirements vs soft_preferences
        
        Token Usage: ~2,500-4,000 tokens per extraction
        """
        # Use configured LLM client (Groq by default)
        if self.llm_client is None:
            raise RuntimeError(
                "LLM client not available. "
                "Set GROQ_API_KEY in .env or use stub mode for testing."
            )
        
        # Delegate to Groq client with structured extraction
        try:
            constraints = await self.llm_client.extract_constraints(natural_language_request)
            return constraints
        except Exception as e:
            # Log error and provide helpful context
            print(f"Constraint extraction failed: {e}")
            
            # Check if it's a token budget issue
            if "budget" in str(e).lower():
                raise RuntimeError(
                    f"Daily token budget exceeded. "
                    f"Check status at /api/tokens/status or wait until UTC midnight."
                ) from e
            
            # Re-raise with context
            raise RuntimeError(f"Failed to extract constraints: {e}") from e
    
    async def create_plan(self, natural_language_request: str, trace_id: str = "unknown") -> FinalItinerary:
        """
        Phase 5-8: Full orchestration pipeline with Review, Repair loop, timeouts, and observability.
        
        Pipeline:
        1. Extract constraints (Phase 2)
        2. Run agents in parallel (Phase 4a, 4b, 4c) with timeouts
        3. Merge outputs → DraftItinerary (Phase 5)
        4. Review → Repair loop (Phase 6-7, max 3 retries)
        5. Return FinalItinerary with disclaimer
        
        Phase 8 additions:
        - Per-agent timeouts and partial failure handling
        - Structured observability logging
        - Total plan timing and logging
        """
        plan_start_time = time.time()
        timeout_seconds = self._settings.agent_timeout_seconds
        
        ObservabilityLogger.log_agent_start("orchestrator", trace_id, 
                                           request_chars=len(natural_language_request))
        
        # Step 1: Extract constraints with timeout
        try:
            constraints = await asyncio.wait_for(
                self.extract_constraints(natural_language_request),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            ObservabilityLogger.log_partial_failure(
                trace_id, "constraint_extraction",
                "fallback_to_stub", "Constraint extraction timed out"
            )
            raise RuntimeError(f"Constraint extraction timed out after {timeout_seconds}s")
        
        # Step 1.5: Trip Structuring (NEW - from improvement.md)
        trip_structure = None
        use_structuring = constraints.duration_days > 7 or constraints.is_road_trip
        
        if use_structuring:
            try:
                trip_structure = await self.trip_structuring_agent.structure(constraints)
                print(f"Trip structured: {trip_structure.trip_type}, {len(trip_structure.regions)} regions, pace={trip_structure.pace}")
                # Update constraints cities from trip structure route
                structured_cities = [r.base_location for r in trip_structure.regions]
                constraints = TravelConstraints(
                    destination_region=constraints.destination_region,
                    cities=structured_cities,
                    duration_days=constraints.duration_days,
                    budget_total=constraints.budget_total,
                    currency=constraints.currency,
                    preferences=constraints.preferences,
                    avoidances=constraints.avoidances,
                    hard_requirements=constraints.hard_requirements,
                    soft_preferences=constraints.soft_preferences,
                    is_road_trip=constraints.is_road_trip or trip_structure.trip_type == "road_trip",
                )
            except Exception as e:
                print(f"Trip structuring failed, using flat pipeline: {e}")
                trip_structure = None
        
        # Step 2: Run agents (per-region if structured, flat otherwise)
        if trip_structure and len(trip_structure.regions) > 1:
            activity_catalog, logistics_output, budget_breakdown = await self._run_agents_per_region(
                constraints, trip_structure, timeout_seconds, trace_id
            )
        else:
            activity_catalog, logistics_output, budget_breakdown = await self._run_agents_flat(
                constraints, timeout_seconds, trace_id
            )
        
        # Step 4: Merge outputs into DraftItinerary
        merge_start = time.time()
        draft = await self.merge(
            constraints=constraints,
            activity_catalog=activity_catalog,
            logistics_output=logistics_output,
            budget_breakdown=budget_breakdown
        )
        ObservabilityLogger.log_agent_complete(
            "merge", trace_id, (time.time() - merge_start) * 1000, 
            artifact_version=1, success=True
        )
        
        # Step 5: Review → Repair loop (Phase 6-7, max 3 retries)
        max_repair_cycles = self._settings.max_review_retries
        repair_count = 0
        
        try:
            review_report = await asyncio.wait_for(
                self.review_agent.review(draft, constraints),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            ObservabilityLogger.log_partial_failure(
                trace_id, "review_agent",
                "pass_without_review", "Review timed out, assuming pass"
            )
            # Create passing review report as fallback
            from ..models import ReviewReport, ReviewStatus
            review_report = ReviewReport(
                draft_version=draft.version,
                overall_status=ReviewStatus.PASS,
                checklist=[],
                blocking_issues=[],
                advisory_warnings=["Review timed out - manual verification recommended"],
                repair_hints=[]
            )
        
        # Log review outcome
        ObservabilityLogger.log_review_outcome(
            trace_id, draft.version, review_report.overall_status,
            {"total": len(review_report.checklist), 
             "passed": sum(1 for c in review_report.checklist if c.passed)},
            len(review_report.blocking_issues),
            len(review_report.advisory_warnings),
            len(review_report.repair_hints)
        )
        
        while review_report.overall_status == "fail" and repair_count < max_repair_cycles:
            print(f"Repair cycle {repair_count + 1}: Addressing {len(review_report.repair_hints)} issues...")
            
            # Log repair action
            actions = [h.suggested_action[:50] for h in review_report.repair_hints[:3]]
            ObservabilityLogger.log_repair_action(trace_id, repair_count + 1, 
                                                len(review_report.repair_hints), actions)
            
            # Attempt repair based on repair hints
            draft = await self.repair(
                draft=draft,
                review_report=review_report,
                constraints=constraints
            )
            
            repair_count += 1
            
            # Re-review after repair
            try:
                review_report = await asyncio.wait_for(
                    self.review_agent.review(draft, constraints),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                ObservabilityLogger.log_partial_failure(
                    trace_id, "review_agent",
                    "pass_without_review", f"Re-review timed out after cycle {repair_count}"
                )
                break
            
            if review_report.overall_status == "pass":
                print(f"Repair successful after {repair_count} cycle(s)")
                break
        
        if review_report.overall_status == "fail":
            print(f"Warning: Max repair cycles ({max_repair_cycles}) reached. Returning best-effort plan.")
        
        # Step 6: Generate insights (Strategic + Budget Reality Check)
        insights = await self._generate_insights(constraints, draft)
        
        # Step 7: Create FinalItinerary from Draft with Review status, insights, and disclaimer
        final_itinerary = self._draft_to_final(
            draft=draft,
            constraints=constraints,
            budget_breakdown=budget_breakdown,
            review_report=review_report,
            repair_cycles=repair_count,
            insights=insights
        )
        
        # Phase 8: Log plan completion
        total_duration_ms = (time.time() - plan_start_time) * 1000
        ObservabilityLogger.log_plan_complete(
            trace_id, total_duration_ms,
            review_report.overall_status, repair_count,
            len(draft.days), len(set(d.city for d in draft.days))
        )
        
        ObservabilityLogger.log_agent_complete(
            "orchestrator", trace_id, total_duration_ms,
            artifact_version=draft.version, success=True
        )
        
        return final_itinerary
    
    async def _run_agents_flat(self, constraints, timeout_seconds, trace_id):
        """Original flat pipeline — runs all agents once on full constraints."""
        # Destination
        activity_catalog = None
        try:
            activity_catalog = await asyncio.wait_for(
                self.destination_agent.research(constraints),
                timeout=timeout_seconds
            )
        except Exception as e:
            ObservabilityLogger.log_partial_failure(
                trace_id, "destination_agent", "use_static_catalog", str(e)[:100]
            )
            activity_catalog = self.destination_agent._get_static_catalog_for_constraints(constraints)
        
        # Logistics + Budget in parallel
        logistics_task = self._run_logistics_with_timeout(constraints, activity_catalog, timeout_seconds, trace_id)
        budget_task = self._run_budget_with_timeout(constraints, timeout_seconds, trace_id)
        logistics_output, budget_breakdown = await asyncio.gather(logistics_task, budget_task, return_exceptions=True)
        
        if isinstance(logistics_output, Exception):
            from ..models import LogisticsOutput
            logistics_output = LogisticsOutput(
                lodging_plans=[], movement_plans=[], day_skeletons=[],
                total_estimated_transit_hours=0.0,
                logistics_summary="Fallback - logistics unavailable"
            )
        if isinstance(budget_breakdown, Exception):
            from ..models import BudgetBreakdown
            budget_breakdown = BudgetBreakdown(
                categories=[], grand_total=0.0, currency=constraints.currency,
                within_budget=True, remaining_buffer=constraints.budget_total
            )
        
        return activity_catalog, logistics_output, budget_breakdown
    
    async def _run_agents_per_region(self, constraints, trip_structure, timeout_seconds, trace_id):
        """Run agents per-region in PARALLEL, then merge results."""
        from ..models import LogisticsOutput, ActivityCatalog, Activity, BudgetBreakdown, BudgetCategory

        async def _process_one_region(region):
            """Process a single region: runs destination, budget, logistics in parallel."""
            print(f"  [Parallel] Processing region: {region.name} ({region.days} days)")
            region_constraints = TravelConstraints(
                destination_region=constraints.destination_region,
                cities=[region.base_location],
                duration_days=region.days,
                budget_total=constraints.budget_total * (region.days / constraints.duration_days),
                currency=constraints.currency,
                preferences=constraints.preferences,
                avoidances=constraints.avoidances,
                hard_requirements=constraints.hard_requirements,
                soft_preferences=constraints.soft_preferences,
                is_road_trip=constraints.is_road_trip,
            )

            # --- Destination (must run first so logistics can use it) ---
            try:
                region_catalog = await asyncio.wait_for(
                    self.destination_agent.research(region_constraints),
                    timeout=timeout_seconds
                )
            except Exception as e:
                print(f"  Region {region.name} destination failed: {e}")
                region_catalog = self.destination_agent._get_static_catalog_for_constraints(region_constraints)

            # --- Budget + Logistics in parallel (both only need region_constraints) ---
            budget_task = asyncio.wait_for(
                self.budget_agent.analyze(region_constraints),
                timeout=timeout_seconds
            )
            logistics_task = asyncio.wait_for(
                self.logistics_agent.plan(region_constraints, region_catalog),
                timeout=timeout_seconds
            )
            budget_result, logistics_result = await asyncio.gather(
                budget_task, logistics_task, return_exceptions=True
            )

            return region_catalog, budget_result, logistics_result

        # ── Run ALL regions in parallel ──────────────────────────────────────
        region_results = await asyncio.gather(
            *[_process_one_region(r) for r in trip_structure.regions],
            return_exceptions=True
        )

        # ── Merge results ────────────────────────────────────────────────────
        all_activities = []
        all_categories = []
        all_movement_plans = []
        all_lodging_plans = []
        all_day_skeletons = []
        grand_total = 0.0
        total_transit = 0.0
        per_city = {}
        neighborhood_notes = {}

        for region, result in zip(trip_structure.regions, region_results):
            if isinstance(result, Exception):
                print(f"  Region {region.name} entirely failed: {result}")
                continue

            region_catalog, budget_result, logistics_result = result

            # Catalog
            all_activities.extend(region_catalog.activities)
            per_city.update(region_catalog.per_city)
            neighborhood_notes.update(region_catalog.neighborhood_notes)

            # Budget
            if not isinstance(budget_result, Exception):
                all_categories.extend(budget_result.categories)
                grand_total += budget_result.grand_total
            else:
                print(f"  Region {region.name} budget failed: {budget_result}")

            # Logistics
            if not isinstance(logistics_result, Exception):
                all_lodging_plans.extend(logistics_result.lodging_plans)
                all_movement_plans.extend(logistics_result.movement_plans)
                all_day_skeletons.extend(logistics_result.day_skeletons)
                total_transit += logistics_result.total_estimated_transit_hours
            else:
                print(f"  Region {region.name} logistics failed: {logistics_result}")

        # Resequence day numbers globally after merging all regions
        for i, skeleton in enumerate(all_day_skeletons):
            skeleton.day_number = i + 1

        activity_catalog = ActivityCatalog(
            activities=all_activities,
            per_city=per_city,
            neighborhood_notes=neighborhood_notes
        )
        logistics_output = LogisticsOutput(
            lodging_plans=all_lodging_plans,
            movement_plans=all_movement_plans,
            day_skeletons=all_day_skeletons,
            total_estimated_transit_hours=total_transit,
            logistics_summary=f"Route: {' → '.join(trip_structure.route)}"
        )
        budget_breakdown = BudgetBreakdown(
            categories=all_categories,
            grand_total=round(grand_total, 2),
            currency=constraints.currency,
            within_budget=grand_total <= constraints.budget_total,
            remaining_buffer=round(max(0, constraints.budget_total - grand_total), 2)
        )

        return activity_catalog, logistics_output, budget_breakdown

    async def _run_logistics_with_timeout(self, constraints, activity_catalog, timeout_seconds, trace_id):
        """Run logistics agent with timeout and observability."""
        agent_start = time.time()
        try:
            result = await asyncio.wait_for(
                self.logistics_agent.plan(constraints, activity_catalog),
                timeout=timeout_seconds
            )
            ObservabilityLogger.log_agent_complete(
                "logistics", trace_id, (time.time() - agent_start) * 1000,
                success=True
            )
            return result
        except asyncio.TimeoutError:
            ObservabilityLogger.log_agent_complete(
                "logistics", trace_id, timeout_seconds * 1000,
                success=False, error_type="TimeoutError"
            )
            raise
    
    async def _run_budget_with_timeout(self, constraints, timeout_seconds, trace_id):
        """Run budget agent with timeout and observability."""
        agent_start = time.time()
        try:
            result = await asyncio.wait_for(
                self.budget_agent.analyze(constraints),
                timeout=timeout_seconds
            )
            ObservabilityLogger.log_agent_complete(
                "budget", trace_id, (time.time() - agent_start) * 1000,
                success=True
            )
            return result
        except asyncio.TimeoutError:
            ObservabilityLogger.log_agent_complete(
                "budget", trace_id, timeout_seconds * 1000,
                success=False, error_type="TimeoutError"
            )
            raise
    
    async def merge(
        self,
        constraints: TravelConstraints,
        activity_catalog: ActivityCatalog,
        logistics_output: LogisticsOutput,
        budget_breakdown: BudgetBreakdown,
    ) -> DraftItinerary:
        """
        Phase 5: Merge agent outputs into cohesive draft.
        
        Combines:
        - What (ActivityCatalog with activity IDs)
        - When/Where (LogisticsOutput with day skeletons)
        - Cost (BudgetBreakdown with category totals)
        
        Resolves conflicts by using stable IDs as linking mechanism.
        
        Args:
            constraints: Original TravelConstraints
            activity_catalog: Output from DestinationAgent
            logistics_output: Output from LogisticsAgent
            budget_breakdown: Output from BudgetAgent
            
        Returns:
            DraftItinerary with day-by-day structure and linked activities
        """
        # Build day-by-day itinerary from logistics skeletons
        days: List[DayItinerary] = []
        
        # Create lookup for activities by ID
        activity_by_id = {a.id: a for a in activity_catalog.activities}
        
        # Track used activities across all days to ensure variety
        used_activity_ids = set()
        
        # Build each day from logistics skeletons
        for skeleton in logistics_output.day_skeletons:
            day_items: List[DayItineraryItem] = []
            day_cost = 0.0
            
            for slot in skeleton.slots:
                # Find appropriate activity for this slot
                activity_ref = None
                cost_estimate = 0.0
                
                # Handle travel slots specially
                if slot.activity_type in ["travel", "checkout", "checkin"]:
                    activity_name = slot.notes
                    activity_type = ActivityType.TRANSPORT if slot.activity_type == "travel" else ActivityType.OTHER
                    item = DayItineraryItem(
                        slot_index=slot.slot_index,
                        time=f"{slot.start_time} - {slot.end_time}",
                        activity_id=None,
                        activity_name=activity_name,
                        city=slot.city,
                        type=activity_type,
                        cost_estimate=0.0,
                        notes=slot.notes
                    )
                    day_items.append(item)
                    continue
                
                # Try to match slot type with available activities
                activity_ref = self._find_activity_for_slot(
                    slot.activity_type,
                    skeleton.city,
                    activity_catalog,
                    activity_by_id,
                    used_activity_ids
                )
                if activity_ref:
                    used_activity_ids.add(activity_ref)
                    
                    # Get cost estimate if we found an activity
                    if activity_ref and activity_ref in activity_by_id:
                        activity = activity_by_id[activity_ref]
                        # Estimate cost based on cost band
                        cost_estimate = self._estimate_activity_cost(activity)
                
                # Get activity details if available, otherwise use slot notes
                activity_name = slot.notes  # Use slot description instead of generic "Free time"
                activity_type = ActivityType.OTHER
                if activity_ref and activity_ref in activity_by_id:
                    activity = activity_by_id[activity_ref]
                    activity_name = activity.name
                    activity_type = activity.type
                
                # Format time range from start_time and end_time
                time_range = f"{slot.start_time} - {slot.end_time}"
                
                item = DayItineraryItem(
                    slot_index=slot.slot_index,
                    time=time_range,
                    activity_id=activity_ref,
                    activity_name=activity_name,
                    city=slot.city,
                    type=activity_type,
                    cost_estimate=cost_estimate,
                    notes=slot.notes
                )
                day_items.append(item)
                day_cost += cost_estimate
            
            day = DayItinerary(
                day_number=skeleton.day_number,
                city=skeleton.city,
                items=day_items,
                day_summary=self._generate_day_summary(skeleton, day_items, activity_by_id),
                day_cost=round(day_cost, 2),
                lodging_area=next(
                    (", ".join(l.suggested_neighborhoods) for l in logistics_output.lodging_plans if l.city == skeleton.city),
                    None
                )
            )
            days.append(day)
        
        # Calculate total cost
        total_cost = sum(d.day_cost for d in days)
        
        return DraftItinerary(
            constraints=constraints,
            days=days,
            total_estimated_cost=round(total_cost, 2),
            currency=constraints.currency,
            budget_summary=budget_breakdown,
            catalog_references=list(activity_by_id.keys()),
            merged_at=__import__('datetime').datetime.now(__import__('datetime').timezone.utc),
            version=1
        )
    
    def _find_activity_for_slot(
        self,
        slot_type: str,
        city: str,
        catalog: ActivityCatalog,
        activity_by_id: Dict[str, Any],
        used_ids: set = None
    ) -> Optional[str]:
        """Find appropriate activity ID for a given slot type."""
        if used_ids is None:
            used_ids = set()
        
        # Get activities for this city
        city_data = catalog.per_city.get(city)
        if not city_data:
            return None
        
        available_ids = city_data  # per_city is Dict[str, List[str]]
        
        # Map slot type to activity type preferences
        type_preferences = {
            "morning": ["temple", "museum", "nature"],
            "afternoon": ["temple", "nature", "shopping"],
            "lunch": ["food"],
            "dinner": ["food"],
        }
        
        preferences = type_preferences.get(slot_type, [])
        
        # Find first activity matching preferences (not already used)
        for activity_id in available_ids:
            if activity_id in used_ids:
                continue
            if activity_id in activity_by_id:
                activity = activity_by_id[activity_id]
                if any(pref in str(activity.type).lower() for pref in preferences):
                    return activity_id
        
        # Fallback: return first unused activity
        for activity_id in available_ids:
            if activity_id not in used_ids:
                return activity_id
        
        return None
    
    def _estimate_activity_cost(self, activity: Any) -> float:
        """Estimate cost for an activity based on its cost band."""
        cost_map = {
            "budget": 0,
            "moderate": 20,
            "expensive": 50,
            "luxury": 100,
        }
        return cost_map.get(str(activity.cost_band).lower(), 20)
    
    def _generate_day_summary(
        self,
        skeleton: Any,
        items: List[DayItineraryItem],
        activity_by_id: Dict[str, Any]
    ) -> str:
        """Generate human-readable summary for a day."""
        # Check if this is a travel day (has travel slots)
        travel_slots = [s for s in skeleton.slots if s.activity_type == "travel"]
        if travel_slots:
            return f"Travel day: {skeleton.pacing_notes or 'Travel between cities'}"
        
        # Get activity names
        activity_names = []
        for item in items:
            if item.activity_id and item.activity_id in activity_by_id:
                activity = activity_by_id[item.activity_id]
                activity_names.append(activity.name)
        
        if activity_names:
            return f"Explore {skeleton.city}: {', '.join(activity_names[:2])}"
        return f"Day in {skeleton.city}"
    
    def _draft_to_final(
        self,
        draft: DraftItinerary,
        constraints: TravelConstraints,
        budget_breakdown: BudgetBreakdown,
        review_report: any = None,  # Optional ReviewReport
        repair_cycles: int = 0,
        insights: Optional[PlanInsights] = None
    ) -> FinalItinerary:
        """Convert DraftItinerary to FinalItinerary with Review status (Phase 6-7)."""
        from ..models import FinalItinerary, ReviewStatus
        
        # Extract neighborhoods from all days
        neighborhoods: Dict[str, List[str]] = {}
        for day in draft.days:
            if day.city not in neighborhoods:
                neighborhoods[day.city] = []
            if day.lodging_area and day.lodging_area not in neighborhoods[day.city]:
                neighborhoods[day.city].append(day.lodging_area)
        
        # Create logistics summary
        logistics_summary = " | ".join(
            f"Day {d.day_number}: {d.city}" for d in draft.days[:3]
        )
        if len(draft.days) > 3:
            logistics_summary += f" ... (+{len(draft.days) - 3} more days)"
        
        # Use review report if available, otherwise default to PASS
        review_status = ReviewStatus.PASS
        review_warnings = []
        
        # Phase 7: Build comprehensive disclaimer
        base_disclaimer = "Generated by AI Travel Planner. Verify prices and availability before booking."
        
        if review_report:
            review_status = review_report.overall_status
            review_warnings = review_report.advisory_warnings.copy()
            
            if review_report.overall_status == "fail":
                base_disclaimer += f"\nWarning: This itinerary has blocking issues after {repair_cycles} repair attempts. Please review carefully before using."
            elif repair_cycles > 0:
                base_disclaimer += f"\nNote: Itinerary required {repair_cycles} repair cycle(s) to resolve issues."
        
        return FinalItinerary(
            constraints=draft.constraints,
            days=draft.days,
            neighborhoods=neighborhoods,
            logistics_summary=logistics_summary,
            strategic_insight=insights.strategic_insight if insights else None,
            budget_analysis=insights.budget_analysis if insights else None,
            cost_optimization_tips=insights.cost_optimization_tips if insights else [],
            budget_rollup=budget_breakdown,
            review_status=review_status,
            review_warnings=review_warnings,
            disclaimer=base_disclaimer
        )
    
    async def _generate_insights(self, constraints: TravelConstraints, draft: DraftItinerary) -> PlanInsights:
        """Generate strategic insights and budget analysis using LLM."""
        if self.llm_client is None:
             return PlanInsights(
                strategic_insight="A well-paced itinerary balancing major landmarks and local experiences.",
                budget_analysis=f"The budget of {constraints.budget_total} {constraints.currency} aligns with a comfortable mid-range trip for {constraints.duration_days} days.",
                cost_optimization_tips=["Book transport in advance", "Use local supermarkets for snacks", "Look for free walking tours"]
            )
        
        system_prompt = """You are a travel strategy expert. Analyze the itinerary and constraints.
Generate:
1. strategic_insight: Narrative on why this plan is smart (e.g. 'Covers 100% of the Ring Road', 'Strategic pace').
2. budget_analysis: A 'Reality Check' on the budget vs duration. Mention if it's budget, mid-range, or luxury.
3. cost_optimization_tips: 3-5 practical tips to save money for this specific trip.

Respond with valid JSON matching the PlanInsights schema."""

        prompt = f"Constraints: {constraints.model_dump_json()}\nItinerary Summary: Total cost {draft.total_estimated_cost} {draft.currency}, {len(draft.days)} days. Cities: {', '.join(set(d.city for d in draft.days))}"
        
        try:
            insights = await self.llm_client.generate_with_schema(
                prompt=prompt,
                system_prompt=system_prompt,
                output_schema=PlanInsights
            )
            return insights
        except Exception as e:
             print(f"Insight generation failed: {e}")
             return PlanInsights(
                strategic_insight="A balanced itinerary designed for maximum coverage of the requested regions.",
                budget_analysis="The budget is sufficient for a standard mid-range experience at this destination.",
                cost_optimization_tips=["Eat at local markets", "Consider a multi-day regional pass"]
            )
    
    async def repair(
        self,
        draft: DraftItinerary,
        review_report: ReviewReport,
        constraints: TravelConstraints
    ) -> DraftItinerary:
        """
        Phase 7: Bounded repair loop implementation.
        
        Interprets RepairHints from ReviewReport and applies fixes:
        - trim_over_budget: Remove expensive activities or reduce costs
        - fix_duration_mismatch: Add/remove days to match duration
        - swap_lodging: Change to cheaper neighborhoods
        - redistribute_budget: Rebalance costs across days
        
        Returns modified DraftItinerary for re-review.
        """
        import copy
        from ..models import DayItinerary, DayItineraryItem, ActivityType
        
        # Create a copy to avoid mutating original
        repaired_draft = copy.deepcopy(draft)
        
        if not review_report.repair_hints:
            print("No repair hints provided, returning draft unchanged")
            return repaired_draft
        
        print(f"Processing {len(review_report.repair_hints)} repair hints...")
        
        # Sort hints by priority (highest first)
        sorted_hints = sorted(review_report.repair_hints, key=lambda h: h.priority, reverse=True)
        
        for hint in sorted_hints:
            issue = hint.issue.lower()
            action = hint.suggested_action.lower()
            print(f"  Repairing: {hint.issue} (priority {hint.priority})")
            
            # Handle budget overruns
            if "budget" in issue or "cost" in issue or "over" in issue:
                if "trim" in action or "reduce" in action or "remove" in action:
                    repaired_draft = self._trim_expensive_activities(repaired_draft)
                elif "swap" in action or "lodging" in action:
                    repaired_draft = self._reduce_lodging_costs(repaired_draft)
                elif "rebalance" in action:
                    repaired_draft = self._rebalance_day_costs(repaired_draft)
            
            # Handle duration mismatches
            elif "duration" in issue or "days" in issue:
                if "add" in action or "extend" in action:
                    repaired_draft = self._add_missing_days(repaired_draft, constraints)
                elif "remove" in action or "trim" in action:
                    repaired_draft = self._remove_extra_days(repaired_draft, constraints)
            
            # Handle duplicate day numbering
            elif "duplicate" in issue or "resequence" in action:
                repaired_draft = self._resequence_days(repaired_draft)
            
            # Handle city mismatches
            elif "city" in issue or "wrong city" in issue:
                repaired_draft = self._fix_city_assignments(repaired_draft, constraints)
            
            # Handle missing activities or structure issues
            elif "structure" in issue or "empty" in issue or "missing" in issue:
                repaired_draft = self._fill_empty_slots(repaired_draft, constraints)
        
        # Recalculate total cost after repairs
        total_cost = sum(d.day_cost for d in repaired_draft.days)
        repaired_draft.total_estimated_cost = round(total_cost, 2)
        
        # Increment version to track repair iterations
        repaired_draft.version += 1
        
        print(f"Repair complete. Draft version: {repaired_draft.version}, Total cost: ${total_cost}")
        return repaired_draft
    
    def _trim_expensive_activities(self, draft: DraftItinerary) -> DraftItinerary:
        """Reduce costs by removing or replacing expensive activities."""
        for day in draft.days:
            for item in day.items:
                # Reduce high cost estimates
                if item.cost_estimate > 50.0:
                    item.cost_estimate = round(item.cost_estimate * 0.7, 2)  # 30% reduction
        return draft
    
    def _reduce_lodging_costs(self, draft: DraftItinerary) -> DraftItinerary:
        """Adjust lodging areas to cheaper alternatives."""
        # Mark lodging areas as budget-friendly
        for day in draft.days:
            if day.lodging_area:
                day.lodging_area = f"Budget-friendly area near {day.lodging_area}"
        return draft
    
    def _rebalance_day_costs(self, draft: DraftItinerary) -> DraftItinerary:
        """Even out cost distribution across days."""
        if not draft.days:
            return draft
        
        avg_cost = sum(d.day_cost for d in draft.days) / len(draft.days)
        
        for day in draft.days:
            # Bring each day closer to average
            if day.day_cost > avg_cost * 1.5:
                day.day_cost = round(avg_cost * 1.2, 2)
        return draft
    
    def _add_missing_days(self, draft: DraftItinerary, constraints: TravelConstraints) -> DraftItinerary:
        """Add days to match required duration."""
        from ..models import DayItinerary, DayItineraryItem, ActivityType
        
        current_days = len(draft.days)
        target_days = constraints.duration_days
        
        if current_days < target_days:
            # Add blank days with minimal structure
            for day_num in range(current_days + 1, target_days + 1):
                new_day = DayItinerary(
                    day_number=day_num,
                    city=constraints.cities[0] if constraints.cities else "Unknown",
                    items=[
                        DayItineraryItem(
                            slot_index=0,
                            time="09:00 - 12:00",
                            activity_id=None,
                            activity_name="Exploration day",
                            city=constraints.cities[0] if constraints.cities else "Unknown",
                            type=ActivityType.OTHER,
                            cost_estimate=0.0,
                            notes="Flexible day for personal exploration"
                        )
                    ],
                    day_summary=f"Day {day_num}: Flexible exploration",
                    day_cost=0.0,
                    lodging_area=None
                )
                draft.days.append(new_day)
        
        return draft
    
    def _remove_extra_days(self, draft: DraftItinerary, constraints: TravelConstraints) -> DraftItinerary:
        """Remove excess days beyond required duration."""
        target_days = constraints.duration_days
        
        if len(draft.days) > target_days:
            # Keep first and last days, remove from middle
            keep_indices = [0] + list(range(len(draft.days) - target_days + 1, len(draft.days)))
            draft.days = [draft.days[i] for i in keep_indices[:target_days]]
            
            # Renumber days
            for i, day in enumerate(draft.days, 1):
                day.day_number = i
        
        return draft
    
    def _fix_city_assignments(self, draft: DraftItinerary, constraints: TravelConstraints) -> DraftItinerary:
        """Ensure all days are assigned to valid cities from constraints."""
        valid_cities = set(constraints.cities)
        
        for day in draft.days:
            if day.city not in valid_cities:
                # Assign to first valid city
                day.city = constraints.cities[0] if constraints.cities else day.city
                for item in day.items:
                    item.city = day.city
        
        return draft
    
    def _fill_empty_slots(self, draft: DraftItinerary, constraints: TravelConstraints) -> DraftItinerary:
        """Fill empty or minimal slots with placeholder activities."""
        from ..models import DayItineraryItem, ActivityType
        
        for day in draft.days:
            if not day.items:
                # Add default item if day is empty
                day.items = [
                    DayItineraryItem(
                        slot_index=0,
                        time="09:00 - 18:00",
                        activity_id=None,
                        activity_name="Free exploration",
                        city=day.city,
                        type=ActivityType.OTHER,
                        cost_estimate=0.0,
                        notes="Day at leisure for personal activities"
                    )
                ]
        
        return draft
    
    def _resequence_days(self, draft: DraftItinerary) -> DraftItinerary:
        """Fix duplicate day numbering by assigning sequential day numbers."""
        for i, day in enumerate(draft.days, 1):
            day.day_number = i
        return draft
