# Root Cause Analysis: Why Itineraries Are Generic

## 5 Critical Bugs Found

### Bug 1: Stub Mode Repeats the SAME Day Template (routes.py:213-238)
Every middle day generates:
- `"{primary_city} Cultural and Historic Tour"` ← THIS is why the user sees it
- Same notes: "Wake up to a pleasant morning..."
- **Zero variety** — Day 2 = Day 3 = Day 4 = ... = Day 14

### Bug 2: Everything is City-Locked
The entire pipeline forces `cities: List[str]` as the unit. 
- For Iceland, it picks "Reykjavik" as the only city
- Then generates 15 days ALL in Reykjavik
- Iceland is a ROUTE (Ring Road), not a city trip

### Bug 3: LLM Extraction Prompt Forces City Inference (groq_client.py:159)
> "If the user mentions a country but no cities, infer 1-2 major cities"
- For Iceland → picks Reykjavik
- For New Zealand → picks Auckland  
- Loses the entire character of these destinations

### Bug 4: Generic Fallback Activities (destination.py:635-723)
When city isn't in the hardcoded list:
- "Iconic {city} Landmark & Architecture Tour"
- "National Museum of {city}"
- These are meaningless for Vik, Hofn, Akureyri

### Bug 5: No Trip-Type Awareness
System doesn't distinguish:
- **City Trip**: Paris, Tokyo (neighborhood-focused)
- **Road Trip**: Iceland, Norway, NZ (route + regions)
- **Multi-City**: Japan (Tokyo → Kyoto)

## Fix Plan
1. Update extraction to generate **route stops** for road-trip countries
2. Overhaul stub mode with varied, region-specific day templates
3. Add destination-specific activity data for road trip regions
4. Make each day unique with different themes and locations
