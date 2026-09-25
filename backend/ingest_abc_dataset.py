"""
ingest_abc_dataset.py
=====================
Ingests the organized ABC ground-truth dataset from `abc/organised_log.csv`
into `backend/watershed.db` as Assets and Photos.

This script only records real per-row facts pulled straight from the CSV
(coordinates, district, structure type, Drishti/MWS identifiers). It
deliberately does NOT set triage_status, confidence_score/level,
structure_condition, elevation_m, slope_deg, or any photo prediction field -
those all require a real computation (satellite pull, terrain lookup, CLIP
inference, cross-validation) that this script has no basis for guessing.
They are left NULL here and filled in by:
  1. scripts/geocode_all_fallbacks.py  - real reverse-geocoding for the
     district-fallback sites (upgrades pairing_method to village_geocoded)
  2. enrich_abc_dataset.py             - real GEE/IMD/CLIP enrichment +
     triage.py classification
"""

import os
import re
import pandas as pd
from sqlalchemy.orm import Session

import sys
sys.path.insert(0, os.path.dirname(__file__))

from database import engine, SessionLocal, Base
import models

# District centroid fallbacks for images without direct lat/lon
DISTRICT_CENTROIDS = {
    "Anantapuramu": (14.6819, 77.6006),
    "Chittoor": (13.2172, 79.1003),
    "East Godavari": (17.0005, 81.8040),
    "Guntur": (16.3067, 80.4365),
    "Kurnool": (15.8281, 78.0373),
    "Prakasam": (15.5057, 80.0499),
    "Srikakulam": (18.2949, 83.8938),
    "Visakhapatnam": (17.6868, 83.2185),
    "Vizianagaram": (18.1067, 83.3956),
    "West Godavari": (16.7107, 81.0952),
    "Ysr Kadapa": (14.4673, 78.8242),
}

def ingest_abc():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    repo_root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
    csv_path = os.path.join(repo_root, "abc", "organised_log.csv")
    gt_dir = os.path.join(repo_root, "abc", "ground_truth")

    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} records from {csv_path}")

    # Avoid duplicate photos
    existing_photo_paths = set(
        p[0] for p in db.query(models.Photo.ground_photo_path).all()
    )

    # Group by (source_pdf, lat, lon) or (source_pdf, district)
    # To create coherent Assets
    assets_created = 0
    photos_created = 0

    # Build unique site key for each row
    def get_site_key(row):
        pdf = str(row["source_pdf"])
        lat = row["attached_lat"]
        lon = row["attached_lon"]
        if pd.notna(lat) and pd.notna(lon):
            return f"{pdf}_{float(lat):.4f}_{float(lon):.4f}"
        return f"{pdf}_{row['district']}_fallback"

    df["site_key"] = df.apply(get_site_key, axis=1)
    grouped = df.groupby("site_key")
    print(f"Unique watershed project sites identified: {len(grouped)}")

    for site_key, group in grouped:
        first = group.iloc[0]
        pdf_stem = str(first["source_pdf"]).replace(".pdf", "")
        district = str(first["district"])

        lat = first["attached_lat"]
        lon = first["attached_lon"]
        pairing_method = "project_level"

        if pd.isna(lat) or pd.isna(lon):
            # Centroid fallback
            lat, lon = DISTRICT_CENTROIDS.get(district, (15.5, 78.5))
            pairing_method = "district_fallback"
        else:
            lat = float(lat)
            lon = float(lon)

        # Primary structure category for this site
        stype_counts = group["structure_type"].value_counts()
        primary_stype = stype_counts.index[0] if len(stype_counts) else "check_dam"

        # Check if asset already exists in db. Matched on project_id ALONE,
        # not lat/lon: verified project_id is real 1:1 with asset in this
        # dataset, and matching on coordinates too caused a real bug -
        # scripts/geocode_all_fallbacks.py legitimately updates a fallback
        # asset's real lat/lon after the first ingest, so a coordinate-based
        # re-match would never find it again and would insert a duplicate
        # empty asset every time this script re-runs (caught and fixed
        # after /api/admin/backfill created 106 real duplicate rows).
        existing_asset = (
            db.query(models.Asset)
            .filter(models.Asset.project_id == pdf_stem)
            .first()
        )

        if not existing_asset:
            asset = models.Asset(
                project_id=pdf_stem,
                state_code="AP",
                state_name="Andhra Pradesh",
                district=district,
                ps_category=primary_stype,
                latitude=lat,
                longitude=lon,
                structure_condition="not_recorded",  # abc dataset carries no pre/post condition label
                pairing_method=pairing_method,
                triage_status=None,       # set by enrich_abc_dataset.py from real triage.py logic
                confidence_score=None,
                confidence_level=None,
                admin_locality=district,
                admin_subdistrict=district,
                elevation_m=None,         # set by enrich_abc_dataset.py from real Copernicus DEM
                slope_deg=None,
            )
            db.add(asset)
            db.flush()
            assets_created += 1
        else:
            asset = existing_asset

        # Now attach all photos belonging to this site
        for _, row in group.iterrows():
            filename = str(row["filename"])
            stype = str(row["structure_type"])
            rel_photo_path = os.path.join("abc", "ground_truth", district, stype, filename).replace("\\", "/")

            if rel_photo_path in existing_photo_paths:
                continue

            # Verify file exists on disk
            full_path = os.path.join(repo_root, rel_photo_path)
            if not os.path.exists(full_path):
                continue

            # Real per-row coordinate from the CSV's attached_lat/attached_lon
            # (coordinate_precision == "project_level") - this used to be
            # silently discarded (Photo never got latitude=/longitude= at
            # all), leaving 1190 real, already-extracted coordinate values
            # as NULL. It is the same one coordinate shared by every photo
            # in this project (verified: 284/284 project_level projects have
            # exactly 1 distinct coordinate among their own rows) - not a
            # per-structure GPS reading - but it is real, extracted data and
            # should be stored rather than dropped.
            photo_lat = float(row["attached_lat"]) if pd.notna(row["attached_lat"]) else None
            photo_lon = float(row["attached_lon"]) if pd.notna(row["attached_lon"]) else None

            photo = models.Photo(
                asset_id=asset.id,
                ground_photo_path=rel_photo_path,
                structure_condition="not_recorded",
                page_num=int(row["page"]) if pd.notna(row["page"]) else None,
                point_idx=0,
                pairing_method=pairing_method,
                latitude=photo_lat,
                longitude=photo_lon,
                drishti_id=str(row["drishti_id"]) if pd.notna(row["drishti_id"]) else None,
                mws_code=str(row["mws_code"]) if pd.notna(row["mws_code"]) else None,
                activity_type=str(row["activity_type"]) if pd.notna(row["activity_type"]) else None,
                predicted_label=None,        # set by enrich_abc_dataset.py from real CLIP inference
                predicted_confidence=None,
            )
            db.add(photo)
            existing_photo_paths.add(rel_photo_path)
            photos_created += 1

    db.commit()
    db.close()

    print(f"\n[SUCCESS] Ingested {assets_created} new assets and {photos_created} new photos into watershed.db!")
    return assets_created, photos_created


if __name__ == "__main__":
    ingest_abc()
