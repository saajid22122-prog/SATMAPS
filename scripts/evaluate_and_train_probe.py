"""
evaluate_and_train_probe.py
===========================
1. Trains the Logistic Regression linear probe on the cached 512-d CLIP embeddings
   using the 1,514 ground-truth photo labels stored in backend/watershed.db.
2. Saves backend/linear_probe.pkl.
3. Evaluates and compares:
   - Default Zero-Shot CLIP
   - Improved visually descriptive Zero-Shot CLIP
   - Retrained Linear Probe (Logistic Regression)
   with real train/test split reporting Accuracy, Precision, Recall, and F1 per category.
"""

import os
import sys
import pickle
import sqlite3
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, precision_recall_fscore_support

# Ensure backend directory is in python path
SCRIPTS_DIR = os.path.dirname(__file__)
REPO_ROOT = os.path.normpath(os.path.join(SCRIPTS_DIR, ".."))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
sys.path.insert(0, BACKEND_DIR)

import ml_engine

def load_data():
    db_path = os.path.join(BACKEND_DIR, "watershed.db")
    emb_path = os.path.join(BACKEND_DIR, "clip_embeddings.npz")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, ground_photo_path, activity_type FROM photos")
    photos = cursor.fetchall()
    conn.close()

    cache = ml_engine.EmbeddingCache(emb_path)

    X_vecs = []
    y_stypes = []
    y_activities = []
    photo_ids = []

    for pid, path, act in photos:
        vec = cache.get(f"abc_{pid}")
        if vec is None:
            vec = cache.get(str(pid))
        if vec is None:
            vec = cache.get(path)
        
        if vec is not None:
            # Extract structure_type from folder path
            parts = path.replace("\\", "/").split("/")
            stype = parts[3] if len(parts) >= 4 else "unknown"
            
            X_vecs.append(vec)
            y_stypes.append(stype)
            y_activities.append(act if act else "unspecified")
            photo_ids.append(pid)

    return np.array(X_vecs), np.array(y_stypes), np.array(y_activities), photo_ids

def run_evaluation():
    print("==========================================================================")
    print(" SRISHTI-DRISHTI GROUND PHOTO CLASSIFIER EVALUATION & PROBE TRAINING")
    print("==========================================================================")
    
    X, y_stype, y_act, photo_ids = load_data()
    print(f"Loaded {len(X)} total photos with cached 512-d CLIP embeddings.\n")

    # Filter out rare classes with < 2 samples for stratified splitting
    counts = dict(zip(*np.unique(y_stype, return_counts=True)))
    valid_mask = np.array([counts[lbl] >= 2 for lbl in y_stype])
    X_sub = X[valid_mask]
    y_sub = y_stype[valid_mask]

    X_train, X_test, y_train, y_test = train_test_split(
        X_sub, y_sub, test_size=0.20, random_state=42, stratify=y_sub
    )

    print(f"Dataset Split (80/20 train/test):")
    print(f"  - Train set: {len(X_train)} samples")
    print(f"  - Test set:  {len(X_test)} samples\n")

    # -------------------------------------------------------------------------
    # 1. Default Zero-Shot CLIP Baseline
    # -------------------------------------------------------------------------
    print("--- 1. DEFAULT ZERO-SHOT CLIP BASELINE ---")
    label_map_default = {
        "farm pond": "farm_pond",
        "check dam": "check_dam",
        "percolation tank": "percolation_tank",
        "horticulture or plantation": "plantation",
        "check wall": "check_dam",
        "drainage line treatment": "water_structure_other",
        "water harvesting entry-point structure": "water_structure_other",
        "dugout pit": "farm_pond",
        "non-structure or negative control photo": "water_structure_other"
    }

    preds_zs_default = []
    for vec in X_test:
        raw_lbl, _ = ml_engine.zero_shot_predict(vec)
        mapped_lbl = label_map_default.get(raw_lbl, "water_structure_other")
        preds_zs_default.append(mapped_lbl)

    acc_zs_def = accuracy_score(y_test, preds_zs_default)
    print(classification_report(y_test, preds_zs_default, digits=4, zero_division=0))
    print(f"Default Zero-Shot Accuracy: {acc_zs_def * 100:.2f}%\n")

    # -------------------------------------------------------------------------
    # 2. Improved Visually Descriptive Zero-Shot CLIP
    # -------------------------------------------------------------------------
    print("--- 2. IMPROVED VISUALLY DESCRIPTIVE ZERO-SHOT CLIP ---")
    ml_engine._lazy_load_clip()
    import torch
    
    improved_prompts = [
        "a photo of an excavated earthen farm pond or rectangular water storage pit in agricultural field",
        "a photo of a concrete, masonry, or stone check dam built across a small stream channel",
        "a photo of a large earthen percolation tank, embankment, or water reservoir basin",
        "a photo of horticulture crops, tree plantation, green farm foliage, or agricultural vegetation",
        "a photo of a rock boulder bund structure, loose stone check wall, or gabion mattress",
        "a photo of a water harvesting entry-point structure, inlet pipe, or drainage line treatment"
    ]
    target_labels = ["farm_pond", "check_dam", "percolation_tank", "plantation", "boulder_structure", "water_structure_other"]

    inputs = ml_engine._processor(text=improved_prompts, return_tensors="pt", padding=True)
    with torch.no_grad():
        text_feats = ml_engine._model.get_text_features(**inputs).pooler_output.numpy()
    text_feats = ml_engine._l2norm(text_feats)

    preds_zs_imp = []
    for vec in X_test:
        sims = text_feats @ vec
        best_idx = int(np.argmax(sims))
        preds_zs_imp.append(target_labels[best_idx])

    acc_zs_imp = accuracy_score(y_test, preds_zs_imp)
    print(classification_report(y_test, preds_zs_imp, digits=4, zero_division=0))
    print(f"Improved Zero-Shot Accuracy: {acc_zs_imp * 100:.2f}%\n")

    # -------------------------------------------------------------------------
    # 3. Retrained Linear Probe (Logistic Regression on structure_type)
    # -------------------------------------------------------------------------
    print("--- 3. RETRAINED LINEAR PROBE (LOGISTIC REGRESSION) ---")
    clf_probe = LogisticRegression(max_iter=1000, C=1.0, random_state=42)
    clf_probe.fit(X_train, y_train)

    preds_probe = clf_probe.predict(X_test)
    acc_probe = accuracy_score(y_test, preds_probe)
    print(classification_report(y_test, preds_probe, digits=4, zero_division=0))
    print(f"Retrained Linear Probe Accuracy (Test set): {acc_probe * 100:.2f}%\n")

    # -------------------------------------------------------------------------
    # Fit probe on ALL 1,514 photos and save backend/linear_probe.pkl
    # -------------------------------------------------------------------------
    print("Fitting Linear Probe on all 1,514 photos for production persistence...")
    full_clf = LogisticRegression(max_iter=1000, C=1.0, random_state=42)
    full_clf.fit(X_sub, y_sub)

    probe_file = os.path.join(BACKEND_DIR, "linear_probe.pkl")
    with open(probe_file, "wb") as f:
        pickle.dump(full_clf, f)
    print(f"Saved trained linear probe model to: {probe_file}")

    print("\n==========================================================================")
    print(" SUMMARY OF ACCURACY GAINS:")
    print("==========================================================================")
    print(f" 1. Default Zero-Shot CLIP:     {acc_zs_def * 100:.2f}%")
    print(f" 2. Improved Zero-Shot CLIP:    {acc_zs_imp * 100:.2f}% (+{(acc_zs_imp - acc_zs_def)*100:.2f}%)")
    print(f" 3. Retrained Linear Probe:     {acc_probe * 100:.2f}% (+{(acc_probe - acc_zs_imp)*100:.2f}% over improved ZS, +{(acc_probe - acc_zs_def)*100:.2f}% overall)")
    print("==========================================================================")

if __name__ == "__main__":
    run_evaluation()
