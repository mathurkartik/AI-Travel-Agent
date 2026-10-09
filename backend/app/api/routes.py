"""
API Routes - Phase 0: Stub endpoints matching eventual contracts.
Phase 7: Will implement full orchestration pipeline.
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from ..models import (
    PlanRequest,
    PlanResponse,
    HealthResponse,
    TravelConstraints,
    FinalItinerary,
    DayItinerary,
    DayItineraryItem,
    BudgetBreakdown,
    BudgetCategory,
    ReviewStatus,
    ActivityType,
    MissingConstraintError,
)

from pydantic import BaseModel

class BookingRequest(BaseModel):
    name: str
    email: str
    comment: str
    itinerary: dict

router = APIRouter()


@router.post("/book", tags=["Booking"])
async def book_itinerary(booking: BookingRequest):
    """
    Submit a booking request.
    In a real app, this would send an email or store in a DB.
    """
    # Simulate sending email to mathurkartik@live.com
    print(f"\n--- NEW BOOKING REQUEST ---")
    print(f"To: mathurkartik@live.com")
    print(f"From: {booking.name} <{booking.email}>")
    print(f"Comment: {booking.comment}")
    
    # Summarize itinerary
    final = booking.itinerary.get("final_itinerary", {})
    constraints = booking.itinerary.get("constraints", {})
    dest = constraints.get("destination_region", "Unknown")
    days = constraints.get("duration_days", "Unknown")
    budget = constraints.get("budget_total", "Unknown")
    currency = constraints.get("currency", "INR")
    
    print(f"Trip: {days} days in {dest}")
    print(f"Budget: {budget} {currency}")
    print(f"--- END OF REQUEST ---\n")
    
    return {"status": "success", "message": "Your booking request has been sent to mathurkartik@live.com. We will contact you soon!"}


@router.post("/plan", response_model=PlanResponse, tags=["Planning"])
async def create_plan(request: Request, plan_request: PlanRequest):
    """
    Create a travel plan from natural language request.
    
    **Phase 5**: Full orchestration with parallel worker agents.
    1. Extracts constraints using Groq LLM
    2. Strictly validates 3 pillars: Destination, Duration, Budget
    3. Runs Destination, Logistics, Budget agents in parallel
    4. Merges outputs into day-by-day itinerary
    **Phase 0 Fallback**: Returns stub response if no LLM configured.
    """
    import time
    start_time = time.time()
    
    trace_id = getattr(request.state, "trace_id", "unknown")
    
    # Phase 5: Full orchestration pipeline
    try:
        from ..agents import OrchestratorAgent
        from ..llm import get_groq_client, TokenBudgetExceeded
        
        # Initialize orchestrator with Groq client
        groq_client = get_groq_client()
        orchestrator = OrchestratorAgent(llm_client=groq_client)
        
        # Run full pipeline: extract → validate 3 pillars → parallel agents → merge → final
        final_itinerary = await orchestrator.create_plan(plan_request.request, trace_id=trace_id)
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        return PlanResponse(
            final_itinerary=final_itinerary,
            constraints=final_itinerary.constraints,
            review_summary=final_itinerary.review_status,
            trace_id=trace_id,
            processing_time_ms=processing_time_ms,
            used_stub_mode=False
        )
        
    except MissingConstraintError as e:
        # STRICT 3-PILLAR VALIDATION FAILURE:
        # Return 400 with actionable feedback, not an API error or silent fake plan
        raise HTTPException(
            status_code=400,
            detail={
                "error": "missing_constraints",
                "message": e.message,
                "missing_fields": e.missing_fields,
                "suggested_tiers": e.suggested_tiers
            }
        )
        
    except (RuntimeError, TokenBudgetExceeded) as e:
        # LLM not available or token budget exceeded - use stub
        print(f"Using stub mode (LLM unavailable): {e}")
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        import re
        request_lower = plan_request.request.lower()
        request_text = plan_request.request
        
        # ── Extract destination ────────────────────────────────────────────
        cities = []
        stop = {'the','a','an','my','our','this','that','days','day','week','weeks',
                'month','months','trip','plan','budget','love','hate','with','and',
                'for','about','around','in','on','at','to','of','from','like','want',
                'need','looking','search','find','make','create','generate','build',
                'please','help','can','should','would','could','some','any','all',
                'i','me','we','us','it','is','am','are','be','do','have','has'}
        
        m = re.search(
            r'(?:trip\s+to|travel\s+to|visit|visiting|going\s+to|to|in|of)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)',
            request_text
        )
        if m:
            candidate = m.group(1).strip()
            if candidate.lower() not in stop and candidate.lower() != "search" and len(candidate) > 1:
                cities = [candidate.title()]
        
        if not cities:
            words = request_text.split()
            for w in words:
                clean = w.strip('",.!?;:()[]/\\\'')
                if clean and clean[0].isupper() and clean.lower() not in stop and len(clean) > 1:
                    if clean.lower() == "search": continue
                    cities = [clean.title()]
                    break
        
        if not cities:
            for w in request_text.split():
                clean = w.strip(',.!?;:')
                if clean.lower() not in stop and len(clean) > 3 and clean.isalpha():
                    cities = [clean.title()]
                    break
        
        has_destination = bool(cities and cities != ["World"])
        
        # ── Extract duration ───────────────────────────────────────────────
        duration = None
        weeks_match = re.search(r'(\d+)\s*-?\s*week', request_lower)
        if weeks_match:
            duration = int(weeks_match.group(1)) * 7
        else:
            days_match = re.search(r'(\d+)\s*-?\s*day', request_lower)
            if days_match:
                duration = int(days_match.group(1))
        
        # ── Extract budget & currency ───────────────────────────────────────
        budget = None
        currency = "INR"
        budget_patterns = [
            (r'\$\s*([\d,]+)', 'USD'),
            (r'€\s*([\d,]+)', 'EUR'),
            (r'£\s*([\d,]+)', 'GBP'),
            (r'¥\s*([\d,]+)', 'JPY'),
            (r'₹\s*([\d,]+)', 'INR'),
            (r'([\d,]+)\s*USD', 'USD'),
            (r'([\d,]+)\s*EUR', 'EUR'),
            (r'([\d,]+)\s*GBP', 'GBP'),
            (r'([\d,]+)\s*INR', 'INR'),
            (r'([\d,]+)\s*(?:budget)', 'INR'),
        ]
        for pat, cur in budget_patterns:
            bm = re.search(pat, request_text, re.IGNORECASE)
            if bm:
                budget = int(bm.group(1).replace(',', ''))
                currency = cur
                break
                
        # Check tier keywords if no exact budget
        tier = None
        if not budget:
            if any(k in request_lower for k in ["cheap", "backpack", "hostel", "tight budget"]):
                tier = "budget"
            elif any(k in request_lower for k in ["moderate", "mid-range", "comfort", "normal"]):
                tier = "moderate"
            elif any(k in request_lower for k in ["luxury", "5-star", "luxurious", "premium", "deluxe"]):
                tier = "luxury"
                
        # ── STRICT 3-PILLAR VALIDATION IN STUB MODE TOO ───────────────────
        missing_fields = []
        if not has_destination:
            missing_fields.append("destination")
        if not duration:
            missing_fields.append("duration")
        if not budget and not tier:
            missing_fields.append("budget")
            
        if missing_fields:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "missing_constraints",
                    "message": MissingConstraintError(missing_fields).message,
                    "missing_fields": missing_fields,
                    "suggested_tiers": [
                        {"tier": "budget", "label": "Budget / Backpacker (~$70/day)"},
                        {"tier": "moderate", "label": "Moderate / Comfortable (~$180/day)"},
                        {"tier": "luxury", "label": "Luxury / Premium (~$400+/day)"},
                    ]
                }
            )
            
        # Resolve tier to budget if duration and tier exist
        if not budget and tier and duration:
            daily_rates = {"budget": 70, "moderate": 180, "luxury": 400}
            rate = daily_rates.get(tier, 180)
            budget = duration * rate * 83
            currency = "INR"

        primary_city = cities[0]

        stub_constraints = TravelConstraints(
            destination_region=primary_city,
            cities=cities if cities else [primary_city],
            duration_days=duration,
            budget_total=budget,
            currency=currency,
            preferences=["Cultural experiences", "Local cuisine", "Sightseeing"],
            avoidances=[],
            hard_requirements=[],
            soft_preferences=[],
            is_road_trip=False,
        )

        # ── Generate generic stub days ─────────────────────────────────────
        stub_days = []
        if not cities:
            cities = [primary_city]

        themes = [
            ("Landmarks & Sightseeing", ActivityType.OTHER),
            ("Cultural Heritage & Museums", ActivityType.MUSEUM),
            ("Local Food & Markets", ActivityType.FOOD),
            ("Nature & Outdoors", ActivityType.NATURE),
            ("Neighborhoods & Local Life", ActivityType.OTHER),
        ]

        for day_num in range(1, duration + 1):
            day_city = cities[min((day_num - 1) % len(cities), len(cities) - 1)]

            if day_num == 1:
                day_items = [
                    DayItineraryItem(slot_index=0, time="09:00 - 14:00",
                        activity_id=f"arrival-{day_num}",
                        activity_name=f"Arrival in {cities[0]}",
                        city=cities[0], type=ActivityType.OTHER, cost_estimate=0.0,
                        notes=f"Arrive in {cities[0]}. Transfer to hotel, check-in, and explore the neighborhood."),
                    DayItineraryItem(slot_index=1, time="15:00 - 20:00",
                        activity_id=f"orient-{day_num}",
                        activity_name=f"Explore {cities[0]}",
                        city=cities[0], type=ActivityType.OTHER, cost_estimate=0.0,
                        notes=f"Walk through {cities[0]}. Visit a local cafe and enjoy dinner."),
                ]
                day_summary = f"Arrival in {cities[0]}"
                day_cost = 0.0
                day_city = cities[0]
            elif day_num == duration:
                day_items = [
                    DayItineraryItem(slot_index=0, time="09:00 - 12:00",
                        activity_id=f"final-{day_num}",
                        activity_name="Last Explorations",
                        city=day_city, type=ActivityType.OTHER, cost_estimate=0.0,
                        notes=f"Final morning in {primary_city}. Pick up souvenirs and farewell photos."),
                    DayItineraryItem(slot_index=1, time="13:00 - 18:00",
                        activity_id=f"departure-{day_num}",
                        activity_name="Departure",
                        city=day_city, type=ActivityType.TRANSPORT, cost_estimate=0.0,
                        notes=f"Transfer to airport. Depart from {primary_city}."),
                ]
                day_summary = f"Departure from {primary_city}"
                day_cost = 0.0
            else:
                theme_idx = (day_num - 2) % len(themes)
                title, atype = themes[theme_idx]
                day_items = [
                    DayItineraryItem(slot_index=0, time="09:00 - 13:00",
                        activity_id=f"explore-{day_num}",
                        activity_name=f"{day_city}: {title}",
                        city=day_city, type=atype, cost_estimate=40.0,
                        notes=f"Explore {title.lower()} in {day_city}."),
                    DayItineraryItem(slot_index=1, time="14:00 - 18:00",
                        activity_id=f"evening-{day_num}",
                        activity_name=f"Evening in {day_city}",
                        city=day_city, type=ActivityType.FOOD, cost_estimate=40.0,
                        notes=f"Local dining and evening in {day_city}."),
                ]
                day_summary = f"Day {day_num}: {title} in {day_city}"
                day_cost = 80.0

            stub_days.append(DayItinerary(
                day_number=day_num, city=day_city,
                items=day_items, day_summary=day_summary,
                day_cost=day_cost, lodging_area=f"{day_city} area"
            ))

        total_cost = sum(d.day_cost for d in stub_days)
        daily_rate = budget / max(1, duration)

        neighborhoods = {c: [f"Central {c}"] for c in cities}

        stub_itinerary = FinalItinerary(
            constraints=stub_constraints,
            days=stub_days,
            neighborhoods=neighborhoods,
            logistics_summary=f"Explore {primary_city} with local transport",
            budget_analysis=f"Budget of {budget:,} {currency} for {duration} days.",
            cost_optimization_tips=["Use public transport", "Eat at local restaurants", "Book accommodation early"],
            budget_rollup=BudgetBreakdown(
                categories=[
                    BudgetCategory(category="stay", estimated_total=round(budget * 0.35, 2), currency=currency, notes=f"{duration} nights"),
                    BudgetCategory(category="food", estimated_total=round(budget * 0.25, 2), currency=currency, notes="Daily meals"),
                    BudgetCategory(category="activities", estimated_total=round(budget * 0.20, 2), currency=currency, notes="Attractions"),
                    BudgetCategory(category="transport", estimated_total=round(budget * 0.20, 2), currency=currency, notes="Local transport"),
                ],
                grand_total=budget,
                currency=currency,
                within_budget=True,
                remaining_buffer=0
            ),
            review_status=ReviewStatus.PASS,
            disclaimer="Stub mode: LLM unavailable. Set GROQ_API_KEY for full AI-generated itineraries."
        )
        
        return PlanResponse(
            final_itinerary=stub_itinerary,
            constraints=stub_constraints,
            review_summary=ReviewStatus.PASS,
            trace_id=trace_id,
            processing_time_ms=processing_time_ms,
            used_stub_mode=True
        )



@router.get("/plan/{plan_id}", tags=["Planning"])
async def get_plan(plan_id: str):
    """
    Retrieve a previously generated plan by ID.
    **Phase 10**: Optional persistent storage.
    """
    raise HTTPException(status_code=501, detail="Persistent storage not yet implemented (Phase 10)")


@router.get("/tokens/status", tags=["Monitoring"])
async def get_token_status():
    """
    Get current Groq token usage status.
    **Useful for monitoring daily budget (100k limit).**
    """
    from ..llm import get_token_tracker
    
    tracker = get_token_tracker()
    summary = tracker.get_usage_summary()
    
    return {
        "daily_limit": summary["daily_limit"],
        "daily_total": summary["daily_total"],
        "remaining": summary["remaining"],
        "percent_used": round(summary["percent_used"], 2),
        "effective_limit": summary["effective_limit"],
        "buffer_percent": summary["buffer_percent"],
        "request_count": summary["request_count"],
        "by_model": summary.get("by_model", {}),
        "next_reset": summary.get("next_reset"),
    }


@router.post("/tokens/reset-cache", tags=["Monitoring"])
async def reset_response_cache():
    """
    Clear the LLM response cache.
    **Useful for testing or when cache is stale.**
    """
    from ..llm import get_cache
    
    cache = get_cache()
    stats_before = cache.get_stats()
    cache.clear()
    
    return {
        "status": "cache_cleared",
        "previous_entries": stats_before["entries"],
        "previous_hits": stats_before["hits"],
    }
