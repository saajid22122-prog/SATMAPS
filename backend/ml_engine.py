"""
Layer 2: Ground-photo classification via a frozen CLIP backbone + a CPU
linear probe that is cheap enough to refit live whenever an expert corrects
a label in Layer 5 (Section 4).

- CLIP (openai/clip-vit-base-patch32) is loaded once, frozen, no gradients.
  It never gets fine-tuned - only used as a fixed 512-d feature extractor.
- Every ground photo's embedding is pre-extracted once and cached to disk
  (clip_embeddings.npz), so a server restart doesn't re-run CLIP on 257 images.
- Bootstrap predictions (before any expert has corrected anything) come from
  CLIP zero-shot: cosine similarity between the image embedding and text
  embeddings of the candidate structure-type prompts.
- Once >=2 classes have >=2 expert-corrected examples each, a scikit-learn
  LogisticRegression ("linear probe") is fit on top of the cached embeddings
  and takes over prediction. Refitting on ~250 cached 512-d vectors is a
  sub-second CPU operation - well within the "no GPU needed" requirement.
"""
import json
import os
import pickle

import numpy as np

# Once the CLIP weights are cached locally (see requirements.txt / first-run
# download), skip the Hugging Face Hub network round trip that otherwise
# checks for updates on every load - that round trip is what makes a cold
# start take minutes instead of seconds on a slow/filtered connection.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

BACKEND_DIR = os.path.dirname(__file__)
EMBEDDINGS_PATH = os.path.join(BACKEND_DIR, "clip_embeddings.npz")
PROBE_PATH = os.path.join(BACKEND_DIR, "linear_probe.pkl")

CANDIDATE_LABELS = [
    "farm_pond",
    "check_dam",
    "percolation_tank",
    "plantation",
    "boulder_structure",
    "water_structure_other",
]

CANDIDATE_PROMPTS = [
    "a photo of an excavated earthen farm pond or rectangular water storage pit in agricultural field",
    "a photo of a concrete, masonry, or stone check dam built across a small stream channel",
    "a photo of a large earthen percolation tank, embankment, or water reservoir basin",
    "a photo of horticulture crops, tree plantation, green farm foliage, or agricultural vegetation",
    "a photo of a rock boulder bund structure, loose stone check wall, or gabion mattress",
    "a photo of a water harvesting entry-point structure, inlet pipe, or drainage line treatment",
]

# Second, independent zero-shot pass over the SAME cached image embedding -
# structure *type* (above) and structure *condition* (below) are different
# questions, and abc's source CSV only ever tells us type. Condition is the
# one real per-photo signal that lets Section 3's disagreement routing
# compare "what the photo shows" against "what the satellite shows" for the
# same site, instead of inventing a condition claim that isn't in the data.
CONDITION_LABELS = [
    "a functional water structure holding visible water",
    "a dry, empty, or silted structure with no visible water",
    "a damaged, breached, or collapsed structure",
    "a newly built or under-construction structure",
]

_model = None
_processor = None
_text_embeddings = None  # (n_labels, 512), L2-normalized
_condition_text_embeddings = None  # (n_condition_labels, 512), L2-normalized


def _lazy_load_clip():
    global _model, _processor
    if _model is not None:
        return
    import torch
    from transformers import CLIPModel, CLIPProcessor

    _model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
    _model.eval()
    for p in _model.parameters():
        p.requires_grad = False
    _processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")


def _l2norm(x, axis=-1):
    return x / (np.linalg.norm(x, axis=axis, keepdims=True) + 1e-8)


def get_text_embeddings():
    global _text_embeddings
    if _text_embeddings is not None:
        return _text_embeddings
    _lazy_load_clip()
    import torch
    inputs = _processor(text=CANDIDATE_PROMPTS, return_tensors="pt", padding=True)
    with torch.no_grad():
        feats = _model.get_text_features(**inputs).pooler_output.numpy()
    _text_embeddings = _l2norm(feats)
    return _text_embeddings


def get_condition_text_embeddings():
    global _condition_text_embeddings
    if _condition_text_embeddings is not None:
        return _condition_text_embeddings
    _lazy_load_clip()
    import torch
    inputs = _processor(text=CONDITION_LABELS, return_tensors="pt", padding=True)
    with torch.no_grad():
        feats = _model.get_text_features(**inputs).pooler_output.numpy()
    _condition_text_embeddings = _l2norm(feats)
    return _condition_text_embeddings


def zero_shot_predict_condition(image_embedding):
    """Same cached image embedding, a second real zero-shot pass against
    CONDITION_LABELS instead of CANDIDATE_LABELS - no new CLIP inference."""
    text_emb = get_condition_text_embeddings()
    sims = text_emb @ image_embedding
    # Temperature scaling: 15.0 for sharper probability distribution
    exp = np.exp(sims * 15.0)
    probs = exp / exp.sum()
    best_idx = int(np.argmax(probs))
    return CONDITION_LABELS[best_idx], float(probs[best_idx])


def embed_image(image_path):
    _lazy_load_clip()
    import torch
    from PIL import Image

    img = Image.open(image_path).convert("RGB")
    inputs = _processor(images=img, return_tensors="pt")
    with torch.no_grad():
        feat = _model.get_image_features(**inputs).pooler_output.numpy()[0]
    return _l2norm(feat)


class EmbeddingCache:
    def __init__(self, path=EMBEDDINGS_PATH):
        self.path = path
        self._keys = []
        self._matrix = None
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            data = np.load(self.path, allow_pickle=True)
            self._keys = list(data["keys"])
            self._matrix = data["matrix"]
        else:
            self._keys = []
            self._matrix = np.zeros((0, 512), dtype=np.float32)

    def save(self):
        np.savez_compressed(self.path, keys=np.array(self._keys), matrix=self._matrix)

    def get(self, key):
        if not self._keys:
            return None
        key_str = str(key)
        candidates = [key_str, f"abc_{key_str}"]
        if key_str.startswith("abc_"):
            candidates.append(key_str[4:])
        for k in candidates:
            if k in self._keys:
                idx = self._keys.index(k)
                return self._matrix[idx]
        return None

    def put(self, key, vec):
        existing = self.get(key)
        if existing is not None:
            key_str = str(key)
            candidates = [key_str, f"abc_{key_str}"]
            if key_str.startswith("abc_"):
                candidates.append(key_str[4:])
            for k in candidates:
                if k in self._keys:
                    idx = self._keys.index(k)
                    self._matrix[idx] = vec
                    break
        else:
            self._keys.append(str(key))
            self._matrix = np.vstack([self._matrix, vec[None, :]]) if self._matrix.shape[0] else vec[None, :]

    def all_items(self):
        return list(zip(self._keys, self._matrix))


def zero_shot_predict(image_embedding):
    text_emb = get_text_embeddings()
    sims = text_emb @ image_embedding  # cosine sim, both L2-normalized
    exp = np.exp(sims * 15.0)  # temperature-scaled softmax
    probs = exp / exp.sum()
    best_idx = int(np.argmax(probs))
    return CANDIDATE_LABELS[best_idx], float(probs[best_idx])


def predict_for_photo(key, image_path, cache: EmbeddingCache):
    vec = cache.get(key)
    if vec is None and image_path and os.path.exists(image_path):
        vec = embed_image(image_path)
        cache.put(key, vec)

    if vec is None:
        return "unspecified", 0.0, None

    probe = load_linear_probe()
    if probe is not None:
        label = probe.predict([vec])[0]
        proba = probe.predict_proba([vec])[0]
        confidence = float(np.max(proba))
        return label, confidence, vec

    label, confidence = zero_shot_predict(vec)
    return label, confidence, vec


def load_linear_probe():
    if os.path.exists(PROBE_PATH):
        with open(PROBE_PATH, "rb") as f:
            return pickle.load(f)
    return None


def refit_linear_probe(db):
    """
    Refits a Logistic Regression linear probe on cached CLIP embeddings
    using all available photo ground-truth labels (or expert corrected_label).
    Persists linear_probe.pkl to disk.
    """
    from sklearn.linear_model import LogisticRegression
    import models

    cache = EmbeddingCache()
    photos = db.query(models.Photo).all()

    X, y = [], []
    for p in photos:
        vec = cache.get(str(p.id))
        if vec is None:
            continue
        
        # Expert corrected label takes priority, otherwise use ground truth structure category
        target_label = p.corrected_label
        if not target_label and p.ground_photo_path:
            parts = p.ground_photo_path.replace("\\", "/").split("/")
            target_label = parts[3] if len(parts) >= 4 else None

        if target_label:
            X.append(vec)
            y.append(target_label)

    if len(X) < 4:
        return None
    labels, counts = np.unique(y, return_counts=True)
    if len(labels) < 2 or np.min(counts) < 2:
        return None

    clf = LogisticRegression(max_iter=1000, C=1.0, random_state=42)
    clf.fit(np.array(X), np.array(y))
    with open(PROBE_PATH, "wb") as f:
        pickle.dump(clf, f)
    return clf

