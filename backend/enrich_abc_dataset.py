"""
enrich_abc_dataset.py
======================
Fills in every computed field that ingest_abc_dataset.py deliberately left
NULL, using only real sources:

  - Per unique coordinate: real Sentinel-2 NDWI + Dynamic World LULC + soil
    texture + Copernicus DEM elevation/slope (restrend_engine.compute_live_snapshot),
    and a real 10-year Landsat-8 NDVI vs IMD-or-Open-Meteo-rainfall RESTREND
    regression (restrend_engine.compute_restrend_series).
  - Per photo: a real CLIP zero-shot structure-type prediction
    (ml_engine.predict_for_photo).
  - Per asset: triage_status and confidence_score/level from triage.py,
    computed from the real signals above - never assigned directly.

Resumable: re-running skips assets/photos that already have real computed
values, and the coordinate-level GEE/rainfall cache
(restrend_cache_abc.json) is written incrementally so an interrupted run
loses at most the in-flight coordinate.

Run from the backend/ directory:
    python enrich_abc_dataset.py
"""
import json
import os
import sys
import time

import ee
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

import ml_engine
import restrend_engine
import triage
import models
from database import SessionLocal

CACHE_PATH = os.path.join(os.path.dirname(__file__), "restrend_cache_abc.json")
COMPLETENESS_FIELDS = 6  # sentinel_ndwi, sentinel_current_lulc, soil_texture_class, elevation_m, slope_deg, restrend_pvalue


def _coord_key(lat, lon):
    return f"{lat:.6f},{lon:.6f}"


def load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f)


def enrich_coordinates(db):
    cache = load_cache()
    assets = db.query(models.Asset).all()
    unique_coords = sorted({(a.latitude, a.longitude) for a in assets})
    print(f"Unique real coordinates to enrich: {len(unique_coords)}")

    for i, (lat, lon) in enumerate(unique_coords):
        key = _coord_key(lat, lon)
        if key in cache and cache[key].get("restrend_pvalue") is not None:
            continue
        if key in cache and cache[key].get("error") and cache[key].get("_attempts", 1) >= 3:
            continue  # persistent real failure (e.g. no cloud-free scenes) - stop retrying forever

        print(f"[{i+1}/{len(unique_coords)}] {key} ...", end=" ", flush=True)
        t0 = time.time()
        try:
            snapshot = restrend_engine.compute_live_snapshot(lat, lon)
            restrend = restrend_engine.compute_restrend_series(lat, lon)
            terrain = restrend_engine.compute_terrain(lat, lon)
            entry = {**snapshot, **restrend}
            entry["elevation_m"] = terrain["elevation_m"] if terrain["elevation_m"] is not None else entry.get("elevation_m")
            entry["slope_deg"] = terrain["slope_deg"] if terrain["slope_deg"] is not None else entry.get("slope_deg")
            cache[key] = entry
            print(f"OK ({len(entry.get('series', []))} pts, p={entry.get('restrend_pvalue')}, "
                  f"precip={entry.get('precip_source')}) in {time.time()-t0:.1f}s")
        except Exception as e:
            attempts = cache.get(key, {}).get("_attempts", 0) + 1
            cache[key] = {"error": f"{type(e).__name__}: {e}", "_attempts": attempts,
                          "series": [], "restrend_slope": None, "restrend_pvalue": None,
                          "rainfall_anomaly": None, "precip_source": None,
                          "elevation_m": None, "slope_deg": None,
                          "sentinel_ndwi": None, "sentinel_current_lulc": None, "soil_texture_class": None}
            print(f"FAILED (attempt {attempts}): {e}")

        time.sleep(0.5)  # pace Open-Meteo calls - a tight loop over 300+ coords triggered its rate limit

        if (i + 1) % 5 == 0 or (i + 1) == len(unique_coords):
            save_cache(cache)

    save_cache(cache)
    return cache


def apply_coordinate_results(db, cache):
    assets = db.query(models.Asset).all()
    updated = 0
    for asset in assets:
        key = _coord_key(asset.latitude, asset.longitude)
        entry = cache.get(key)
        if not entry:
            continue

        asset.sentinel_ndwi = entry.get("sentinel_ndwi")
        asset.sentinel_current_lulc = entry.get("sentinel_current_lulc")
        asset.soil_texture_class = entry.get("soil_texture_class")
        asset.elevation_m = entry.get("elevation_m")
        asset.slope_deg = entry.get("slope_deg")
        asset.restrend_slope = entry.get("restrend_slope")
        asset.restrend_pvalue = entry.get("restrend_pvalue")
        asset.restrend_rainfall_anomaly = entry.get("rainfall_anomaly")
        asset.restrend_precip_source = entry.get("precip_source")

        db.query(models.RestrendPoint).filter(models.RestrendPoint.asset_id == asset.id).delete()
        for pt in entry.get("series", []):
            db.add(models.RestrendPoint(
                asset_id=asset.id,
                year=pt["year"], month=pt["month"],
                ndvi_observed=pt.get("ndvi_observed"),
                precipitation_mm=pt.get("precipitation_mm"),
                ndvi_modeled=pt.get("ndvi_modeled"),
                residual=pt.get("residual"),
            ))
        updated += 1
    db.commit()
    print(f"Applied real coordinate-level data to {updated} assets.")


def enrich_photos(db):
    cache = ml_engine.EmbeddingCache()
    photos = db.query(models.Photo).filter(models.Photo.predicted_label.is_(None)).all()
    print(f"Photos needing real CLIP prediction: {len(photos)}")
    repo_root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))

    done = 0
    for photo in photos:
        abs_path = os.path.join(repo_root, photo.ground_photo_path)
        if not os.path.exists(abs_path):
            continue
        try:
            key = f"abc_{photo.id}"
            label, confidence, _vec = ml_engine.predict_for_photo(key, abs_path, cache)
            photo.predicted_label = label
            photo.predicted_confidence = confidence
        except Exception as e:
            print(f"  [warn] CLIP failed for photo {photo.id} ({abs_path}): {e}")
        done += 1
        if done % 50 == 0:
            db.commit()
            cache.save()
            print(f"  ... {done}/{len(photos)} photos embedded")

    db.commit()
    cache.save()
    print(f"CLIP prediction complete for {done} photos.")


def apply_triage(db):
    assets = db.query(models.Asset).all()
    counts = {}
    for asset in assets:
        photo_confs = [p.predicted_confidence for p in asset.photos if p.predicted_confidence is not None]
        avg_photo_conf = float(np.mean(photo_confs)) if photo_confs else None

        present = sum(1 for v in [
            asset.sentinel_ndwi, asset.sentinel_current_lulc, asset.soil_texture_class,
            asset.elevation_m, asset.slope_deg, asset.restrend_pvalue,
        ] if v is not None)
        completeness_fraction = present / COMPLETENESS_FIELDS

        # structure_condition is "not_recorded" for every abc asset (no pre/post
        # label exists in the source data) - triage.py's FUNCTIONAL_CONDITIONS /
        # DEGRADED_HINT_CONDITIONS sets deliberately never match this value, so
        # classification always falls to its honest "unspecified condition"
        # branch (satellite + RESTREND only, never fabricating "disagreement"
        # from a condition claim we don't actually have).
        asset.triage_status = triage.classify_triage_status(
            structure_condition=asset.structure_condition,
            ndwi=asset.sentinel_ndwi,
            restrend_slope=asset.restrend_slope,
            restrend_pvalue=asset.restrend_pvalue,
            pairing_method=asset.pairing_method,
        )
        c_score, c_level = triage.composite_confidence(
            ndwi=asset.sentinel_ndwi,
            photo_confidence=avg_photo_conf,
            rainfall_anomaly=asset.restrend_rainfall_anomaly,
            completeness_fraction=completeness_fraction,
        )
        asset.confidence_score = c_score
        asset.confidence_level = c_level
        counts[asset.triage_status] = counts.get(asset.triage_status, 0) + 1

    db.commit()
    print(f"Triage applied to {len(assets)} assets: {counts}")


def main():
    print("Initializing Google Earth Engine...")
    ee.Initialize()
    print(f"IMD reachable: {restrend_engine.imd_is_reachable()} (falls back to Open-Meteo if False)")

    db = SessionLocal()
    try:
        cache = enrich_coordinates(db)
        apply_coordinate_results(db, cache)
        enrich_photos(db)
        apply_triage(db)
    finally:
        db.close()
    print("\nDone. Re-run this script any time - it skips already-enriched coordinates/photos.")


if __name__ == "__main__":
    main()
