"""
One-off: re-runs only compute_live_snapshot (real Sentinel-2 median NDWI +
Dynamic World mode-composite LULC + soil) for every unique asset coordinate,
using the corrected restrend_engine.compute_live_snapshot (fixed to use a
temporal composite instead of a single first() scene - see its docstring).
Does NOT re-run the expensive 10-year RESTREND regression, which is already
cached and correct. Then reapplies triage.py with the corrected NDWI/LULC.
"""
import os
import sys
import time

import ee

sys.path.insert(0, os.path.dirname(__file__))
import models
import restrend_engine
from database import SessionLocal
from enrich_abc_dataset import apply_triage, _coord_key


def main():
    ee.Initialize()
    db = SessionLocal()
    assets = db.query(models.Asset).all()
    unique_coords = sorted({(a.latitude, a.longitude) for a in assets})
    print(f"Refreshing live snapshot for {len(unique_coords)} unique coordinates...")

    snapshot_cache = {}
    for i, (lat, lon) in enumerate(unique_coords):
        try:
            snapshot_cache[_coord_key(lat, lon)] = restrend_engine.compute_live_snapshot(lat, lon)
            if (i + 1) % 25 == 0:
                print(f"  {i+1}/{len(unique_coords)}")
        except Exception as e:
            print(f"  [{i+1}/{len(unique_coords)}] FAILED {lat},{lon}: {e}")

    updated = 0
    for asset in assets:
        snap = snapshot_cache.get(_coord_key(asset.latitude, asset.longitude))
        if not snap:
            continue
        asset.sentinel_ndwi = snap.get("sentinel_ndwi")
        asset.sentinel_current_lulc = snap.get("sentinel_current_lulc")
        asset.soil_texture_class = snap.get("soil_texture_class")
        updated += 1
    db.commit()
    print(f"Updated {updated} assets with corrected NDWI/LULC/soil.")

    apply_triage(db)
    db.close()


if __name__ == "__main__":
    main()
