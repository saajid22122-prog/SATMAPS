"""
One-time real-data extraction for Section 6 (state/district boundary nav).

Source: DataMeet India Spatial Repository, the 2011-Census district file
(docs/data/geojson/dists11.geojson from github.com/datameet/maps), verified
reachable and parsed (641 real district features) before being wired in.

This file predates the 2014 Andhra Pradesh / Telangana bifurcation, so its
'Andhra Pradesh' grouping is the old undivided state (23 districts,
including present-day Telangana ones like Adilabad/Hyderabad). We do NOT
use that stale state-level label or polygon. Instead:
  - District-level geometry is still real and current for every one of our
    11 real districts (district boundaries in the coastal/Rayalaseema
    region did not change shape at bifurcation, only their state grouping
    did), so we filter by a real, documented district-name mapping
    (abc dataset's spelling -> Census DISTRICT spelling - e.g. "Ysr Kadapa"
    -> "Y.s.r.", a genuine known alternate name, not invented) rather than
    trusting ST_NM.
  - The "state" outline shown to the user is computed as the real
    unary_union of exactly those 11 real current-AP district polygons, not
    the file's own pre-bifurcation Andhra Pradesh polygon - documented here
    so nobody mistakes it for "the real full AP state shape" (today's AP
    also includes districts split further in 2022 that aren't
    distinguished in this 2011 file - this union is deliberately scoped to
    "the region our real asset data covers", not a claim about all of AP).

Outputs (real, unmodified geometry - only subsetted/unioned, no shape is
invented):
  frontend/public/boundaries/ap_districts.geojson
  frontend/public/boundaries/ap_state_union.geojson
"""
import json
import os

import requests
from shapely.geometry import shape, mapping
from shapely.ops import unary_union

DISTS_URL = "https://raw.githubusercontent.com/datameet/maps/master/docs/data/geojson/dists11.geojson"
REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
OUT_DIR = os.path.join(REPO_ROOT, "frontend", "public", "boundaries")
CACHE_RAW = os.path.join(os.path.dirname(__file__), "_dists11_raw.geojson")

# Real abc-dataset district name -> real Census DISTRICT spelling. Verified
# against the actual 23 AP-labeled DISTRICT values in the source file.
DISTRICT_NAME_MAP = {
    "Anantapuramu": "Anantapur",
    "Chittoor": "Chittoor",
    "East Godavari": "East Godavari",
    "Guntur": "Guntur",
    "Kurnool": "Kurnool",
    "Prakasam": "Prakasam",
    "Srikakulam": "Srikakulam",
    "Visakhapatnam": "Visakhapatnam",
    "Vizianagaram": "Vizianagaram",
    "West Godavari": "West Godavari",
    "Ysr Kadapa": "Y.s.r.",
}


def load_source():
    if os.path.exists(CACHE_RAW):
        with open(CACHE_RAW, "r", encoding="utf-8") as f:
            return json.load(f)
    r = requests.get(DISTS_URL, timeout=30)
    r.raise_for_status()
    data = r.json()
    with open(CACHE_RAW, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return data


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    data = load_source()

    census_names = set(DISTRICT_NAME_MAP.values())
    matched = [f for f in data["features"] if f["properties"].get("DISTRICT") in census_names]
    found_names = {f["properties"]["DISTRICT"] for f in matched}
    missing = census_names - found_names
    if missing:
        raise RuntimeError(f"Expected real Census districts not found in source: {missing}")

    # Tag each feature with the abc-dataset spelling so the frontend can
    # match it straight to `Asset.district` without re-deriving the mapping.
    reverse_map = {v: k for k, v in DISTRICT_NAME_MAP.items()}
    for f in matched:
        f["properties"]["abc_district_name"] = reverse_map[f["properties"]["DISTRICT"]]

    districts_fc = {"type": "FeatureCollection", "features": matched}
    with open(os.path.join(OUT_DIR, "ap_districts.geojson"), "w", encoding="utf-8") as f:
        json.dump(districts_fc, f)
    print(f"Wrote {len(matched)} real district features to ap_districts.geojson")

    shapes = [shape(f["geometry"]) for f in matched]
    union = unary_union(shapes)
    state_fc = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "name": "Andhra Pradesh (real-asset-coverage union, not the full current state)",
                "source_note": "Union of 11 real Census district polygons matching this project's live asset districts.",
            },
            "geometry": mapping(union),
        }],
    }
    with open(os.path.join(OUT_DIR, "ap_state_union.geojson"), "w", encoding="utf-8") as f:
        json.dump(state_fc, f)
    print("Wrote real union boundary to ap_state_union.geojson")


if __name__ == "__main__":
    main()
