# 🚀 AI Travel Planner — Improvement Patch (v1.0)

## 🎯 Goal

Fix poor itinerary quality for long-duration and multi-region trips (e.g., 10–15 day Iceland trips) by introducing **hierarchical trip planning (structure → execution)**.

This patch is designed to integrate with the existing architecture without rewriting the system.

---

# 🔴 Problem Summary

Current pipeline:

```
Orchestrator → parallel(Destination, Logistics, Budget) → Merge → Review
```

Issue:

* Works for short, city-based trips
* Fails for long trips due to:

  * No route or region planning
  * Repetitive daily structure
  * No geographic progression
  * Budget not influencing planning early

---

# 🟢 Core Fix: Introduce Trip Structuring Layer

## New Pipeline

```
User
 ↓
Orchestrator (extract constraints)
 ↓
TripStructuringAgent   ← NEW
 ↓
parallel (per region):
   → Destination Agent
   → Logistics Agent
   → Budget Agent
 ↓
Merge
 ↓
Review
 ↓
Repair
 ↓
Final Itinerary
```

---

# 🧩 1. Add TripStructuringAgent

## File

```
backend/app/agents/trip_structuring.py
```

## Function

```python
async def run_trip_structuring(constraints: TravelConstraints) -> TripStructure:
    """
    Converts TravelConstraints into structured regions and route plan.
    """
```

## Output Schema

```json
{
  "trip_type": "city_trip | road_trip | multi_region",
  "regions": [
    {
      "name": "South Coast",
      "base_location": "Vik",
      "days": 3
    }
  ],
  "route": ["Reykjavik", "South Coast", "East Fjords", "North Iceland"],
  "pace": "relaxed | balanced | aggressive"
}
```

## Rules

* If `duration_days > 7` → MUST create multiple regions
* If destination is geographically spread → use `road_trip`
* Total allocated days must equal `duration_days`
* Avoid assigning all days to one location

---

# 🧠 2. Update Orchestrator

## Modify `create_plan()` flow

### BEFORE

```python
destination = await destination_agent(constraints)
logistics = await logistics_agent(constraints)
budget = await budget_agent(constraints)
```

### AFTER

```python
# Step 1: Structure trip
trip_structure = await run_trip_structuring(constraints)

# Step 2: Execute per region
all_destinations = []
all_logistics = []
all_budgets = []

for region in trip_structure.regions:
    region_context = {
        "region_name": region["name"],
        "days": region["days"],
        "base_location": region["base_location"]
    }

    dest = await destination_agent(constraints, region_context)
    log = await logistics_agent(constraints, region_context)
    bud = await budget_agent(constraints, region_context)

    all_destinations.append(dest)
    all_logistics.append(log)
    all_budgets.append(bud)

# Step 3: Merge
draft = merge(all_destinations, all_logistics, all_budgets, trip_structure)
```

---

# 🌍 3. Update Destination Agent

## Change Signature

```python
async def destination_agent(constraints, region_context)
```

## Behavior

* Generate activities specific to region
* Avoid duplicate activities across regions
* Tag all outputs with region name

---

# 🛣️ 4. Update Logistics Agent

## Add Route Awareness

### New Output Field

```json
"route_plan": {
  "mode": "self_drive | train | flight",
  "loop": true,
  "start": "Reykjavik",
  "end": "Reykjavik",
  "daily_travel_hours": [3, 5, 4]
}
```

## Rules

* If `trip_type == road_trip`:

  * enforce route progression
  * avoid backtracking
* Assign lodging per region (not global)

---

# 💰 5. Update Budget Agent

## Change Behavior

### BEFORE

* Validates total cost

### AFTER

* Allocates budget per region
* Suggests:

  * cheaper lodging areas
  * alternative activities
  * transport adjustments

---

# 🔁 6. Scaling Logic (Orchestrator Rule)

Add:

```python
if constraints.duration_days > 7:
    use_trip_structuring = True
else:
    use_trip_structuring = False
```

If false:

* fallback to existing pipeline

---

# 🧪 7. Enhance Review Agent

## Add Checks

### Geographic Progression

* No unrealistic backtracking

### Coverage

* Trips >7 days must include multiple regions

### Diversity

* No repeated daily templates

### Travel Realism

* Daily travel time ≤ 6–7 hours

---

# 🔄 8. Repair Logic Update

If review fails:

* Rebalance region day allocation
* Remove duplicate activities
* Fix route ordering
* Adjust cost-heavy segments

Max retries: 3

---

# 🧠 9. Global Prompt Update (ALL AGENTS)

Add:

```
If trip duration > 7 days:
- Divide trip into logical regions
- Ensure progression across locations
- Avoid repeating the same daily structure
- Account for travel time between regions
```

---

# 🧱 10. Add Data Models

## TripStructure

```json
{
  "trip_type": "string",
  "regions": [],
  "route": [],
  "pace": "string"
}
```

## Region

```json
{
  "name": "string",
  "base_location": "string",
  "days": "number"
}
```

---

# ✅ Expected Output Change

## BEFORE

* Repetitive days
* No travel realism
* Weak long-trip handling

## AFTER

* Region-based itinerary
* Logical travel progression
* Diverse day structure
* Budget-aware planning

---

# 🧪 Test Case

Input:

```
15-day Iceland trip, ₹15,00,000 budget
```

Expected:

* Reykjavik + Golden Circle
* South Coast
* East Fjords
* North Iceland
* Logical route flow
* No repetition

---

# 🎯 Priority

## MUST

* TripStructuringAgent
* Orchestrator update
* Region-based planning

## HIGH IMPACT

* Logistics route logic
* Review enhancements

## OPTIONAL

* Budget influence

---

# END
