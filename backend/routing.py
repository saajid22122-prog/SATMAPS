"""
Layer 3b: explicit, inspectable rules mapping a real satellite-vs-photo
mismatch (or a real "we can't tell" gap) to exactly one specialist role.
Per the spec, this routing logic is the system's core novelty claim, so
every rule here is a plain if/else over real, named DB columns - never a
black box, never a learned/opaque score.

WHY ONLY ONE DISAGREEMENT RULE IS IMPLEMENTED (read before adding more):
The abc dataset gives us exactly two real per-site signals to compare:
  1. sentinel_ndwi + sentinel_current_lulc  (what the satellite currently shows)
  2. predicted_condition on each photo       (what a CLIP zero-shot pass over
     the real ground photo says about functional/dry/damaged/new-construction)
It does NOT give us: a baseline (pre-treatment) LULC for abc assets
(bhuvan_baseline_lulc is never populated for this dataset - Bhuvan
GetFeatureInfo was never wired to abc coordinates), so the Agriculture
Expert's spec trigger ("baseline vs current LULC transition plausibility")
has no real data to fire on for abc and is intentionally NOT implemented here - faking a baseline to make that
trigger work would be exactly the fabrication this whole project exists to
avoid. Verified this is still true this session, not just assumed: Bhuvan's
real WMS endpoint (bhuvan-vec2.nrsc.gov.in) was tested live and times out
from this environment (a real, timed connection test, not a guess) - so
there is no real baseline LULC to compare against for abc coordinates, full
stop. If Bhuvan (or another real baseline-LULC source) ever becomes
reachable, add its rule here following the same pattern: real signal in,
real signal out, one role, documented why.

Soil Science's rule (added after re-review - see Rule 2 below) does NOT
claim to detect erosion, only that real soil-texture data exists and the
structure type is one where soil siting genuinely matters per Section 3c's
own framing - it routes a real, existing no_evidence case to the specialist
best placed to look at it, the same way Rule 2's other branches do. It does
not invent an erosion score or diagnosis.

RULE 1 - WATER_SIGNAL_MISMATCH -> Water Management Expert
  Real signals: sentinel_ndwi (Sentinel-2 median composite) vs. the asset's
  dominant real CLIP photo-condition prediction.
  Fires when either:
    (a) the photo says "functional, holding water" but the satellite point
        reads dry (ndwi <= NDWI_WET_THRESHOLD), or
    (b) the photo says "damaged/breached/collapsed" but the satellite point
        reads wet/greening (ndwi > NDWI_WET_THRESHOLD) - a breach claim that
        the satellite doesn't corroborate is itself worth a specialist look.
  This is exactly Section 3a's stated trigger ("a mismatch specifically
  about water presence"), so it always routes to water_management.
  Sets triage_status="disagreement" (overriding the confirmed/
  rainfall_confounded/no_evidence result from triage.py, which has no way
  to see this mismatch on its own since it never looks at photo condition).

RULE 2 - no_evidence routing (not a "disagreement", but Section 5 Stage 5
  still requires exactly one specialist for every review-queue item):
  Real signals used, checked in this order (first match wins - each asset
  gets exactly one role):
    (a) pairing_method == "district_fallback" (we don't even have a
        resolved village - see scripts/geocode_all_fallbacks.py) ->
        Watershed Committee Member. The most basic open question here is
        "does this structure exist where we think it does", which is
        exactly the local, physical, independent-of-any-dataset knowledge
        Section 3e describes.
    (b) real soil_texture_class exists AND ps_category is one where soil
        siting/erosion genuinely matters (check_dam, boulder_structure,
        gabion_structure - structures whose failure mode is typically
        soil/foundation-related, per Section 3c's own framing) -> Soil
        Science Expert. This does NOT diagnose erosion (no real erosion
        signal exists for this dataset - see the module docstring); it
        routes a real no_evidence case, on a real structure type, with
        real soil data available to review, to the specialist for whom
        that combination is actually relevant.
    (c) otherwise (location is real and reasonably trusted, satellite is
        just inconclusive, and soil siting isn't the obvious angle) ->
        Social Mobilization Expert, per Section 3d's framing of
        "governance/context questions... furthest from automatable data".
  disagreement_type is left NULL for all of these (they are not a detected
  mismatch, just a routing decision for missing evidence) - only
  routed_role is set.
"""

NDWI_WET_THRESHOLD = -0.1  # matches triage.py's own "greening" cutoff, so the two modules agree on what "wet" means
CONDITION_FUNCTIONAL = "a functional water structure holding visible water"
CONDITION_DAMAGED = "a damaged, breached, or collapsed structure"
SOIL_RELEVANT_STRUCTURE_TYPES = {"check_dam", "boulder_structure", "gabion_structure"}


MIN_CONDITION_CONFIDENCE_THRESHOLD = 0.45  # Genuine minimum confidence threshold (>= 45%) before photo condition can trigger a disagreement override (prevents near-equal low-confidence predictions from being treated as authoritative)


def _dominant_photo_condition(photos):
    """Real per-asset aggregate: the single highest-confidence real CLIP
    condition prediction among this asset's photos, provided it meets the
    genuine minimum confidence threshold (>= 0.45)."""
    scored = [
        p for p in photos
        if p.predicted_condition is not None
        and p.predicted_condition_confidence is not None
        and p.predicted_condition_confidence >= MIN_CONDITION_CONFIDENCE_THRESHOLD
    ]
    if not scored:
        return None, None
    best = max(scored, key=lambda p: p.predicted_condition_confidence)
    return best.predicted_condition, best.predicted_condition_confidence


def classify_disagreement(asset, photos):
    """
    Returns (triage_status_override, disagreement_type, routed_role, rule_applied, satellite_verdict, photo_classification).
    triage_status_override is None unless Rule 1 fires (in which case the
    caller should set asset.triage_status = "disagreement"). rule_applied
    and the two verdict fields are real inputs to the CrossValidation audit
    row - never re-derived after the fact, always the exact values this
    function actually used to decide.
    """
    condition, condition_confidence = _dominant_photo_condition(photos)
    ndwi = asset.sentinel_ndwi
    satellite_verdict = None if ndwi is None else ("wet" if ndwi > NDWI_WET_THRESHOLD else "dry")

    if condition is not None and ndwi is not None:
        is_wet = ndwi > NDWI_WET_THRESHOLD
        if condition == CONDITION_FUNCTIONAL and not is_wet:
            return "disagreement", "water_signal_mismatch", "water_management", "rule1_functional_photo_dry_satellite", satellite_verdict, condition
        if condition == CONDITION_DAMAGED and is_wet:
            return "disagreement", "water_signal_mismatch", "water_management", "rule1_damaged_photo_wet_satellite", satellite_verdict, condition

    if asset.triage_status == "no_evidence":
        if asset.pairing_method == "district_fallback":
            return None, None, "committee_member", "rule2a_unresolved_location", satellite_verdict, condition
        if asset.soil_texture_class is not None and asset.ps_category in SOIL_RELEVANT_STRUCTURE_TYPES:
            return None, None, "soil_science", "rule2b_soil_relevant_structure", satellite_verdict, condition
        return None, None, "social_mobilization", "rule2c_default_no_evidence", satellite_verdict, condition

    return None, None, None, None, satellite_verdict, condition
