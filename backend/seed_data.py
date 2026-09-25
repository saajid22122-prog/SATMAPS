"""
Step 1 (Section 7): ingest all_india_watershed_master.csv (257 rows / 98
unique sites) into the DB, attach the pre-computed RESTREND + terrain cache,
run the CLIP zero-shot classifier over every ground photo, apply the Layer 3
triage + Layer 4 confidence logic, and train the DPR feasibility model.

Run from backend/:  python seed_data.py
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))

from database import Base, engine, SessionLocal
import models
import ml_engine
import triage
import site_feasibility

BACKEND_DIR = os.path.dirname(__file__)
REPO_ROOT = os.path.join(BACKEND_DIR, "..")
CSV_PATH = os.path.join(REPO_ROOT, "all_india_watershed_master.csv")
CACHE_PATH = os.path.join(BACKEND_DIR, "restrend_cache.json")

CONDITION_PRIORITY = [
    "functional_post_treatment",
    "baseline_pre_treatment",
    "proposed_pre_construction",
    "unspecified",
    "control_non_structure",
]
PAIRING_PRIORITY = ["same_page", "document_fallback", "negative_control"]

ENRICHMENT_FIELDS = [
    "bhuvan_baseline_lulc", "sentinel_current_lulc", "sentinel_ndwi",
    "soil_texture_class", "admin_locality", "admin_subdistrict",
]


def _pick_priority(values, priority_list):
    counts = values.value_counts()
    for p in priority_list:
        if p in counts.index:
            return p
    return counts.index[0]


def _first_non_unavailable(series):
    for v in series:
        if pd.notna(v) and str(v).strip().lower() not in ("unavailable", "unknown", ""):
            return v
    return series.iloc[0] if len(series) else None


def normalize_path(p):
    return str(p).replace("\\", "/")


def resolve_photo_path(rel_path):
    return os.path.normpath(os.path.join(REPO_ROOT, rel_path))


def completeness_fraction(row):
    present = 0
    for f in ENRICHMENT_FIELDS:
        v = row.get(f)
        if pd.notna(v) and str(v).strip().lower() not in ("unavailable", "unknown", ""):
            present += 1
    return present / len(ENRICHMENT_FIELDS)


def main():
    print("Creating tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    print(f"Loading {CSV_PATH} ...")
    df = pd.read_csv(CSV_PATH)
    print(f"  {len(df)} rows, {df[['latitude','longitude']].drop_duplicates().shape[0]} unique sites")

    if not os.path.exists(CACHE_PATH):
        raise FileNotFoundError(f"{CACHE_PATH} missing - run precompute_restrend_cache.py first.")
    with open(CACHE_PATH, "r", encoding="utf-8") as f:
        restrend_cache = json.load(f)

    embed_cache = ml_engine.EmbeddingCache()

    db = SessionLocal()
    n_assets = 0
    n_photos = 0

    grouped = df.groupby(["latitude", "longitude"], sort=False)
    for (lat, lon), group in grouped:
        cache_key = f"{lat:.6f},{lon:.6f}"
        rcache = restrend_cache.get(cache_key, {})

        condition = _pick_priority(group["structure_condition"], CONDITION_PRIORITY)
        pairing = _pick_priority(group["pairing_method"], PAIRING_PRIORITY)
        row0 = group.iloc[0]

        ndwi_raw = _first_non_unavailable(group["sentinel_ndwi"])
        try:
            ndwi = float(ndwi_raw)
        except (TypeError, ValueError):
            ndwi = None

        asset = models.Asset(
            project_id=row0["project_id"],
            state_code=row0["state_code"],
            state_name=row0["state_name"],
            district=row0["district"],
            ps_category=_pick_priority(group["ps_category"], []),
            latitude=float(lat),
            longitude=float(lon),
            structure_condition=condition,
            pairing_method=pairing,
            bhuvan_baseline_lulc=_first_non_unavailable(group["bhuvan_baseline_lulc"]),
            sentinel_current_lulc=_first_non_unavailable(group["sentinel_current_lulc"]),
            sentinel_ndwi=ndwi,
            soil_texture_class=_first_non_unavailable(group["soil_texture_class"]),
            admin_locality=_first_non_unavailable(group["admin_locality"]),
            admin_subdistrict=_first_non_unavailable(group["admin_subdistrict"]),
            elevation_m=rcache.get("elevation_m"),
            slope_deg=rcache.get("slope_deg"),
            space_tile_path=normalize_path(row0["space_tile_path"]),
            restrend_slope=rcache.get("restrend_slope"),
            restrend_pvalue=rcache.get("restrend_pvalue"),
            restrend_rainfall_anomaly=rcache.get("rainfall_anomaly"),
        )
        db.add(asset)
        db.flush()  # get asset.id

        photo_confidences = []
        for _, r in group.iterrows():
            abs_path = resolve_photo_path(r["ground_photo_path"])
            predicted_label, predicted_confidence = None, None
            if os.path.exists(abs_path):
                try:
                    photo_key = f"photo_{n_photos}"
                    label, conf, _vec = ml_engine.predict_for_photo(photo_key, abs_path, embed_cache)
                    predicted_label, predicted_confidence = label, conf
                    photo_confidences.append(conf)
                except Exception as e:
                    print(f"  [warn] CLIP failed for {abs_path}: {e}")
            else:
                print(f"  [warn] missing photo file: {abs_path}")

            photo = models.Photo(
                asset_id=asset.id,
                ground_photo_path=normalize_path(r["ground_photo_path"]),
                structure_condition=r["structure_condition"],
                page_num=int(r["page_num"]) if pd.notna(r["page_num"]) else None,
                point_idx=int(r["point_idx"]) if pd.notna(r["point_idx"]) else None,
                pairing_method=r["pairing_method"],
                pixel_variance_stddev=float(r["pixel_variance_stddev"]) if pd.notna(r["pixel_variance_stddev"]) else None,
                predicted_label=predicted_label,
                predicted_confidence=predicted_confidence,
            )
            db.add(photo)
            n_photos += 1

        for point in rcache.get("series", []):
            db.add(models.RestrendPoint(
                asset_id=asset.id,
                year=point["year"],
                month=point["month"],
                ndvi_observed=point["ndvi_observed"],
                precipitation_mm=point["precipitation_mm"],
                ndvi_modeled=point["ndvi_modeled"],
                residual=point["residual"],
            ))

        # Layer 3 + Layer 4
        asset.triage_status = triage.classify_triage_status(
            condition, ndwi, asset.restrend_slope, asset.restrend_pvalue, pairing
        )
        mean_photo_conf = float(np.mean(photo_confidences)) if photo_confidences else None
        score, level = triage.composite_confidence(
            ndwi, mean_photo_conf, asset.restrend_rainfall_anomaly, completeness_fraction(row0)
        )
        asset.confidence_score = score
        asset.confidence_level = level

        n_assets += 1
        if n_assets % 10 == 0:
            print(f"  ...{n_assets} assets seeded")
            embed_cache.save()

    db.commit()
    embed_cache.save()
    db.close()

    print(f"Seeded {n_assets} assets, {n_photos} photos.")

    print("Training DPR feasibility model...")
    meta = site_feasibility.train_and_cache()
    print(f"  {meta}")

    print("Done.")


if __name__ == "__main__":
    main()
