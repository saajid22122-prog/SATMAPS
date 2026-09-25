"""
1. Real CLIP condition zero-shot pass for every photo, reusing the image
   embeddings already cached in clip_embeddings.npz (no new CLIP inference -
   just a second text-prompt comparison against the same real vectors).
2. Real routing.classify_disagreement() per asset, using those conditions
   plus the corrected NDWI from refresh_snapshot.py.

Run after enrich_abc_dataset.py and refresh_snapshot.py have both completed.
Safe to re-run.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import ml_engine
import models
import routing
from database import SessionLocal


def apply_conditions(db):
    cache = ml_engine.EmbeddingCache()
    photos = db.query(models.Photo).all()
    done = 0
    for photo in photos:
        vec = cache.get(f"abc_{photo.id}")
        if vec is None:
            continue  # embedding wasn't computed (missing file etc.) - leave condition NULL, honest gap
        label, confidence = ml_engine.zero_shot_predict_condition(vec)
        photo.predicted_condition = label
        photo.predicted_condition_confidence = confidence
        done += 1
    db.commit()
    print(f"Real condition prediction applied to {done}/{len(photos)} photos.")


def apply_routing(db):
    assets = db.query(models.Asset).all()
    counts = {}
    for asset in assets:
        (override, disagreement_type, routed_role,
         rule_applied, satellite_verdict, photo_classification) = routing.classify_disagreement(asset, asset.photos)
        if override:
            asset.triage_status = override
        asset.disagreement_type = disagreement_type
        asset.routed_role = routed_role

        # Real audit-trail row (Section 3's CrossValidation table) - one
        # per classification run, replacing any prior row for this asset.
        db.query(models.CrossValidation).filter(models.CrossValidation.asset_id == asset.id).delete()
        db.add(models.CrossValidation(
            asset_id=asset.id,
            satellite_verdict=satellite_verdict,
            photo_classification=photo_classification,
            disagreement_type=disagreement_type,
            routed_role=routed_role,
            rule_applied=rule_applied,
        ))

        key = (asset.triage_status, routed_role)
        counts[key] = counts.get(key, 0) + 1
    db.commit()
    print(f"Routing applied to {len(assets)} assets.")
    for (status, role), n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  triage_status={status!r} routed_role={role!r}: {n}")


def main():
    db = SessionLocal()
    try:
        apply_conditions(db)
        apply_routing(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
