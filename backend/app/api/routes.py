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
        
        if not cities:
            cities = ["World"]
        
        # ── Extract duration ───────────────────────────────────────────────
        duration = 5
        weeks_match = re.search(r'(\d+)\s*-?\s*week', request_lower)
        if weeks_match:
            duration = int(weeks_match.group(1)) * 7
        else:
            days_match = re.search(r'(\d+)\s*-?\s*day', request_lower)
            if days_match:
                duration = int(days_match.group(1))
        
        # ── Extract budget & currency ───────────────────────────────────────
        budget = 50000
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

        primary_city = cities[0]
        dest_lower = primary_city.lower()
        
        # ── Route-aware stop generation ────────────────────────────────────
        ROAD_TRIP_ROUTES = {
            "iceland": ["Reykjavik", "Golden Circle", "Vik", "Skaftafell", "Hofn", "Egilsstadir", "Akureyri", "Snaefellsnes"],
            "norway": ["Oslo", "Bergen", "Flam", "Geiranger", "Alesund", "Tromso"],
            "new zealand": ["Auckland", "Rotorua", "Taupo", "Wellington", "Queenstown", "Milford Sound", "Wanaka"],
            "scotland": ["Edinburgh", "Highlands", "Isle of Skye", "Inverness", "Glencoe", "Glasgow"],
            "ireland": ["Dublin", "Galway", "Cliffs of Moher", "Ring of Kerry", "Cork", "Killarney"],
            "portugal": ["Lisbon", "Sintra", "Porto", "Douro Valley", "Algarve"],
            "switzerland": ["Zurich", "Lucerne", "Interlaken", "Zermatt", "Geneva"],
            "japan": ["Tokyo", "Hakone", "Kyoto", "Nara", "Osaka"],
        }
        
        ROUTE_DAY_THEMES = {
            "iceland": [
                ("Reykjavik", "Reykjavik City Exploration", "Explore Hallgrimskirkja church, the harbor area, and Laugavegur shopping street. Visit the Harpa Concert Hall and enjoy local seafood at a downtown restaurant."),
                ("Golden Circle", "Golden Circle Day Trip", "Drive the famous Golden Circle route: Thingvellir National Park (UNESCO site where tectonic plates meet), Geysir geothermal area with erupting Strokkur, and the magnificent Gullfoss waterfall."),
                ("Blue Lagoon", "Blue Lagoon & Reykjanes Peninsula", "Visit the iconic Blue Lagoon geothermal spa. Explore the volcanic Reykjanes Peninsula with its lava fields, hot springs, and dramatic coastal cliffs."),
                ("South Coast", "South Coast Waterfalls", "Drive the scenic South Coast. Stop at Seljalandsfoss (walk behind the waterfall) and Skogafoss (climb 527 steps for panoramic views). Visit the Skogar Folk Museum."),
                ("Vik", "Black Sand Beach & Vik Village", "Explore Reynisfjara black sand beach with its basalt columns and sea stacks. Visit the charming village of Vik and hike to the Dyrholaey arch for puffin spotting."),
                ("Skaftafell", "Glacier Hiking & Ice Caves", "Hike on Skaftafell glacier in Vatnajokull National Park. Take a guided ice cave tour (seasonal). Visit Svartifoss waterfall surrounded by basalt columns."),
                ("Jokulsarlon", "Glacier Lagoon & Diamond Beach", "Visit Jokulsarlon glacier lagoon and take an amphibian boat tour among floating icebergs. Walk along Diamond Beach where ice chunks wash ashore on black sand."),
                ("Hofn", "East Iceland & Fjords Drive", "Drive through the dramatic East Fjords. Stop at fishing villages and scenic viewpoints. Enjoy fresh langoustine (lobster) in Hofn, the lobster capital of Iceland."),
                ("Egilsstadir", "Seydisfjordur & East Iceland", "Visit the colorful town of Seydisfjordur with its rainbow road and Nordic architecture. Explore Lagarfljot lake and the surrounding wilderness."),
                ("Myvatn", "Lake Myvatn Geothermal Wonders", "Explore the otherworldly Lake Myvatn area: Dimmuborgir lava formations, Grjotagja cave, Hverir geothermal mud pots, and relax at Myvatn Nature Baths."),
                ("Akureyri", "North Iceland & Whale Watching", "Visit Akureyri, the capital of the north. Take a whale watching tour from Husavik. See Godafoss (Waterfall of the Gods) and explore the Arctic botanical garden."),
                ("Dettifoss", "Dettifoss & Asbyrgi Canyon", "Visit Dettifoss, Europe's most powerful waterfall. Explore the horseshoe-shaped Asbyrgi canyon and the volcanic landscapes of Jokulsargljufur."),
                ("Snaefellsnes", "Snaefellsnes Peninsula", "Explore the 'Mini Iceland' peninsula: Kirkjufell mountain (most photographed), Arnarstapi coastal cliffs, Djupalonssandur black pebble beach, and Snaefellsjokull glacier."),
                ("Borgarnes", "West Iceland & Settlement Center", "Visit the Settlement Center in Borgarnes. Explore Hraunfossar and Barnafoss waterfalls. Discover Deildartunguhver, Europe's most powerful hot spring."),
                ("Reykjavik", "Return & Farewell", "Return to Reykjavik. Last-minute shopping on Laugavegur street. Visit any missed city attractions. Enjoy a farewell dinner at a top Reykjavik restaurant."),
            ],
            "thailand": [
                ("Bangkok", "Grand Palace & Riverside", "Explore the majestic Grand Palace and Wat Phra Kaew. Take a long-tail boat along the Chao Phraya River and visit Wat Arun (Temple of Dawn)."),
                ("Bangkok", "Street Food & Markets", "Experience the vibrant energy of Yaowarat (Chinatown). Sample world-famous street food and explore the bustling flower market and local canals."),
                ("Chiang Mai", "Old City & Temples", "Discover the ancient temples of Chiang Mai's Old City. Visit Wat Chedi Luang and Wat Phra Singh. Enjoy a traditional Khantoke dinner."),
                ("Chiang Mai", "Nature & Mountains", "Visit Doi Suthep Temple for panoramic views. Explore the lush gardens of Bhubing Palace and meet elephants at an ethical sanctuary."),
                ("Krabi", "Island Hopping & Beaches", "Take a boat tour to the Four Islands (Koh Poda, Chicken Island, Tup Island, Phranang Cave). Relax on the white sands of Railay Beach."),
                ("Phuket", "Old Town & Sunset Points", "Wander through the colorful streets of Phuket Old Town. Visit the Big Buddha and catch a spectacular sunset at Promthep Cape."),
            ],
            "india": [
                ("Delhi", "Historical Landmarks", "Visit the Red Fort, Jama Masjid, and Raj Ghat. Explore the bustling markets of Chandni Chowk in Old Delhi."),
                ("Agra", "Taj Mahal & Agra Fort", "Witness the sunrise at the iconic Taj Mahal. Explore the grand Agra Fort and visit the tomb of Itmad-ud-Daulah."),
                ("Jaipur", "Pink City Exploration", "Visit the Amber Fort, Hawa Mahal (Palace of Winds), and the City Palace. Shop for traditional handicrafts and jewelry."),
                ("Udaipur", "City of Lakes", "Enjoy a boat ride on Lake Pichola. Visit the stunning City Palace and the Jagdish Temple."),
                ("Goa", "Beaches & Old Goa", "Relax on the golden sands of Calangute or Baga beach. Visit the historic churches of Old Goa, including the Basilica of Bom Jesus."),
            ]
        }
        
        # Detect if this is a road trip destination or a major country
        is_road_trip = dest_lower in ROAD_TRIP_ROUTES
        if is_road_trip:
            route_stops = ROAD_TRIP_ROUTES[dest_lower]
            cities = route_stops[:min(6, len(route_stops))]
        elif dest_lower == "thailand":
            cities = ["Bangkok", "Chiang Mai", "Krabi", "Phuket"]
        elif dest_lower == "india":
            cities = ["Delhi", "Agra", "Jaipur", "Udaipur", "Goa"]
        elif dest_lower == "japan":
            cities = ["Tokyo", "Kyoto", "Osaka", "Hakone"]
        
        stub_constraints = TravelConstraints(
            destination_region=primary_city,
            cities=cities if cities else [primary_city],
            duration_days=duration,
            budget_total=budget,
            currency=currency,
            preferences=["Nature", "Scenic drives", "Local cuisine", "Adventure"] if is_road_trip else ["Cultural experiences", "Local cuisine", "Sightseeing"],
            avoidances=[],
            hard_requirements=[],
            soft_preferences=[],
            is_road_trip=is_road_trip,
        )
        
        # ── Generate varied days ───────────────────────────────────────────
        stub_days = []
        day_themes = ROUTE_DAY_THEMES.get(dest_lower, [])
        
        # Ensure we have at least one city
        if not cities:
            cities = [primary_city]
            
        for day_num in range(1, duration + 1):
            if day_num == 1:
                day_items = [
                    DayItineraryItem(slot_index=0, time="09:00 - 14:00",
                        activity_id=f"arrival-{day_num}",
                        activity_name=f"Arrival in {cities[0]}",
                        city=cities[0], type=ActivityType.OTHER, cost_estimate=0.0,
                        notes=f"Arrive at {cities[0]} airport. Pick up rental car (if road trip) or transfer to hotel. Check-in, rest, and explore the immediate neighborhood."),
                    DayItineraryItem(slot_index=1, time="15:00 - 20:00",
                        activity_id=f"orient-{day_num}",
                        activity_name=f"{cities[0]} Orientation & First Impressions",
                        city=cities[0], type=ActivityType.OTHER, cost_estimate=0.0,
                        notes=f"Take a leisurely walk through {cities[0]}. Visit a local cafe, explore the main streets, and enjoy your first dinner at a highly-rated local restaurant."),
                ]
                day_summary = f"Arrival & Orientation in {cities[0]}"
                day_cost = 0.0
                day_city = cities[0]
            elif day_num == duration:
                day_items = [
                    DayItineraryItem(slot_index=0, time="09:00 - 12:00",
                        activity_id=f"final-{day_num}",
                        activity_name="Last Explorations & Souvenirs",
                        city=cities[0], type=ActivityType.SHOPPING, cost_estimate=0.0,
                        notes=f"Final morning in {primary_city}. Pick up souvenirs, visit any remaining spots, and take farewell photos."),
                    DayItineraryItem(slot_index=1, time="13:00 - 18:00",
                        activity_id=f"departure-{day_num}",
                        activity_name="Departure",
                        city=cities[0], type=ActivityType.TRANSPORT, cost_estimate=0.0,
                        notes=f"Transfer to the airport. Depart with incredible memories of your {primary_city} adventure."),
                ]
                day_summary = f"Departure from {cities[0]}"
                day_cost = 0.0
                day_city = cities[0]
            elif day_themes and (day_num - 2) < len(day_themes):
                # Use destination-specific themed days
                theme = day_themes[day_num - 2]
                region, title, description = theme[0], theme[1], theme[2]
                day_city = region
                day_items = [
                    DayItineraryItem(slot_index=0, time="08:00 - 13:00",
                        activity_id=f"morning-{day_num}",
                        activity_name=title,
                        city=region, type=ActivityType.NATURE, cost_estimate=40.0,
                        notes=description),
                    DayItineraryItem(slot_index=1, time="14:00 - 19:00",
                        activity_id=f"afternoon-{day_num}",
                        activity_name=f"Afternoon in {region}",
                        city=region, type=ActivityType.FOOD, cost_estimate=40.0,
                        notes=f"Enjoy lunch featuring local {region} cuisine. Continue exploring the {region} area. Capture photos of the landmarks."),
                ]
                day_summary = f"Day {day_num}: {title}"
                day_cost = 80.0
            else:
                # Varied generic days (rotate themes)
                themes = [
                    ("Nature & Scenic Exploration", ActivityType.NATURE, f"Explore the natural landscapes around {primary_city}. Hike trails, visit viewpoints, and discover hidden gems."),
                    ("Cultural Heritage & Museums", ActivityType.MUSEUM, f"Visit {primary_city}'s most important museums and cultural sites. Learn about local history, art, and traditions."),
                    ("Local Markets & Food Tour", ActivityType.FOOD, f"Spend the day exploring local food markets, trying street food, and visiting artisan shops in {primary_city}."),
                    ("Adventure & Outdoor Activities", ActivityType.NATURE, f"Engage in outdoor activities: hiking, cycling, kayaking, or guided nature walks."),
                    ("Neighborhoods & Hidden Gems", ActivityType.OTHER, f"Explore lesser-known neighborhoods and off-the-beaten-path attractions."),
                ]
                theme_idx = (day_num - 2) % len(themes)
                title, atype, desc = themes[theme_idx]
                day_city = cities[min(day_num % len(cities), len(cities) - 1)] if is_road_trip or len(cities) > 1 else primary_city
                day_items = [
                    DayItineraryItem(slot_index=0, time="09:00 - 13:00",
                        activity_id=f"explore-{day_num}",
                        activity_name=f"{day_city}: {title}",
                        city=day_city, type=atype, cost_estimate=40.0,
                        notes=desc),
                    DayItineraryItem(slot_index=1, time="14:00 - 18:00",
                        activity_id=f"evening-{day_num}",
                        activity_name=f"Evening in {day_city}",
                        city=day_city, type=ActivityType.FOOD, cost_estimate=40.0,
                        notes=f"Enjoy local dining and evening atmosphere in {day_city}."),
                ]
                day_summary = f"Day {day_num}: {title} in {day_city}"
                day_cost = 80.0

            
            stub_days.append(DayItinerary(
                day_number=day_num, city=day_city,
                items=day_items, day_summary=day_summary,
                day_cost=day_cost, lodging_area=f"{day_city} area"
            ))
        
        total_cost = sum(d.day_cost for d in stub_days)
        
        # Regional pricing
        daily_rate = {"iceland": 18000, "norway": 16000, "switzerland": 17000,
                      "new zealand": 12000, "japan": 10000}.get(dest_lower, 12000)
        
        neighborhoods = {}
        for c in cities:
            neighborhoods[c] = [f"Central {c}", f"{c} area"]
        
        stub_itinerary = FinalItinerary(
            constraints=stub_constraints,
            days=stub_days,
            neighborhoods=neighborhoods,
            logistics_summary=("Ring Road self-drive route" if is_road_trip else f"Explore {primary_city} with local transport"),
            strategic_insight=(f"This {duration}-day itinerary covers the full {primary_city} Ring Road route with balanced pacing — no burnout, maximum coverage." if is_road_trip and dest_lower == "iceland" else None),
            budget_analysis=f"Your budget of {budget:,} {currency} for {duration} days is {'comfortable for a mid-range experience' if budget >= duration * daily_rate * 0.8 else 'tight — consider budget accommodations'}.",
            cost_optimization_tips=["Book accommodation early for best rates", "Cook some meals if self-catering available", "Look for free natural attractions"] if is_road_trip else ["Use public transport over taxis", "Eat at local restaurants instead of tourist spots"],
            budget_rollup=BudgetBreakdown(
                categories=[
                    BudgetCategory(category="stay", estimated_total=duration * daily_rate * 0.35, currency=currency, notes=f"{duration} nights ({primary_city} region)"),
                    BudgetCategory(category="food", estimated_total=duration * daily_rate * 0.2, currency=currency, notes="Daily meals"),
                    BudgetCategory(category="activities", estimated_total=duration * daily_rate * 0.2, currency=currency, notes="Attractions and experiences"),
                    BudgetCategory(category="transport", estimated_total=duration * daily_rate * 0.25, currency=currency, notes=("SUV rental + fuel" if is_road_trip else "Local transport")),
                ],
                grand_total=duration * daily_rate,
                currency=currency,
                within_budget=budget >= (duration * daily_rate),
                remaining_buffer=max(0, budget - (duration * daily_rate))
            ),
            review_status=ReviewStatus.PASS,
            disclaimer="Stub mode — set GROQ_API_KEY for full LLM-powered itineraries with real landmark data."
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
