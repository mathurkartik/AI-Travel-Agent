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
    JAPAN_5D_TOKYO_KYOTO_3000_CONSTRAINTS,
)

router = APIRouter()


@router.post("/plan", response_model=PlanResponse, tags=["Planning"])
async def create_plan(request: Request, plan_request: PlanRequest):
    """
    Create a travel plan from natural language request.
    
    **Phase 5**: Full orchestration with parallel worker agents.
    1. Extracts constraints using Groq LLM
    2. Runs Destination, Logistics, Budget agents in parallel
    3. Merges outputs into day-by-day itinerary
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
        
        # Run full pipeline: extract → parallel agents → merge → final (Phase 8: with trace_id)
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
        
    except (RuntimeError, TokenBudgetExceeded) as e:
        # LLM not available or budget exceeded - use stub
        print(f"Using stub mode (LLM unavailable): {e}")
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Extract basic info from request for personalized stub
        import re
        request_lower = plan_request.request.lower()
        request_text = plan_request.request
        
        # ── Extract destination ────────────────────────────────────────────
        cities = []
        # Stopwords that should never be treated as a destination
        stop = {'the','a','an','my','our','this','that','days','day','week','weeks',
                'month','months','trip','plan','budget','love','hate','with','and',
                'for','about','around','in','on','at','to','of','from','like','want',
                'need','looking','search','find','make','create','generate','build',
                'please','help','can','should','would','could','some','any','all',
                'i','me','we','us','it','is','am','are','be','do','have','has'}
        
        # Strategy 1: "trip to X", "visit X", "in X", "of X", "to X"
        m = re.search(
            r'(?:trip\s+to|travel\s+to|visit|visiting|going\s+to|to|in|of)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)',
            request_text
        )
        if m:
            candidate = m.group(1).strip()
            # If the candidate is "The Search", skip it (user noise)
            if candidate.lower() not in stop and candidate.lower() != "search" and len(candidate) > 1:
                cities = [candidate.title()]
        
        # Strategy 2: first capitalized word(s) not in stopwords
        if not cities:
            words = request_text.split()
            for w in words:
                clean = w.strip('",.!?;:()[]/\\')
                if clean and clean[0].isupper() and clean.lower() not in stop and len(clean) > 1:
                    # Specific check for "The Search" or "Search" noise
                    if clean.lower() == "search": continue
                    cities = [clean.title()]
                    break
        
        # Strategy 3: find any word > 3 chars not in stop (best guess)
        if not cities:
            for w in request_text.split():
                clean = w.strip(',.!?;:')
                if clean.lower() not in stop and len(clean) > 3 and clean.isalpha():
                    cities = [clean.title()]
                    break
        
        if not cities:
            cities = ["World"]  # absolute last resort
        
        # ── Extract duration ───────────────────────────────────────────────
        duration = 5
        weeks_match = re.search(r'(\d+)\s*-?\s*week', request_lower)
        if weeks_match:
            duration = int(weeks_match.group(1)) * 7
        else:
            days_match = re.search(r'(\d+)\s*-?\s*day', request_lower)
            if days_match:
                duration = int(days_match.group(1))
        
        # ── Extract budget ─────────────────────────────────────────────────
        # Supports: $3000, 1500000 budget, budget 50000, "50000 INR", etc.
        budget = 50000  # default INR
        budget_patterns = [
            r'[\$€£₹]\s*([\d,]+)',               # $3000, ₹50000
            r'([\d,]+)\s*(?:INR|USD|EUR|GBP|budget)',  # 1500000 INR / 1500000 budget
            r'budget\s*[\$€£₹]?\s*([\d,]+)',      # budget 50000
        ]
        for pat in budget_patterns:
            bm = re.search(pat, request_text, re.IGNORECASE)
            if bm:
                budget = int(bm.group(1).replace(',', ''))
                break

        
        primary_city = cities[0]
        
        # Create rich narrative stub constraints
        stub_constraints = TravelConstraints(
            destination_region=f"{primary_city} Region (stub mode)",
            cities=cities,
            duration_days=duration,
            budget_total=budget,
            currency="INR",
            preferences=["Cultural experiences", "Local cuisine", "Sightseeing"],
            avoidances=[],
            hard_requirements=[],
            soft_preferences=[]
        )
        
        # Generate rich narrative days based on extracted info
        stub_days = []
        for day_num in range(1, duration + 1):
            if day_num == 1:
                day_items = [
                    DayItineraryItem(
                        slot_index=0,
                        time="09:00 - 12:00",
                        activity_id=f"arrival-{day_num}",
                        activity_name=f"Arrival in {primary_city}. Welcome to your destination.",
                        city=primary_city,
                        type=ActivityType.OTHER,
                        cost_estimate=0.0,
                        notes=f"Arrive at {primary_city} International Airport. Complete immigration and collect baggage. Meet your representative for transfers to the hotel. Check-in and rest for the day. Overnight stay in {primary_city}."
                    ),
                    DayItineraryItem(
                        slot_index=1,
                        time="14:00 - 18:00",
                        activity_id=f"explore-{day_num}",
                        activity_name=f"Welcome to {primary_city} - City Orientation",
                        city=primary_city,
                        type=ActivityType.OTHER,
                        cost_estimate=0.0,
                        notes=f"Wake up to a pleasant morning and have your breakfast at the hotel. Take a leisurely walk around your hotel neighborhood to get acquainted with {primary_city}. Explore nearby cafes, local shops, and get a feel for the city's atmosphere."
                    ),
                ]
                day_summary = f"Arrival in {primary_city}"
                day_cost = 0.0  # Must match sum of item cost_estimates
            elif day_num == duration:
                day_items = [
                    DayItineraryItem(
                        slot_index=0,
                        time="09:00 - 12:00",
                        activity_id=f"final-{day_num}",
                        activity_name=f"Last Minute Exploration and Souvenirs",
                        city=primary_city,
                        type=ActivityType.SHOPPING,
                        cost_estimate=0.0,
                        notes=f"Wake up to a pleasant morning and have your breakfast at the hotel. Visit local markets or shopping districts for last-minute souvenirs. Take final photos of {primary_city} landmarks."
                    ),
                    DayItineraryItem(
                        slot_index=1,
                        time="14:00 - 18:00",
                        activity_id=f"departure-{day_num}",
                        activity_name=f"Departure. Take a bag of happy memories.",
                        city=primary_city,
                        type=ActivityType.TRANSPORT,
                        cost_estimate=0.0,
                        notes=f"Get ready and board your transfers to the airport. Your amazing {primary_city} trip concludes once you are dropped off at the airport for your onward journey. Depart with cultural experiences, scenic pictures, and happy memories."
                    ),
                ]
                day_summary = f"Departure from {primary_city}"
                day_cost = 0.0  # Must match sum of item cost_estimates (0.0 + 0.0)
            else:
                # Middle days with rich narratives
                day_items = [
                    DayItineraryItem(
                        slot_index=0,
                        time="09:00 - 13:00",
                        activity_id=f"sightseeing-{day_num}",
                        activity_name=f"{primary_city} Cultural and Historic Tour",
                        city=primary_city,
                        type=ActivityType.MUSEUM,
                        cost_estimate=30.0,
                        notes=f"Wake up to a pleasant morning and have your breakfast at the hotel. Today, board your transfers to explore {primary_city}'s famous cultural sites and historic landmarks. Visit iconic museums, monuments, and architectural wonders. Learn about the city's rich history and heritage from your guide."
                    ),
                    DayItineraryItem(
                        slot_index=1,
                        time="14:00 - 18:00",
                        activity_id=f"experience-{day_num}",
                        activity_name=f"Local Experiences and Cuisine",
                        city=primary_city,
                        type=ActivityType.FOOD,
                        cost_estimate=50.0,
                        notes=f"Enjoy lunch at a local restaurant featuring authentic {primary_city} cuisine. Continue exploring neighborhoods, visit local markets, and experience the city's vibrant culture. Take plenty of photos and soak in the atmosphere. Return to hotel for overnight stay."
                    ),
                ]
                day_summary = f"Explore {primary_city} - Day {day_num}"
                day_cost = 80.0  # Matches sum: 30.0 + 50.0
            
            stub_days.append(DayItinerary(
                day_number=day_num,
                city=primary_city,
                items=day_items,
                day_summary=day_summary,
                day_cost=day_cost,
                lodging_area=f"{primary_city} City Center"
            ))
        
        # Calculate total cost
        total_cost = sum(d.day_cost for d in stub_days)
        
        stub_itinerary = FinalItinerary(
            constraints=stub_constraints,
            days=stub_days,
            neighborhoods={
                primary_city: ["City Center", "Historic District"]
            },
            logistics_summary=f"Explore {primary_city} - transfers and local transport",
            budget_rollup=BudgetBreakdown(
                categories=[
                    BudgetCategory(
                        category="stay",
                        estimated_total=duration * 5000.0,
                        currency="INR",
                        notes=f"{duration} nights in {primary_city} (mid-range)"
                    ),
                    BudgetCategory(
                        category="food",
                        estimated_total=duration * 2500.0,
                        currency="INR",
                        notes="Daily meals and local cuisine"
                    ),
                    BudgetCategory(
                        category="activities",
                        estimated_total=duration * 3000.0,
                        currency="INR",
                        notes="Attractions and experiences"
                    ),
                    BudgetCategory(
                        category="transport",
                        estimated_total=duration * 1500.0,
                        currency="INR",
                        notes="Local transport and transfers"
                    ),
                ],
                grand_total=duration * 12000.0,
                currency="INR",
                within_budget=budget >= (duration * 12000.0),
                remaining_buffer=max(0, budget - (duration * 12000.0))
            ),
            review_status=ReviewStatus.PASS,
            disclaimer="This is a stub response with narrative-style itineraries. Set GROQ_API_KEY for LLM-powered detailed extraction and full orchestration with real-time data."
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
