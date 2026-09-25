"""
Layer 7.1 - Direct geotagged photo upload (the primary live-demo ingestion
path). Extracts real GPS EXIF from the uploaded file, rejects it if there's
no GPS tag or the point falls outside every known state bounding box (same
boundary-validation rule the offline pipeline enforces), then runs one
combined live Earth Engine query, a Bhuvan WMS baseline lookup, a reverse
geocode, and the CLIP classifier - and writes a new Asset + Photo.
"""
import io
import os
import uuid

import ee
import requests
from bs4 import BeautifulSoup
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

import ml_engine
import models
import restrend_engine
import triage
from database import SessionLocal
from state_registry import STATE_REGISTRY, BHUVAN_WMS_ENDPOINT

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
UPLOAD_DIR = os.path.join(REPO_ROOT, "all_india_watershed_dataset", "uploads", "ground_photos")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ENRICHMENT_FIELDS_FOR_COMPLETENESS = 6  # matches seed_data.ENRICHMENT_FIELDS


def _dms_to_decimal(dms, ref):
    degrees, minutes, seconds = dms
    value = float(degrees) + float(minutes) / 60.0 + float(seconds) / 3600.0
    if ref in ("S", "W"):
        value = -value
    return value


def extract_gps(image: Image.Image):
    exif = image.getexif()
    if not exif:
        return None
    gps_ifd = exif.get_ifd(0x8825)  # GPSInfo tag
    if not gps_ifd:
        return None
    gps = {GPSTAGS.get(k, k): v for k, v in gps_ifd.items()}
    if "GPSLatitude" not in gps or "GPSLongitude" not in gps:
        return None
    lat = _dms_to_decimal(gps["GPSLatitude"], gps.get("GPSLatitudeRef", "N"))
    lon = _dms_to_decimal(gps["GPSLongitude"], gps.get("GPSLongitudeRef", "E"))
    return lat, lon


def find_state(lat, lon):
    for code, info in STATE_REGISTRY.items():
        min_lon, min_lat, max_lon, max_lat = info["bbox"]
        if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
            return code, info
    return None, None


def _bhuvan_baseline_lulc(lat, lon, wms_layer):
    params = {
        "SERVICE": "WMS", "VERSION": "1.1.1", "REQUEST": "GetFeatureInfo",
        "LAYERS": wms_layer, "QUERY_LAYERS": wms_layer, "STYLES": "",
        "BBOX": f"{lon-0.005},{lat-0.005},{lon+0.005},{lat+0.005}",
        "SRS": "EPSG:4326", "WIDTH": "512", "HEIGHT": "512", "X": "256", "Y": "256",
        "INFO_FORMAT": "text/html",
    }
    try:
        r = requests.get(BHUVAN_WMS_ENDPOINT, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        tbl = soup.find("table")
        if not tbl:
            return None
        trs = tbl.find_all("tr")
        if len(trs) <= 1:
            return None
        tds = trs[1].find_all("td")
        if len(tds) < 2:
            return None
        return " ".join(tds[1].get_text(strip=True).split())
    except Exception:
        return None


def _reverse_geocode(lat, lon):
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "json", "accept-language": "en"},
            headers={"User-Agent": "WatershedMonitoring/1.0 (SIH26015)"},
            timeout=8,
        )
        if r.status_code != 200:
            return None, None
        addr = r.json().get("address", {})
        locality = addr.get("village") or addr.get("hamlet") or addr.get("suburb") or addr.get("town") or "Rural Area"
        subdistrict = addr.get("subdistrict") or addr.get("county") or addr.get("state_district") or "Unspecified"
        return locality, subdistrict
    except Exception:
        return None, None


def process_uploaded_photo(filename: str, contents: bytes) -> dict:
    image = Image.open(io.BytesIO(contents))
    image.load()
    gps = extract_gps(image)
    if gps is None:
        raise ValueError("No GPS EXIF data found in the uploaded photo. A geotagged photo is required.")
    lat, lon = gps

    state_code, state_info = find_state(lat, lon)
    if state_code is None:
        raise ValueError(
            f"Coordinate ({lat:.5f}, {lon:.5f}) falls outside every known state bounding box - rejected at ingest time."
        )

    ee.Initialize()
    snapshot = restrend_engine.compute_live_snapshot(lat, lon)
    baseline_lulc = _bhuvan_baseline_lulc(lat, lon, state_info["wms_layer"])
    locality, subdistrict = _reverse_geocode(lat, lon)

    ext = os.path.splitext(filename)[1] or ".jpg"
    saved_name = f"upload_{uuid.uuid4().hex[:12]}{ext}"
    saved_path = os.path.join(UPLOAD_DIR, saved_name)
    image.convert("RGB").save(saved_path)

    db = SessionLocal()
    try:
        embed_cache = ml_engine.EmbeddingCache()
        predicted_label, predicted_confidence = None, None
        try:
            predicted_label, predicted_confidence, _vec = ml_engine.predict_for_photo(
                f"upload_{saved_name}", saved_path, embed_cache
            )
            embed_cache.save()
        except Exception:
            pass

        # Real S3-compatible cloud storage (Section 8/10), after CLIP has
        # read the local file it needs - local disk on a real container
        # host does not survive a redeploy, so a real upload needs a real
        # durable URL. Falls back to the local relative path (same as
        # before this session) only if storage genuinely isn't configured
        # or the real upload call fails - never silently claims cloud
        # durability it didn't actually get.
        ground_photo_path = os.path.relpath(saved_path, REPO_ROOT).replace("\\", "/")
        try:
            import storage
            if storage.storage_configured():
                ground_photo_path = storage.upload_photo(saved_path, saved_name)
                os.remove(saved_path)  # real cloud copy is now the durable one - don't keep an ephemeral local duplicate
        except Exception as e:
            print(f"[ingest_pipeline] Cloud storage upload failed, using local path: {e}")

        present_fields = sum(1 for v in [
            baseline_lulc, snapshot.get("sentinel_current_lulc"), snapshot.get("sentinel_ndwi"),
            snapshot.get("soil_texture_class"), locality, subdistrict,
        ] if v is not None)
        completeness = present_fields / ENRICHMENT_FIELDS_FOR_COMPLETENESS

        asset = models.Asset(
            project_id=f"DIRECT_UPLOAD_{uuid.uuid4().hex[:8]}",
            state_code=state_code,
            state_name=state_info["name"],
            district=subdistrict or "Unknown",
            ps_category="water_conservation_structures",
            latitude=lat,
            longitude=lon,
            structure_condition="unspecified",
            pairing_method="same_page",
            bhuvan_baseline_lulc=baseline_lulc,
            sentinel_current_lulc=snapshot.get("sentinel_current_lulc"),
            sentinel_ndwi=snapshot.get("sentinel_ndwi"),
            soil_texture_class=snapshot.get("soil_texture_class"),
            admin_locality=locality,
            admin_subdistrict=subdistrict,
            elevation_m=snapshot.get("elevation_m"),
            slope_deg=snapshot.get("slope_deg"),
            space_tile_path=None,
            restrend_slope=None,
            restrend_pvalue=None,
            restrend_rainfall_anomaly=None,
        )
        db.add(asset)
        db.flush()

        asset.triage_status = triage.classify_triage_status(
            asset.structure_condition, asset.sentinel_ndwi, None, None, asset.pairing_method
        )
        score, level = triage.composite_confidence(
            asset.sentinel_ndwi, predicted_confidence, None, completeness
        )
        asset.confidence_score = score
        asset.confidence_level = level

        photo = models.Photo(
            asset_id=asset.id,
            ground_photo_path=ground_photo_path,
            structure_condition="unspecified",
            pairing_method="same_page",
            predicted_label=predicted_label,
            predicted_confidence=predicted_confidence,
        )
        db.add(photo)
        db.commit()
        db.refresh(asset)

        return {
            "asset_id": asset.id,
            "latitude": lat,
            "longitude": lon,
            "state_code": state_code,
            "predicted_structure_label": predicted_label,
            "predicted_confidence": predicted_confidence,
            "sentinel_ndwi": asset.sentinel_ndwi,
            "sentinel_current_lulc": asset.sentinel_current_lulc,
            "bhuvan_baseline_lulc": asset.bhuvan_baseline_lulc,
            "soil_texture_class": asset.soil_texture_class,
            "elevation_m": asset.elevation_m,
            "slope_deg": asset.slope_deg,
            "triage_status": asset.triage_status,
            "confidence_level": asset.confidence_level,
            "note": "RESTREND history not yet available for this new point - triage will update once the async backfill runs.",
        }
    finally:
        db.close()
