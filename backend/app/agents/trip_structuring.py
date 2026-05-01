"""
Trip Structuring Agent — New hierarchical planning layer.
Converts TravelConstraints into structured regions and route plan
BEFORE the parallel worker agents execute.
"""

from typing import List, Optional
from ..models.schemas import TravelConstraints, TripStructure, Region


# Known road trip route databases
ROAD_TRIP_ROUTES = {
    "iceland": {
        "route": ["Reykjavik", "Golden Circle", "South Coast", "Vik", "Skaftafell",
                  "Hofn", "East Fjords", "Myvatn", "Akureyri", "Snaefellsnes", "Reykjavik"],
        "regions": [
            Region(name="Reykjavik & Golden Circle", base_location="Reykjavik", days=3,
                   highlights=["Hallgrimskirkja", "Thingvellir", "Geysir", "Gullfoss", "Blue Lagoon"]),
            Region(name="South Coast", base_location="Vik", days=3,
                   highlights=["Seljalandsfoss", "Skogafoss", "Reynisfjara Black Beach", "Dyrholaey"]),
            Region(name="Glacier Region", base_location="Hofn", days=3,
                   highlights=["Skaftafell Glacier", "Svartifoss", "Jokulsarlon Lagoon", "Diamond Beach"]),
            Region(name="East Fjords", base_location="Egilsstadir", days=2,
                   highlights=["Seydisfjordur", "Lagarfljot", "East Fjord villages"]),
            Region(name="North Iceland", base_location="Akureyri", days=3,
                   highlights=["Godafoss", "Myvatn", "Husavik whale watching", "Dettifoss"]),
            Region(name="West Iceland & Snaefellsnes", base_location="Borgarnes", days=2,
                   highlights=["Kirkjufell", "Arnarstapi", "Hraunfossar", "Snaefellsjokull"]),
        ]
    },
    "norway": {
        "route": ["Oslo", "Bergen", "Flam", "Geiranger", "Alesund", "Tromso"],
        "regions": [
            Region(name="Oslo", base_location="Oslo", days=2,
                   highlights=["Opera House", "Vigeland Park", "Viking Ship Museum"]),
            Region(name="Bergen & Fjords", base_location="Bergen", days=3,
                   highlights=["Bryggen", "Floibanen", "Flam Railway", "Sognefjorden"]),
            Region(name="Geirangerfjord", base_location="Geiranger", days=2,
                   highlights=["Geirangerfjord cruise", "Trollstigen", "Seven Sisters"]),
            Region(name="Northern Norway", base_location="Tromso", days=3,
                   highlights=["Arctic Cathedral", "Northern Lights", "Whale safari"]),
        ]
    },
    "new zealand": {
        "route": ["Auckland", "Rotorua", "Taupo", "Wellington", "Kaikoura", "Queenstown", "Milford Sound"],
        "regions": [
            Region(name="Auckland & Northland", base_location="Auckland", days=2,
                   highlights=["Sky Tower", "Waiheke Island", "Hobbiton"]),
            Region(name="Rotorua & Taupo", base_location="Rotorua", days=3,
                   highlights=["Geothermal parks", "Maori culture", "Lake Taupo", "Tongariro"]),
            Region(name="Wellington", base_location="Wellington", days=2,
                   highlights=["Te Papa Museum", "Cable Car", "Cuba Street"]),
            Region(name="South Island Highlights", base_location="Queenstown", days=4,
                   highlights=["Milford Sound", "Bungee jumping", "Lake Wanaka", "Remarkables"]),
        ]
    },
    "scotland": {
        "route": ["Edinburgh", "Stirling", "Glencoe", "Isle of Skye", "Inverness", "Glasgow"],
        "regions": [
            Region(name="Edinburgh", base_location="Edinburgh", days=2,
                   highlights=["Edinburgh Castle", "Royal Mile", "Arthur's Seat"]),
            Region(name="Highlands", base_location="Fort William", days=3,
                   highlights=["Glencoe", "Ben Nevis", "Glenfinnan Viaduct"]),
            Region(name="Isle of Skye", base_location="Portree", days=2,
                   highlights=["Old Man of Storr", "Fairy Pools", "Quiraing"]),
            Region(name="Inverness & Loch Ness", base_location="Inverness", days=2,
                   highlights=["Loch Ness", "Urquhart Castle", "Culloden"]),
        ]
    },
    "switzerland": {
        "route": ["Zurich", "Lucerne", "Interlaken", "Zermatt", "Geneva"],
        "regions": [
            Region(name="Zurich & Lucerne", base_location="Lucerne", days=2,
                   highlights=["Chapel Bridge", "Lake Lucerne", "Mount Pilatus"]),
            Region(name="Bernese Oberland", base_location="Interlaken", days=3,
                   highlights=["Jungfraujoch", "Grindelwald", "Lauterbrunnen", "Lake Brienz"]),
            Region(name="Zermatt & Matterhorn", base_location="Zermatt", days=2,
                   highlights=["Matterhorn", "Gornergrat", "Glacier Paradise"]),
            Region(name="Geneva & Lausanne", base_location="Geneva", days=2,
                   highlights=["Jet d'Eau", "Lake Geneva", "Montreux"]),
        ]
    },
    "ireland": {
        "route": ["Dublin", "Kilkenny", "Cork", "Ring of Kerry", "Cliffs of Moher", "Galway"],
        "regions": [
            Region(name="Dublin", base_location="Dublin", days=2,
                   highlights=["Trinity College", "Temple Bar", "Guinness Storehouse"]),
            Region(name="South Ireland", base_location="Cork", days=2,
                   highlights=["Blarney Castle", "Kilkenny", "Rock of Cashel"]),
            Region(name="Kerry & Ring of Kerry", base_location="Killarney", days=3,
                   highlights=["Ring of Kerry", "Killarney National Park", "Dingle Peninsula"]),
            Region(name="West Ireland", base_location="Galway", days=2,
                   highlights=["Cliffs of Moher", "Aran Islands", "Connemara"]),
        ]
    },
    "portugal": {
        "route": ["Lisbon", "Sintra", "Porto", "Douro Valley", "Algarve"],
        "regions": [
            Region(name="Lisbon & Sintra", base_location="Lisbon", days=3,
                   highlights=["Belem Tower", "Alfama", "Sintra palaces", "Cascais"]),
            Region(name="Porto & Douro", base_location="Porto", days=3,
                   highlights=["Ribeira", "Port wine cellars", "Douro Valley cruise"]),
            Region(name="Algarve Coast", base_location="Lagos", days=2,
                   highlights=["Ponta da Piedade", "Benagil Cave", "Faro"]),
        ]
    },
}

# Multi-city route databases
MULTI_CITY_ROUTES = {
    "japan": {
        "route": ["Tokyo", "Hakone", "Kyoto", "Osaka"],
        "regions": [
            Region(name="Tokyo", base_location="Tokyo", days=3,
                   highlights=["Senso-ji", "Shibuya", "TeamLab", "Tsukiji"]),
            Region(name="Hakone", base_location="Hakone", days=1,
                   highlights=["Mt. Fuji views", "Hakone Shrine", "Hot springs"]),
            Region(name="Kyoto", base_location="Kyoto", days=3,
                   highlights=["Fushimi Inari", "Kinkaku-ji", "Arashiyama", "Gion"]),
            Region(name="Osaka", base_location="Osaka", days=2,
                   highlights=["Dotonbori", "Osaka Castle", "Street food"]),
        ]
    },
    "italy": {
        "route": ["Rome", "Florence", "Cinque Terre", "Venice"],
        "regions": [
            Region(name="Rome", base_location="Rome", days=3,
                   highlights=["Colosseum", "Vatican", "Trastevere", "Pantheon"]),
            Region(name="Florence & Tuscany", base_location="Florence", days=3,
                   highlights=["Uffizi", "Duomo", "Ponte Vecchio", "Chianti"]),
            Region(name="Cinque Terre", base_location="Monterosso", days=2,
                   highlights=["Five villages", "Hiking trails", "Seafood"]),
            Region(name="Venice", base_location="Venice", days=2,
                   highlights=["St. Mark's", "Grand Canal", "Murano", "Burano"]),
        ]
    },
    "spain": {
        "route": ["Barcelona", "Madrid", "Seville", "Granada"],
        "regions": [
            Region(name="Barcelona", base_location="Barcelona", days=3,
                   highlights=["Sagrada Familia", "Park Guell", "Las Ramblas", "Gothic Quarter"]),
            Region(name="Madrid", base_location="Madrid", days=2,
                   highlights=["Prado Museum", "Retiro Park", "Plaza Mayor"]),
            Region(name="Andalusia", base_location="Seville", days=3,
                   highlights=["Alcazar", "Alhambra", "Flamenco", "Tapas"]),
        ]
    },
}


class TripStructuringAgent:
    """
    NEW agent that creates trip structure BEFORE parallel execution.
    Divides trips into logical regions with day allocations.
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    async def structure(self, constraints: TravelConstraints) -> TripStructure:
        """
        Convert TravelConstraints into a TripStructure with regions.
        
        Rules:
        - duration > 7 days → MUST create multiple regions
        - road trip destinations → use known route databases
        - Total allocated days MUST equal duration_days
        - Avoid assigning all days to one location
        """
        dest_lower = constraints.destination_region.lower().strip()
        duration = constraints.duration_days

        # Single city / short trip
        if duration <= 7 and len(constraints.cities) <= 2 and not constraints.is_road_trip:
            return self._structure_city_trip(constraints)

        # Check road trip routes first
        if dest_lower in ROAD_TRIP_ROUTES or constraints.is_road_trip:
            return self._structure_road_trip(dest_lower, duration, constraints)

        # Check multi-city routes
        if dest_lower in MULTI_CITY_ROUTES:
            return self._structure_multi_city(dest_lower, duration, constraints)

        # Long trip to unknown destination → create regions from cities
        return self._structure_from_cities(constraints)

    def _structure_road_trip(self, dest: str, duration: int, constraints: TravelConstraints) -> TripStructure:
        """Structure a road trip using known route databases."""
        route_data = ROAD_TRIP_ROUTES.get(dest)
        if not route_data:
            # Unknown road trip destination, fall back to cities
            return self._structure_from_cities(constraints)

        template_regions = route_data["regions"]
        route = route_data["route"]

        # Scale regions to fit duration
        regions = self._scale_regions_to_duration(template_regions, duration)

        return TripStructure(
            trip_type="road_trip",
            regions=regions,
            route=route,
            pace=self._determine_pace(duration, len(regions))
        )

    def _structure_multi_city(self, dest: str, duration: int, constraints: TravelConstraints) -> TripStructure:
        """Structure a multi-city trip."""
        route_data = MULTI_CITY_ROUTES.get(dest)
        if not route_data:
            return self._structure_from_cities(constraints)

        template_regions = route_data["regions"]
        route = route_data["route"]
        regions = self._scale_regions_to_duration(template_regions, duration)

        return TripStructure(
            trip_type="multi_region",
            regions=regions,
            route=route,
            pace=self._determine_pace(duration, len(regions))
        )

    def _structure_city_trip(self, constraints: TravelConstraints) -> TripStructure:
        """Structure a simple city trip (≤ 7 days, 1-2 cities)."""
        regions = []
        days_per_city = max(1, constraints.duration_days // len(constraints.cities))
        remainder = constraints.duration_days % len(constraints.cities)

        for i, city in enumerate(constraints.cities):
            extra = 1 if i < remainder else 0
            regions.append(Region(
                name=city,
                base_location=city,
                days=days_per_city + extra,
                highlights=[]
            ))

        return TripStructure(
            trip_type="city_trip",
            regions=regions,
            route=constraints.cities,
            pace="relaxed" if constraints.duration_days >= 5 else "balanced"
        )

    def _structure_from_cities(self, constraints: TravelConstraints) -> TripStructure:
        """Structure from the cities list when no route template exists."""
        cities = constraints.cities
        duration = constraints.duration_days

        if len(cities) == 1:
            # Single city, long trip — split into neighborhoods/areas
            city = cities[0]
            if duration <= 3:
                regions = [Region(name=city, base_location=city, days=duration, highlights=[])]
            else:
                # Split into exploration phases
                half = duration // 2
                regions = [
                    Region(name=f"{city} Central", base_location=city, days=half,
                           highlights=["City landmarks", "Museums", "Markets"]),
                    Region(name=f"{city} Surroundings", base_location=city, days=duration - half,
                           highlights=["Day trips", "Nature", "Local experiences"]),
                ]
        else:
            # Distribute days across cities
            days_per = max(1, duration // len(cities))
            remainder = duration % len(cities)
            regions = []
            for i, city in enumerate(cities):
                extra = 1 if i < remainder else 0
                regions.append(Region(
                    name=city,
                    base_location=city,
                    days=days_per + extra,
                    highlights=[]
                ))

        return TripStructure(
            trip_type="multi_region" if len(regions) > 1 else "city_trip",
            regions=regions,
            route=[r.base_location for r in regions],
            pace=self._determine_pace(duration, len(regions))
        )

    def _scale_regions_to_duration(self, template_regions: List[Region], duration: int) -> List[Region]:
        """Scale template regions to fit the actual trip duration."""
        template_total = sum(r.days for r in template_regions)

        if template_total == duration:
            return [r.model_copy() for r in template_regions]

        # Scale proportionally
        scale = duration / template_total
        scaled = []

        for region in template_regions:
            days = max(1, round(region.days * scale))
            scaled.append(Region(
                name=region.name,
                base_location=region.base_location,
                days=days,
                highlights=region.highlights.copy()
            ))

        # Ensure total equals duration
        while sum(r.days for r in scaled) != duration:
            total = sum(r.days for r in scaled)
            if total < duration:
                # Add to largest
                largest_idx = max(range(len(scaled)), key=lambda i: scaled[i].days)
                scaled[largest_idx] = Region(
                    name=scaled[largest_idx].name,
                    base_location=scaled[largest_idx].base_location,
                    days=scaled[largest_idx].days + 1,
                    highlights=scaled[largest_idx].highlights.copy()
                )
            else:
                # Subtract from largest that has > 1 day
                candidates = [i for i, r in enumerate(scaled) if r.days > 1]
                if not candidates:
                    break  # Cannot reduce further
                largest_idx = max(candidates, key=lambda i: scaled[i].days)
                scaled[largest_idx] = Region(
                    name=scaled[largest_idx].name,
                    base_location=scaled[largest_idx].base_location,
                    days=scaled[largest_idx].days - 1,
                    highlights=scaled[largest_idx].highlights.copy()
                )

        return scaled

    def _determine_pace(self, duration: int, num_regions: int) -> str:
        """Determine trip pace based on days-per-region ratio."""
        if num_regions == 0:
            return "balanced"
        ratio = duration / num_regions
        if ratio >= 3:
            return "relaxed"
        elif ratio >= 2:
            return "balanced"
        else:
            return "aggressive"
