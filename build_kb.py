"""Assemble the static knowledge for the Autonomous Trailer agent from public APIs.

Run once (needs internet) to refresh kb_data.json:

    python build_kb.py

Sources (all free, no API key, used within their published usage policies):
  * OpenStreetMap Nominatim  - town coordinates and county  (max 1 request/second, custom User-Agent)
  * OSRM public demo server  - real driving distance and time for every road in the graph
  * Open-Meteo Elevation API - altitude of every town (used to detect steep grades)
  * Wikipedia REST API       - a short description of every town

The road network itself (towns, roads, class distances) comes from Practical Exercise 3.
Live weather is NOT stored here; the notebook fetches it at run time because it changes.
"""

import json
import time
from datetime import datetime, timezone

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

HEADERS = {"User-Agent": "KnowledgeEngineering-AutonomousTrailer/1.0 (student coursework)"}
OUTPUT = "kb_data.json"

# Practical Exercise 3: two-way roads and their distances (km).
ROADS = [
    ("Nairobi", "Thika", 45),
    ("Thika", "Murang'a", 45),
    ("Murang'a", "Nyeri", 65),
    ("Nyeri", "Nanyuki", 60),
    ("Nyeri", "Nyahururu", 95),
    ("Nyahururu", "Nakuru", 70),
    ("Nairobi", "Limuru", 32),
    ("Limuru", "Naivasha", 67),
    ("Naivasha", "Gilgil", 31),
    ("Gilgil", "Nakuru", 35),
    ("Nakuru", "Kericho", 105),
    ("Nairobi", "Mai Mahiu", 58),
    ("Mai Mahiu", "Narok", 77),
    ("Narok", "Bomet", 96),
    ("Bomet", "Kericho", 57),
    ("Kericho", "Ahero", 72),
    ("Ahero", "Kisumu", 28),
]

REGIONS = {
    "Nairobi": "Nairobi",
    "Thika": "Central Highlands", "Murang'a": "Central Highlands",
    "Nyeri": "Central Highlands", "Nanyuki": "Central Highlands",
    "Limuru": "Rift Valley", "Naivasha": "Rift Valley", "Gilgil": "Rift Valley",
    "Nakuru": "Rift Valley", "Nyahururu": "Rift Valley", "Mai Mahiu": "Rift Valley",
    "Narok": "Rift Valley", "Bomet": "Rift Valley",
    "Kericho": "Lake Victoria Basin", "Ahero": "Lake Victoria Basin", "Kisumu": "Lake Victoria Basin",
}

# Wikipedia article titles where they differ from the town name.
WIKI_TITLES = {"Murang'a": "Murang'a", "Mai Mahiu": "Mai Mahiu"}


SESSION = requests.Session()
SESSION.headers.update(HEADERS)
SESSION.mount("https://", HTTPAdapter(max_retries=Retry(total=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])))


def get(url, **params):
    response = SESSION.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def geocode(town):
    """Nominatim: latitude, longitude and county of a Kenyan town.

    Many towns share their name with a county, and Nominatim may rank the county boundary
    first (its centroid can be 40+ km from the town). Only results that OSM addresses as a
    city, town or village are accepted.
    """
    for query in (f"{town}, Kenya", f"{town} Town, Kenya"):
        results = get(
            "https://nominatim.openstreetmap.org/search",
            q=query, format="json", limit=8, countrycodes="ke", addressdetails=1,
        )
        places = [r for r in results if r.get("addresstype") in ("city", "town", "village")]
        if places:
            result = places[0]
            break
        time.sleep(1.1)
    else:
        raise LookupError(f"Nominatim found no populated place called {town}")
    address = result.get("address", {})
    county = address.get("state") or address.get("county") or "Unknown"  # Kenyan counties are OSM "state"
    return float(result["lat"]), float(result["lon"]), county


def elevations(coords):
    """Open-Meteo: altitude (m) for a batch of (lat, lon) pairs."""
    data = get(
        "https://api.open-meteo.com/v1/elevation",
        latitude=",".join(f"{lat:.5f}" for lat, _ in coords),
        longitude=",".join(f"{lon:.5f}" for _, lon in coords),
    )
    return data["elevation"]


def describe(town):
    """Wikipedia: one-line description of a town."""
    title = WIKI_TITLES.get(town, town).replace(" ", "_")
    data = get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}")
    sentence = data.get("extract", "").split(". ")[0].strip()
    url = data.get("content_urls", {}).get("desktop", {}).get("page", "")
    return sentence.rstrip(".") + "." if sentence else "", url


def drive(a, b):
    """OSRM: driving distance (km) and time (min) between two coordinates."""
    (lat1, lon1), (lat2, lon2) = a, b
    data = get(
        f"https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}",
        overview="false",
    )
    route = data["routes"][0]
    return round(route["distance"] / 1000, 1), round(route["duration"] / 60, 1)


def main():
    towns = {}
    for town in REGIONS:
        lat, lon, county = geocode(town)
        description, url = describe(town)
        towns[town] = {
            "lat": lat, "lon": lon, "county": county, "region": REGIONS[town],
            "description": description, "wikipedia": url,
        }
        print(f"{town:<10} {lat:8.4f} {lon:8.4f}  {county}")
        time.sleep(1.1)  # Nominatim usage policy: at most one request per second

    for town, metres in zip(towns, elevations([(t["lat"], t["lon"]) for t in towns.values()])):
        towns[town]["elevation_m"] = round(metres)

    roads = []
    for a, b, km in ROADS:
        osrm_km, minutes = drive((towns[a]["lat"], towns[a]["lon"]), (towns[b]["lat"], towns[b]["lon"]))
        roads.append({"a": a, "b": b, "km_class": km, "km_osrm": osrm_km, "minutes_osrm": minutes})
        print(f"{a:>10} - {b:<10} class {km:>4} km   OSRM {osrm_km:>6} km  {minutes:>6} min")
        time.sleep(1.1)

    trip_km, trip_min = drive(
        (towns["Nairobi"]["lat"], towns["Nairobi"]["lon"]), (towns["Kisumu"]["lat"], towns["Kisumu"]["lon"])
    )

    kb = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sources": {
            "roads": "Practical Exercise 3 (class road graph)",
            "coordinates": "OpenStreetMap Nominatim (ODbL)",
            "road_distances": "OSRM demo server, OpenStreetMap data (ODbL)",
            "elevation": "Open-Meteo Elevation API (Copernicus DEM)",
            "descriptions": "Wikipedia REST API (CC BY-SA)",
        },
        "towns": towns,
        "roads": roads,
        "osrm_nairobi_kisumu": {"km": trip_km, "minutes": trip_min},
    }
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(kb, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(towns)} towns and {len(roads)} roads to {OUTPUT}")


if __name__ == "__main__":
    main()
