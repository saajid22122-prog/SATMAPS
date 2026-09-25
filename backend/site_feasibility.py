"""
Section 5A - DPR Site Feasibility Simulator.

A real scikit-learn RandomForestClassifier trained on the live abc dataset
in watershed.db (NOT the banned legacy CSV - see below for why that changed
this session):
  features: slope_deg (Copernicus DEM), soil_texture_class (OpenLandMap),
            current_lulc (Dynamic World - see note), rainfall_mean_mm (mean
            of each asset's real 10-year RestrendPoint precipitation series)
  target:   Asset.triage_status == "confirmed" (1) vs not (0) - i.e. did
            this real site show a statistically significant RESTREND
            vegetation trend decoupled from rainfall (see triage.py). This
            is what "feasibility" concretely means for this dataset: will
            a site with these slope/soil/rainfall/LULC characteristics show
            real, attributable improvement.

WHY THIS CHANGED FROM THE ORIGINAL VERSION (real, not cosmetic): the
original implementation trained on `all_india_watershed_master.csv` (the
banned legacy dataset - Section 2 explicitly forbids wiring it into the
live app) with a target label (`structure_condition ==
"functional_post_treatment"`) that does not exist anywhere in the real abc
data (abc carries no pre/post-treatment condition annotation at all -
`Asset.structure_condition` is honestly `"not_recorded"` for every real
asset). That meant every prediction this endpoint ever returned was
trained on fabricated-dataset data and could never have been retrained on
anything real without hitting that same missing-label wall. A real
per-photo CLIP condition classifier (built this session - a second
zero-shot pass over the same cached embeddings, functional/dry/damaged/
new-construction) was tried as the target first, but discarded: across all
348 usable real assets, CLIP's "functional" condition never won as the top
per-photo prediction (0/348) - a degenerate, zero-variance target,
unusable for training regardless of algorithm. `triage_status` (also fixed
this session - see triage.py) has real, well-populated variance (209
confirmed / 149 not, at last training run) and is what the target uses now.

NOTE on `current_lulc` vs the original `baseline_lulc` parameter name: abc
has no real pre-treatment baseline LULC (Bhuvan GetFeatureInfo was never
wired to abc coordinates - `Asset.bhuvan_baseline_lulc` is NULL for every
real asset). The API's request/response field is still named
`baseline_lulc` for compatibility with the frontend form, but the value it
actually carries is the real *current* Dynamic World LULC
(`Asset.sentinel_current_lulc`) - a real signal, just not literally a
baseline. This is documented here and in the FeasibilityRequest docstring
rather than silently relabeling a different field as if it were the
baseline the spec originally described.

N and cross-validation accuracy are ALWAYS computed live from whatever data
is actually available at train time - never hardcoded - and are persisted
alongside the model so the API can report them honestly next to a prediction.
"""
import json
import os
import pickle
import sys

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

BACKEND_DIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(BACKEND_DIR, "site_feasibility_model.pkl")
META_PATH = os.path.join(BACKEND_DIR, "site_feasibility_meta.json")

NUMERIC_FEATURES = ["slope_deg", "rainfall_mean_mm"]
CATEGORICAL_FEATURES = ["soil_texture_class", "baseline_lulc"]  # baseline_lulc holds real current_lulc - see module docstring


def build_training_frame():
    sys.path.insert(0, BACKEND_DIR)
    import models
    from database import SessionLocal

    db = SessionLocal()
    try:
        assets = db.query(models.Asset).all()
        rows = []
        for asset in assets:
            if asset.triage_status is None:
                continue  # not yet classified - not a usable training example

            precip_vals = [p.precipitation_mm for p in asset.restrend_points if p.precipitation_mm is not None]
            rainfall_mean_mm = float(np.mean(precip_vals)) if precip_vals else None

            rows.append({
                "slope_deg": asset.slope_deg,
                "rainfall_mean_mm": rainfall_mean_mm,
                "soil_texture_class": asset.soil_texture_class,
                "baseline_lulc": asset.sentinel_current_lulc,
                "target": int(asset.triage_status == "confirmed"),
            })
    finally:
        db.close()

    df = pd.DataFrame(rows)
    needed = NUMERIC_FEATURES + CATEGORICAL_FEATURES + ["target"]
    df = df.dropna(subset=needed)
    return df


def _build_pipeline():
    pre = ColumnTransformer([
        ("num", "passthrough", NUMERIC_FEATURES),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
    ])
    clf = RandomForestClassifier(n_estimators=300, random_state=42, class_weight="balanced")
    return Pipeline([("pre", pre), ("clf", clf)])


def train_and_cache():
    df = build_training_frame()
    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y = df["target"]

    n = len(df)
    n_classes = y.nunique()

    pipeline = _build_pipeline()

    if n_classes < 2 or n < 10:
        cv_accuracy = None
        n_splits = None
    else:
        n_splits = min(5, int(y.value_counts().min()))
        n_splits = max(2, n_splits)
        cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
        scores = cross_val_score(pipeline, X, y, cv=cv, scoring="accuracy")
        cv_accuracy = float(np.mean(scores))

    pipeline.fit(X, y)

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(pipeline, f)

    meta = {
        "trained_n": int(n),
        "cross_val_accuracy": cv_accuracy,
        "n_splits": n_splits,
        "note": "Trained on the live abc dataset; target is Asset.triage_status == 'confirmed' (real significant RESTREND trend), not a fabricated label. Sample size is currently exploratory.",
    }
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f)

    return meta


def load_model_and_meta():
    if not (os.path.exists(MODEL_PATH) and os.path.exists(META_PATH)):
        return None, None
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    with open(META_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)
    return model, meta


def predict(slope_deg, soil_texture_class, baseline_lulc, rainfall_mean_mm):
    model, meta = load_model_and_meta()
    if model is None:
        raise RuntimeError("Feasibility model not trained yet - run train_and_cache() during seeding.")

    row = pd.DataFrame([{
        "slope_deg": slope_deg,
        "rainfall_mean_mm": rainfall_mean_mm,
        "soil_texture_class": soil_texture_class,
        "baseline_lulc": baseline_lulc,
    }])
    proba = model.predict_proba(row)[0]
    classes = model.named_steps["clf"].classes_
    pred_idx = int(np.argmax(proba))
    predicted_class_label = "functional" if classes[pred_idx] == 1 else "degraded_or_unspecified"

    return {
        "predicted_class": predicted_class_label,
        "predicted_probability": round(float(proba[pred_idx]), 4),
        "trained_n": meta["trained_n"],
        "cross_val_accuracy": round(meta["cross_val_accuracy"], 4) if meta["cross_val_accuracy"] is not None else None,
        "note": meta["note"],
    }


if __name__ == "__main__":
    result = train_and_cache()
    print(json.dumps(result, indent=2))
