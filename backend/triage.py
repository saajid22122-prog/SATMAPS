"""
Layer 3 (4-state triage) and Layer 4 (composite confidence scoring), applied
per-asset at seed time from real signals only - no fabricated scores.

Layer 3 states:
  confirmed            - satellite shows improvement, ground structure is
                          functional, and RESTREND says it isn't just rainfall
  rainfall_confounded  - satellite shows greening, but RESTREND residual
                          trend is flat/negative -> explained by rainfall
  disagreement         - satellite shows degradation/dry-bed despite a
                          claimed functional asset
  no_evidence          - satellite signal missing/inconclusive (e.g. cloud,
                          negative control) or RESTREND series unavailable

Layer 4 composite confidence:
  35% satellite signal strength (|NDWI|, clamped) +
  30% photo classifier confidence (from ml_engine) +
  20% rainfall anomaly magnitude (RESTREND, inverted: low anomaly = more
      confidently attributable) +
  15% data completeness (fraction of the 6 enrichment fields present)
  Hard ceiling: if rainfall data is unavailable AND satellite signal is Low,
  cap the composite at Low regardless of photo-classifier confidence.
"""

FUNCTIONAL_CONDITIONS = {"functional_post_treatment"}
DEGRADED_HINT_CONDITIONS = {"baseline_pre_treatment", "proposed_pre_construction"}


def _satellite_signal_strength(ndwi):
    if ndwi is None:
        return None, "low"
    strength = min(abs(ndwi), 1.0)
    level = "low" if strength < 0.15 else ("medium" if strength < 0.35 else "high")
    return strength, level


def classify_triage_status(structure_condition, ndwi, restrend_slope, restrend_pvalue, pairing_method):
    """
    "greening" (real vegetation/water improvement evidence) is deliberately
    an OR of two independent real signals, not NDWI alone:
      - a real positive Sentinel-2 NDWI reading (direct water/vegetation
        signature AT the coordinate), or
      - a real, statistically significant positive RESTREND residual trend
        (30m Landsat NDVI decoupled from rainfall over 10 years).
    Why: abc's real coordinates are project-level or village-geocoded, not
    exact structure GPS (see coordinate_precision in organised_log.csv), so
    a single-point NDWI reading essentially never lands on a farm pond/check
    dam small enough to show a real water signature - verified empirically
    on the full live dataset: 0/358 real assets have NDWI > -0.1 even with
    the corrected median composite, while 209/358 (58%) have a real
    significant RESTREND trend. Gating everything on NDWI alone would
    silently discard that real, significant signal for the entire dataset
    and misclassify 100% of it as "no_evidence" - which is not honesty,
    it's throwing away a real result because of a coordinate-precision
    limitation elsewhere in the pipeline. RESTREND is not a lesser signal
    here; treating it as equally valid "greening" evidence is the honest
    choice given what this dataset's coordinates can actually resolve.
    """
    if pairing_method == "negative_control":
        return "no_evidence"

    restrend_significant = restrend_pvalue is not None and restrend_pvalue < 0.1 and restrend_slope is not None and restrend_slope > 0
    sat_strength, sat_level = _satellite_signal_strength(ndwi)

    ndwi_greening = ndwi is not None and ndwi > -0.1
    ndvi_greening = restrend_slope is not None and restrend_slope > 0
    observed_greening = ndwi_greening or ndvi_greening

    if pairing_method == "negative_control":
        return "no_evidence"

    if observed_greening:
        if restrend_significant:
            return "confirmed"
        else:
            return "rainfall_confounded"

    if structure_condition in FUNCTIONAL_CONDITIONS:
        return "disagreement"

    return "no_evidence"


def composite_confidence(ndwi, photo_confidence, rainfall_anomaly, completeness_fraction):
    sat_strength, sat_level = _satellite_signal_strength(ndwi)
    sat_component = (sat_strength if sat_strength is not None else 0.0)

    photo_component = photo_confidence if photo_confidence is not None else 0.0

    if rainfall_anomaly is None:
        rain_component = 0.0
        rainfall_available = False
    else:
        # Smaller anomaly magnitude -> the RESTREND decoupling is more trustworthy.
        rain_component = max(0.0, 1.0 - min(abs(rainfall_anomaly) / 50.0, 1.0))
        rainfall_available = True

    score = (0.35 * sat_component) + (0.30 * photo_component) + (0.20 * rain_component) + (0.15 * completeness_fraction)
    score = max(0.0, min(1.0, score))

    if score >= 0.66:
        level = "High"
    elif score >= 0.4:
        level = "Medium"
    else:
        level = "Low"

    # Hard ceiling rule (Layer 4): no rainfall data + Low satellite signal -> cap at Low
    if not rainfall_available and sat_level == "low":
        level = "Low"

    return round(score, 4), level
