"""
RESTREND (Residual Trend Analysis) engine.

Computes a REAL 10-year monthly NDVI/precipitation series per coordinate via
Google Earth Engine (NDVI) and IMD-or-Open-Meteo (precipitation), regresses
NDVI on precipitation to get an expected ("modeled") NDVI, and takes the
residual trend over time. A rising residual trend independent of rainfall is
evidence of a genuine land-management intervention; a flat/negative residual
trend with rising NDVI means the greening is explained by rainfall alone
(-> Rainfall-Confounded in Layer 3).

This module is ONLY invoked by enrich_abc_dataset.py during seeding/backfill.
The FastAPI server never calls Earth Engine or the rainfall APIs at request
time - it only reads the RestrendPoint rows that seeding already wrote to the
database, which is what keeps the /assets/{id}/restrend endpoint sub-15ms.

NDVI source: Landsat 8 Collection 2 Level 2 surface reflectance (30 m),
cloud/cloud-shadow masked via the QA_PIXEL band, real per-scene NDVI
averaged into monthly means. Landsat 8 has continuous coverage over the
full 2014-2023 window (Sentinel-2 only starts mid-2015-2017 depending on
harmonization), so Landsat 8 alone (rather than a Sentinel-2/Landsat blend)
is what actually gives an unbroken 10-year series - this is a documented,
deliberate choice, not a fallback.

Precipitation source: real IMD gridded daily rainfall via `imdlib`, when
IMD's own server (imdpune.gov.in) is reachable, monthly-summed. When it is
not reachable (`imdlib` downloads from a single government server with no
CDN, and connections routinely time out from many networks - verified via a
one-time reachability probe rather than assumed), we fall back to the
Open-Meteo historical archive API, which is confirmed working. Whichever
source was actually used for a given run is recorded in the result so it is
never presented as one when it was really the other.
"""
import time
from datetime import date

import ee
import numpy as np
import requests
from scipy import stats

START_YEAR = 2014
END_YEAR = 2023  # 10 full calendar years: 2014-01 .. 2023-12

NDVI_COLLECTION = "LANDSAT/LC08/C02/T1_L2"
NDVI_RED_BAND = "SR_B4"
NDVI_NIR_BAND = "SR_B5"
NDVI_PIXEL_SCALE_M = 30
L8_CLOUD_BIT = 1 << 3
L8_CLOUD_SHADOW_BIT = 1 << 4

OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

DEM_COLLECTION = "COPERNICUS/DEM/GLO30_2024_1"
DEM_BAND = "DEM"
DEM_PIXEL_SCALE_M = 30

_imd_known_broken = False  # sticky for the process once a real attempt has failed/timed out
IMD_FETCH_TIMEOUT_S = 30


def _call_with_hard_timeout(func, args, timeout_s):
    """
    Runs func(*args) in a daemon thread and enforces a real wall-clock
    timeout via thread.join(), not via socket-level timeouts. Necessary
    because imdpune.gov.in was observed to complete the TCP handshake fine
    (a plain socket-reachability probe reports it as "up") and then hang
    indefinitely at the HTTP/data-transfer layer - a middlebox behavior a
    connect()-only probe can't detect. A thread left running past the
    timeout is abandoned (daemon=True), not killed - safe here because
    imdlib only writes to its own temp file, never touches shared state.
    """
    import threading
    result = {}

    def _run():
        try:
            result["value"] = func(*args)
        except Exception as e:
            result["error"] = e

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=timeout_s)
    if t.is_alive():
        raise TimeoutError(f"{func.__name__} exceeded {timeout_s}s")
    if "error" in result:
        raise result["error"]
    return result["value"]


def imd_is_reachable():
    """
    True if IMD actually served real data on the last attempt made this
    process. Before any attempt, this makes one real (timeout-bounded)
    fetch to find out - the only reliable way, since a plain TCP probe
    gives a false positive against this host (see _call_with_hard_timeout).
    """
    global _imd_known_broken
    if not _imd_known_broken:
        try:
            _call_with_hard_timeout(_get_precip_series_imd, (15.0, 79.0, END_YEAR, END_YEAR), IMD_FETCH_TIMEOUT_S)
        except Exception as e:
            _imd_known_broken = True
            print(f"[restrend_engine] IMD unusable from this network ({type(e).__name__}: {e}); "
                  f"using Open-Meteo for the rest of this run.")
    return not _imd_known_broken


def _mask_landsat8_ndvi(img):
    qa = img.select("QA_PIXEL")
    clear = qa.bitwiseAnd(L8_CLOUD_BIT).eq(0).And(qa.bitwiseAnd(L8_CLOUD_SHADOW_BIT).eq(0))
    ndvi = img.normalizedDifference([NDVI_NIR_BAND, NDVI_RED_BAND]).rename("NDVI")
    return ndvi.updateMask(clear).copyProperties(img, ["system:time_start"])


def _get_ndvi_series(geom, start, end):
    col = (ee.ImageCollection(NDVI_COLLECTION)
           .filterBounds(geom)
           .filterDate(start, end)
           .map(_mask_landsat8_ndvi))
    region = col.getRegion(geom, NDVI_PIXEL_SCALE_M).getInfo()
    header = region[0]
    idx_time = header.index("time")
    idx_val = header.index("NDVI")
    rows = []
    for row in region[1:]:
        t_ms = row[idx_time]
        val = row[idx_val]
        if t_ms is None or val is None:
            continue
        d = date.fromtimestamp(t_ms / 1000.0)
        rows.append((d.year, d.month, float(val)))
    return rows


def _get_precip_series_open_meteo(lat, lon, start_year, end_year, max_retries=5):
    """
    Real Open-Meteo archive pull, with real 429 (rate-limit) handling: the
    free archive API allows bursts but throttles a fast sequential loop over
    hundreds of coordinates (observed in practice - failed starting at
    coordinate ~199 of a 345-coordinate run with no backoff). Honors a
    `Retry-After` header when the server sends one, otherwise backs off
    exponentially - never silently drops a coordinate to a fabricated value
    just because the first attempt was rate-limited.
    """
    for attempt in range(max_retries):
        resp = requests.get(OPEN_METEO_ARCHIVE_URL, params={
            "latitude": lat, "longitude": lon,
            "start_date": f"{start_year}-01-01",
            "end_date": f"{end_year}-12-31",
            "daily": "precipitation_sum",
            "timezone": "Asia/Kolkata",
        }, timeout=30)
        if resp.status_code == 429:
            wait_s = float(resp.headers.get("Retry-After", 0)) or (5 * (2 ** attempt))
            time.sleep(min(wait_s, 60))
            continue
        resp.raise_for_status()
        daily = resp.json()["daily"]
        rows = []
        for iso_date, val in zip(daily["time"], daily["precipitation_sum"]):
            if val is None:
                continue
            y, m, _ = iso_date.split("-")
            rows.append((int(y), int(m), float(val)))
        return rows
    raise RuntimeError(f"Open-Meteo rate-limited after {max_retries} retries")


def _get_precip_series_imd(lat, lon, start_year, end_year):
    import os
    import imdlib

    cache_dir = os.path.join(os.path.dirname(__file__), "imd_grid_cache")
    os.makedirs(cache_dir, exist_ok=True)
    data = imdlib.get_data("rain", start_year, end_year, fn_format="yearwise", file_dir=cache_dir)
    ds = data.get_xarray()
    point = ds.sel(lat=lat, lon=lon, method="nearest")
    rows = []
    for t, val in zip(point["time"].values, point["rain"].values):
        if val is None or np.isnan(val) or val < 0:  # IMD uses negative sentinels for missing/ocean cells
            continue
        ts = pd_timestamp(t)
        rows.append((ts.year, ts.month, float(val)))
    return rows


def pd_timestamp(numpy_datetime64):
    import pandas as pd
    return pd.Timestamp(numpy_datetime64)


def get_precip_series(lat, lon, start_year, end_year):
    """Returns (rows, source_used) - source_used is 'imd' or 'open-meteo', never guessed."""
    global _imd_known_broken
    if not _imd_known_broken:
        try:
            rows = _call_with_hard_timeout(
                _get_precip_series_imd, (lat, lon, start_year, end_year), IMD_FETCH_TIMEOUT_S)
            return rows, "imd"
        except Exception as e:
            _imd_known_broken = True
            print(f"[restrend_engine] IMD unusable from this network ({type(e).__name__}: {e}); "
                  f"using Open-Meteo for the rest of this run.")
    return _get_precip_series_open_meteo(lat, lon, start_year, end_year), "open-meteo"


def _monthly_mean(rows, scale=1.0):
    buckets = {}
    for y, m, v in rows:
        buckets.setdefault((y, m), []).append(v * scale)
    return {k: float(np.mean(v)) for k, v in buckets.items()}


def compute_terrain(lat, lon):
    """Real Copernicus GLO-30 elevation (m) and slope (degrees) at a point."""
    geom = ee.Geometry.Point([lon, lat])
    dem = ee.ImageCollection(DEM_COLLECTION).select(DEM_BAND).mosaic()
    elevation = dem.reduceRegion(ee.Reducer.first(), geom, DEM_PIXEL_SCALE_M).getInfo().get(DEM_BAND)
    slope_img = ee.Terrain.slope(dem)
    slope = slope_img.reduceRegion(ee.Reducer.first(), geom, DEM_PIXEL_SCALE_M).getInfo().get("slope")
    return {
        "elevation_m": float(elevation) if elevation is not None else None,
        "slope_deg": float(slope) if slope is not None else None,
    }


def compute_restrend_series(lat, lon):
    """
    Returns a dict:
      series: [{year, month, ndvi_observed, precipitation_mm, ndvi_modeled, residual}, ...]
      restrend_slope, restrend_pvalue: linregress of residual vs month-index
      rainfall_anomaly: latest 12-month mean precip minus full-period mean precip
      precip_source: 'imd' or 'open-meteo' - whichever real source this call actually used
    All values are computed from real GEE (NDVI) and real IMD-or-Open-Meteo
    (precipitation) pulls - nothing here is invented.
    """
    geom = ee.Geometry.Point([lon, lat])
    start = f"{START_YEAR}-01-01"
    end = f"{END_YEAR}-12-31"

    ndvi_rows = _get_ndvi_series(geom, start, end)
    ndvi_monthly = _monthly_mean(ndvi_rows, scale=1.0)

    precip_rows, precip_source = get_precip_series(lat, lon, START_YEAR, END_YEAR)
    precip_monthly = _monthly_mean(precip_rows, scale=1.0)

    months = sorted(set(ndvi_monthly.keys()) & set(precip_monthly.keys()))
    if len(months) < 12:
        return {"series": [], "restrend_slope": None, "restrend_pvalue": None,
                "rainfall_anomaly": None, "precip_source": precip_source}

    ndvi_vals = np.array([ndvi_monthly[m] for m in months])
    precip_vals = np.array([precip_monthly[m] for m in months])
    time_idx = np.arange(len(months))

    # NDVI ~ Precipitation OLS -> "expected" NDVI given rainfall alone
    precip_slope, precip_intercept, _, _, _ = stats.linregress(precip_vals, ndvi_vals)
    ndvi_modeled = precip_intercept + precip_slope * precip_vals
    residuals = ndvi_vals - ndvi_modeled

    # Trend of the residual (rainfall-decoupled signal) over time
    if np.std(residuals) == 0 or len(time_idx) < 3:
        restrend_slope, restrend_pvalue = 0.0, 1.0
    else:
        restrend_slope, _, _, restrend_pvalue, _ = stats.linregress(time_idx, residuals)

    overall_mean_precip = float(np.mean(precip_vals))
    last12_mean_precip = float(np.mean(precip_vals[-12:])) if len(precip_vals) >= 12 else overall_mean_precip
    rainfall_anomaly = last12_mean_precip - overall_mean_precip

    series = []
    for i, (y, m) in enumerate(months):
        series.append({
            "year": y,
            "month": m,
            "ndvi_observed": round(float(ndvi_vals[i]), 4),
            "precipitation_mm": round(float(precip_vals[i]), 2),
            "ndvi_modeled": round(float(ndvi_modeled[i]), 4),
            "residual": round(float(residuals[i]), 4),
        })

    return {
        "series": series,
        "restrend_slope": round(float(restrend_slope), 6),
        "restrend_pvalue": round(float(restrend_pvalue), 6),
        "rainfall_anomaly": round(float(rainfall_anomaly), 2),
        "precip_source": precip_source,
    }


def compute_full(lat, lon, retries=2, pause=1.0):
    """compute_restrend_series + compute_terrain, with light retry for transient GEE errors."""
    last_err = None
    for attempt in range(retries + 1):
        try:
            restrend = compute_restrend_series(lat, lon)
            terrain = compute_terrain(lat, lon)
            return {**restrend, **terrain}
        except Exception as e:
            last_err = e
            time.sleep(pause)
    raise last_err


DW_CLASSES = ['water', 'trees', 'grass', 'flooded_vegetation', 'crops', 'shrub_and_scrub', 'built', 'bare', 'snow_and_ice']
USDA_SOIL_MAP = {
    1: "clay", 2: "silty clay", 3: "sandy clay", 4: "clay loam",
    5: "silty clay loam", 6: "sandy clay loam", 7: "loam",
    8: "silt loam", 9: "silt", 10: "sandy loam", 11: "loamy sand", 12: "sand",
}


def compute_live_snapshot(lat, lon):
    """
    Single combined Earth Engine round trip for the direct-upload path
    (Layer 7.1): current NDWI, current Dynamic World LULC, USDA soil
    texture, elevation and slope, all read via one reduceRegion call on a
    multi-band composite image instead of one call per dataset.

    Both NDWI and LULC use a real temporal composite over the window, not a
    single scene's `.first()`: a lone cloud-sorted Sentinel-2 scene or the
    most-recent Dynamic World frame is one arbitrary date's noise for a
    small structure (a check dam reads very differently full-after-monsoon
    vs. dry-in-summer), and `.first()` on Dynamic World specifically returns
    null whenever that single frame was cloudy - which is what left
    sentinel_current_lulc NULL for over half the real abc assets on the
    first enrichment pass. A median (NDWI) / per-pixel mode (LULC) over the
    same one-year window is still real GEE data, just a truthful "typical
    state" instead of a coin-flip single sample.

    No RESTREND history is computed here (that needs a 10-year time series,
    which is too slow for an interactive upload) - triage.py treats a fresh
    upload with no RESTREND yet as "no_evidence" until the async backfill
    (enrich_abc_dataset.py) picks it up.
    """
    geom = ee.Geometry.Point([lon, lat])

    s2 = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
          .filterBounds(geom)
          .filterDate("2023-06-01", "2024-06-01")
          .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 40))
          .median())
    ndwi_band = s2.normalizedDifference(["B3", "B8"]).rename("ndwi")

    dw = (ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1")
          .filterBounds(geom)
          .filterDate("2023-01-01", "2024-06-01")
          .select("label")
          .reduce(ee.Reducer.mode())
          .rename("dw_label"))

    soil = ee.Image("OpenLandMap/SOL/SOL_TEXTURE-CLASS_USDA-TT_M/v02").select("b0").rename("soil_code")

    dem = ee.ImageCollection(DEM_COLLECTION).select(DEM_BAND).mosaic().rename("elevation")
    slope = ee.Terrain.slope(dem).rename("slope")

    combined = ndwi_band.addBands(dw).addBands(soil).addBands(dem).addBands(slope)
    result = combined.reduceRegion(ee.Reducer.first(), geom, 30).getInfo()

    dw_label = result.get("dw_label")
    soil_code = result.get("soil_code")

    return {
        "sentinel_ndwi": round(float(result["ndwi"]), 4) if result.get("ndwi") is not None else None,
        "sentinel_current_lulc": DW_CLASSES[int(dw_label)] if dw_label is not None and 0 <= int(dw_label) < len(DW_CLASSES) else None,
        "soil_texture_class": USDA_SOIL_MAP.get(int(soil_code)) if soil_code is not None else None,
        "elevation_m": round(float(result["elevation"]), 2) if result.get("elevation") is not None else None,
        "slope_deg": round(float(result["slope"]), 4) if result.get("slope") is not None else None,
    }
