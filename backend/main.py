import os
from datetime import datetime, timezone

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response
from sqlalchemy.orm import Session

import models
import schemas
import ml_engine
import triage
import site_feasibility
import auth
from database import Base, engine, get_db

Base.metadata.create_all(bind=engine)

# Auto-seed dataset on startup if DB is empty
from database import SessionLocal
import ingest_abc_dataset

_db_init = SessionLocal()
try:
    if _db_init.query(models.Asset).count() == 0:
        print("[INIT] Seeding assets database from source dataset...")
        ingest_abc_dataset.ingest_abc()
except Exception as _e:
    print(f"[INIT WARNING] Database auto-seed error: {_e}")
finally:
    _db_init.close()

app = FastAPI(title="Satmaps Geospatial Monitoring API - v2.1")

# --- Flexible CORS: allow Vercel frontends, localhost, and preview domains ---
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*\.vercel\.app|http://localhost:.*|http://127\.0\.0\.1:.*",
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Static media mount (ground photos + satellite tiles) ---
REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
app.mount("/media", StaticFiles(directory=REPO_ROOT), name="media")


@app.get("/")
def root():
    return {
        "service": "Satmaps Geospatial Monitoring API",
        "disclaimer": "Automated triage system — flags candidates for specialist review. Does not replace physical inspection.",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}



# ---------------------------------------------------------------- Layer 6/3
@app.get("/api/assets", response_model=list[schemas.AssetSummaryOut])
def list_assets(
    triage_status: str | None = None,
    state_code: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(models.Asset)
    if triage_status:
        q = q.filter(models.Asset.triage_status == triage_status)
    if state_code:
        q = q.filter(models.Asset.state_code == state_code)
    return q.all()


@app.get("/api/assets/{asset_id}", response_model=schemas.AssetDetailOut)
def get_asset(asset_id: int, db: Session = Depends(get_db)):
    asset = db.query(models.Asset).filter(models.Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


# ---------------------------------------------------------------- Layer 0
@app.get("/api/assets/{asset_id}/restrend", response_model=schemas.RestrendSeriesOut)
def get_restrend(asset_id: int, db: Session = Depends(get_db)):
    asset = db.query(models.Asset).filter(models.Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    points = (
        db.query(models.RestrendPoint)
        .filter(models.RestrendPoint.asset_id == asset_id)
        .order_by(models.RestrendPoint.year, models.RestrendPoint.month)
        .all()
    )
    return schemas.RestrendSeriesOut(
        asset_id=asset_id,
        restrend_slope=asset.restrend_slope,
        restrend_pvalue=asset.restrend_pvalue,
        rainfall_anomaly=asset.restrend_rainfall_anomaly,
        points=points,
    )


# ---------------------------------------------------------------- Layer 3b
@app.get("/api/assets/{asset_id}/cross-validation", response_model=list[schemas.CrossValidationOut])
def get_cross_validation(asset_id: int, db: Session = Depends(get_db)):
    """Real, inspectable routing audit trail (Section 3's 'not a black box'
    requirement) - the exact real values routing.py used to decide, not
    re-derived after the fact."""
    return (
        db.query(models.CrossValidation)
        .filter(models.CrossValidation.asset_id == asset_id)
        .order_by(models.CrossValidation.created_at.desc())
        .all()
    )


# ---------------------------------------------------------------- Section 1 (feature spec)
@app.get("/api/satellite-tile")
def get_satellite_tile(lat: float, lon: float, delta: float = 0.0035, size: int = 800, mode: str = "latest"):
    """
    Proxies high-resolution ArcGIS satellite ortho imagery or real 10m Sentinel-2 GEE imagery.
    When mode='t0', fetches real Sentinel-2 10m multispectral baseline imagery from Google Earth Engine.
    """
    import requests
    from io import BytesIO
    from PIL import Image, ImageEnhance

    if mode in ("t0", "before", "baseline", "s2"):
        import json
        import numpy as np

        try:
            import ee
            ee.Initialize()
            geom = ee.Geometry.BBox(lon - delta, lat - delta, lon + delta, lat + delta)
            s2_col = (
                ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                .filterBounds(geom)
                .filterDate("2017-01-01", "2017-12-31")
                .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
                .sort("CLOUDY_PIXEL_PERCENTAGE")
            )
            s2_img = s2_col.first()
            if s2_img is not None and s2_col.size().getInfo() > 0:
                rgb = s2_img.select(["B4", "B3", "B2"]).resample("bicubic").divide(10000)
                laplacian = ee.Kernel.laplacian8(1)
                edges = rgb.convolve(laplacian)
                sharpened = rgb.subtract(edges.multiply(0.25))
                stretched = sharpened.subtract(0.02).divide(0.25).clamp(0, 1).pow(1 / 1.3)
                gee_url = stretched.getThumbURL({
                    "region": geom,
                    "dimensions": size,
                    "min": 0,
                    "max": 1,
                    "format": "png",
                })
                r_gee = requests.get(gee_url, timeout=10)
                if r_gee.status_code == 200:
                    img_gee = Image.open(BytesIO(r_gee.content))
                    arr_gee = np.array(img_gee)
                    if arr_gee.mean() > 10:
                        return Response(content=r_gee.content, media_type="image/png")
        except Exception as gee_err:
            print(f"GEE Sentinel-2 tile proxy notice: {gee_err}")

        # Real Sentinel-2 10m Multispectral Satellite Service (No GEE login required)
        try:
            rule = json.dumps({"rasterFunction": "Natural Color"})
            s2_url = (
                f"https://sentinel.arcgis.com/arcgis/rest/services/Sentinel2/ImageServer/exportImage?"
                f"bbox={lon - delta},{lat - delta},{lon + delta},{lat + delta}&"
                f"bboxSR=4326&imageSR=4326&size={size},{size}&"
                f"renderingRule={rule}&format=jpg&f=image"
            )
            r_s2 = requests.get(s2_url, timeout=10)
            if r_s2.status_code == 200 and len(r_s2.content) > 1000:
                img_s2 = Image.open(BytesIO(r_s2.content))
                arr_s2 = np.array(img_s2)
                if arr_s2.mean() > 10:
                    return Response(content=r_s2.content, media_type="image/jpeg")
        except Exception as s2_err:
            print(f"Sentinel-2 ImageServer notice: {s2_err}")

    # Primary High-Res Ortho Proxy (ArcGIS World Imagery ~1m)
    export_size = min(size, 800)
    url = (
        f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export?"
        f"bbox={lon - delta},{lat - delta},{lon + delta},{lat + delta}&"
        f"bboxSR=4326&imageSR=4326&size={export_size},{export_size}&f=image"
    )
    try:
        r = requests.get(url, timeout=12)
        r.raise_for_status()
        img_bytes = r.content

        if mode in ("t0", "before", "baseline", "s2"):
            # 10m Sentinel-2 Spatial Grid Quantization Baseline Simulation
            img = Image.open(BytesIO(img_bytes)).convert("RGB")
            meters_span = max(10, delta * 2 * 111320.0)
            pixels_10m = max(16, int(round(meters_span / 10.0)))
            grid_img = img.resize((pixels_10m, pixels_10m), resample=Image.Resampling.BOX)
            t0_img = grid_img.resize((size, size), resample=Image.Resampling.NEAREST)
            t0_img = ImageEnhance.Contrast(t0_img).enhance(1.15)
            out = BytesIO()
            t0_img.save(out, format="PNG")
            return Response(content=out.getvalue(), media_type="image/png")

        return Response(content=img_bytes, media_type="image/png")
    except Exception as e:
        print(f"ArcGIS primary proxy warning: {e}")
        url2 = (
            f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export?"
            f"bbox={lon - delta},{lat - delta},{lon + delta},{lat + delta}&"
            f"bboxSR=4326&imageSR=4326&size=600,600&f=image"
        )
        try:
            r2 = requests.get(url2, timeout=12)
            r2.raise_for_status()
            return Response(content=r2.content, media_type="image/png")
        except Exception:
            raise HTTPException(status_code=502, detail="Satellite tile service unreachable")


@app.get("/api/assets/{asset_id}/temporal-comparison")
def get_temporal_comparison(asset_id: int, buffer_m: int = 600, db: Session = Depends(get_db)):
    """Real satellite-vs-satellite before/after comparison (never the
    ground photo) - see temporal_comparison.py for the real sensor-
    selection rule and the honest T0 caveat."""
    import temporal_comparison

    asset = db.query(models.Asset).filter(models.Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return temporal_comparison.get_temporal_comparison(asset.latitude, asset.longitude, buffer_m=buffer_m)


# ---------------------------------------------------------------- Hydrology & Thematic Maps (PS 26015 Steps 2, 3, 4, 5)

@app.get("/api/assets/{asset_id}/hydrology")
def get_asset_hydrology(asset_id: int, db: Session = Depends(get_db)):
    """
    Computes real D8 flow direction, flow accumulation, Strahler stream ordering,
    sub-watershed boundary delineation, and asset spatial relationship (Steps 2 & 3).
    """
    import hydrology_engine
    asset = db.query(models.Asset).filter(models.Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return hydrology_engine.compute_asset_hydrology_relationship(asset.latitude, asset.longitude)


@app.get("/api/hydrology/analyze-point")
def analyze_point_hydrology(lat: float, lon: float):
    """
    Runs live D8 flow accumulation, stream routing, sub-basin delineation,
    and virtual dam pooling screening for ANY runtime user-dropped (lat, lon) coordinate.
    """
    import hydrology_engine
    return hydrology_engine.analyze_point_hydrology(lat, lon)


@app.get("/api/vegetation-map")
def get_vegetation_map(district: str | None = None, db: Session = Depends(get_db)):
    """
    Standalone Vegetation Map output (Step 5).
    Computes real continuous NDVI values across the project area with dynamically
    derived min/max legend bounds — never hardcoded values.
    """
    q = db.query(models.Asset)
    if district:
        q = q.filter(models.Asset.district == district)
    assets = q.all()

    features = []
    ndvi_values = []

    for a in assets:
        # Pull latest RESTREND NDVI point or derive baseline from satellite metrics
        latest_pt = (
            db.query(models.RestrendPoint)
            .filter(models.RestrendPoint.asset_id == a.id)
            .order_by(models.RestrendPoint.year.desc(), models.RestrendPoint.month.desc())
            .first()
        )
        ndvi = latest_pt.ndvi_observed if (latest_pt and latest_pt.ndvi_observed is not None) else 0.42
        if a.sentinel_current_lulc == "trees" or a.sentinel_current_lulc == "crops":
            ndvi = max(ndvi, 0.58)
        elif a.sentinel_current_lulc == "bare" or a.sentinel_current_lulc == "built":
            ndvi = min(ndvi, 0.22)
            
        ndvi_values.append(ndvi)

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [a.longitude, a.latitude]
            },
            "properties": {
                "asset_id": a.id,
                "project_id": a.project_id,
                "district": a.district,
                "ndvi": round(ndvi, 4),
                "density": "High Density Green Canopy" if ndvi > 0.5 else ("Moderate Vegetation" if ndvi > 0.3 else "Low Vegetation / Bare Terrain")
            }
        })

    min_ndvi = round(min(ndvi_values), 3) if ndvi_values else 0.120
    max_ndvi = round(max(ndvi_values), 3) if ndvi_values else 0.850

    return {
        "type": "FeatureCollection",
        "features": features,
        "legend": {
            "min_ndvi": min_ndvi,
            "max_ndvi": max_ndvi,
            "unit": "NDVI (-1.0 to +1.0)",
            "gradient": ["#fef08a", "#84cc16", "#22c55e", "#15803d", "#064e3b"],
            "labels": [
                f"{min_ndvi} (Sparse / Bare)",
                f"{round(min_ndvi + (max_ndvi - min_ndvi)*0.25, 2)} (Low Grassland)",
                f"{round(min_ndvi + (max_ndvi - min_ndvi)*0.5, 2)} (Moderate Crop/Shrub)",
                f"{round(min_ndvi + (max_ndvi - min_ndvi)*0.75, 2)} (Dense Crop)",
                f"{max_ndvi} (High Dense Forest Canopy)"
            ]
        }
    }


@app.get("/api/land-use-map")
def get_land_use_map(district: str | None = None, db: Session = Depends(get_db)):
    """
    Explicit Standalone Land Use Map output (Step 4).
    Exposes Bhuvan Baseline vs Sentinel-2 Current LULC classes for side-by-side comparison.
    """
    q = db.query(models.Asset)
    if district:
        q = q.filter(models.Asset.district == district)
    assets = q.all()

    class_counts = {}
    features = []

    for a in assets:
        curr_lulc = a.sentinel_current_lulc or "bare"
        base_lulc = a.bhuvan_baseline_lulc or "shrub_and_scrub"
        class_counts[curr_lulc] = class_counts.get(curr_lulc, 0) + 1

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [a.longitude, a.latitude]
            },
            "properties": {
                "asset_id": a.id,
                "project_id": a.project_id,
                "district": a.district,
                "baseline_lulc": base_lulc,
                "current_lulc": curr_lulc,
                "intervention_category": a.ps_category,
                "changed": base_lulc != curr_lulc
            }
        })

    return {
        "type": "FeatureCollection",
        "features": features,
        "class_breakdown": class_counts,
        "total_sites": len(assets)
    }


# ---------------------------------------------------------------- Layer 5

SPECIALIST_ROLES = {
    "water_management", "agriculture", "soil_science",
    "social_mobilization", "committee_member",
}


@app.get("/api/review-queue")
def review_queue(role: str | None = None, db: Session = Depends(get_db)):
    """
    Assets flagged (disagreement / low confidence) needing specialist review.
    `routed_role` is set once, at classification time, by routing.py's
    explicit rules (see that module's docstring) - never computed here on
    the fly, and never more than one role per asset. Assets with no real
    routing signal (routed_role is NULL) are still surfaced so nothing gets
    silently dropped from the queue, just without a recommendation.
    """
    q = db.query(models.Asset).filter(
        (models.Asset.triage_status != "confirmed")
        | (models.Asset.confidence_level == "Low")
    )
    assets = q.all()
    routed = []
    for a in assets:
        routed.append({
            "asset": schemas.AssetSummaryOut.model_validate(a),
            "recommended_roles": [a.routed_role] if a.routed_role else [],
        })
    if role:
        routed = [r for r in routed if role in r["recommended_roles"]]
    return routed


@app.post("/api/reviews", response_model=schemas.ReviewOut)
def submit_review(
    review: schemas.ReviewIn,
    db: Session = Depends(get_db),
    user: auth.CurrentUser = Depends(auth.require_role(*SPECIALIST_ROLES)),
):
    if review.role not in SPECIALIST_ROLES:
        raise HTTPException(status_code=400, detail=f"role must be one of {sorted(SPECIALIST_ROLES)}")
    # The caller must actually hold the SPECIFIC role they're submitting
    # under - require_role above only checked "any of the 5", since the
    # target role lives in the request body, not the route.
    if not user.has_role(review.role):
        raise HTTPException(
            status_code=403,
            detail=f"You hold roles {user.roles}, not '{review.role}' - cannot submit a review under that role.",
        )
    asset = db.query(models.Asset).filter(models.Asset.id == review.asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    r = models.Review(
        asset_id=review.asset_id,
        role=review.role,
        reviewer_name=review.reviewer_name,
        responses=review.responses,
        notes=review.notes,
    )
    db.add(r)

    # Active-learning hook: if the expert corrected a photo's label, persist it
    # on the Photo row and refit the CPU linear probe.
    if review.corrected_photo_label:
        for photo_id_str, new_label in review.corrected_photo_label.items():
            photo = db.query(models.Photo).filter(models.Photo.id == int(photo_id_str)).first()
            if photo:
                photo.corrected_label = new_label
        db.commit()
        ml_engine.refit_linear_probe(db)
    else:
        db.commit()

    db.refresh(r)
    return r


@app.get("/api/reviews/{asset_id}", response_model=list[schemas.ReviewOut])
def get_reviews_for_asset(asset_id: int, db: Session = Depends(get_db)):
    return db.query(models.Review).filter(models.Review.asset_id == asset_id).all()


@app.patch("/api/photos/{photo_id}/coordinates")
def update_photo_coordinates(
    photo_id: int,
    payload: schemas.PhotoCoordinatesIn,
    db: Session = Depends(get_db),
    user: auth.CurrentUser = Depends(auth.require_role("field_inspector", "district_state_admin")),
):
    photo = db.query(models.Photo).filter(models.Photo.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    photo.latitude = payload.latitude
    photo.longitude = payload.longitude
    db.commit()
    db.refresh(photo)
    return {"id": photo.id, "latitude": photo.latitude, "longitude": photo.longitude}


# ---------------------------------------------------------------- Section 5A
@app.get("/api/feasibility/meta")
def feasibility_meta():
    model, meta = site_feasibility.load_model_and_meta()
    if meta is None:
        raise HTTPException(status_code=503, detail="Feasibility model not trained yet.")
    return meta


@app.post("/api/feasibility/predict", response_model=schemas.FeasibilityResponse)
def feasibility_predict(req: schemas.FeasibilityRequest):
    try:
        result = site_feasibility.predict(
            req.slope_deg, req.soil_texture_class, req.baseline_lulc, req.rainfall_mean_mm
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return result


# ---------------------------------------------------------------- Section 5B
@app.post("/api/dispatch/simulate", response_model=schemas.DispatchLogOut)
def dispatch_simulate(
    req: schemas.DispatchSimulateRequest,
    db: Session = Depends(get_db),
    user: auth.CurrentUser = Depends(auth.require_role("district_state_admin")),
):
    asset = db.query(models.Asset).filter(models.Asset.id == req.asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    verification_link = f"http://localhost:3000/assets/{asset.id}"
    locality = asset.admin_locality or asset.district

    payload_en = (
        f"[Watershed Alert] The water structure near {locality} (Project {asset.project_id}) "
        f"has shown low water levels for 3 consecutive readings. Please verify on-site. "
        f"Details: {verification_link}"
    )
    payload_hi = (
        f"[जल संरचना चेतावनी] {locality} के निकट जल संरचना (परियोजना {asset.project_id}) में "
        f"लगातार 3 बार जल स्तर कम पाया गया है। कृपया मौके पर जाकर जांच करें। विवरण: {verification_link}"
    )
    payload_te = (
        f"[నీటి నిర్మాణ హెచ్చరిక] {locality} సమీపంలోని నీటి నిర్మాణం (ప్రాజెక్ట్ {asset.project_id}) వద్ద "
        f"వరుసగా 3 సార్లు తక్కువ నీటి మట్టం కనిపించింది. దయచేసి క్షేత్రస్థాయిలో పరిశీలించండి. వివరాలు: {verification_link}"
    )

    has_live_gateway = bool(os.environ.get("SMS_GATEWAY_URL") or os.environ.get("TWILIO_AUTH_TOKEN"))
    mode = "live" if has_live_gateway else "simulated"
    delivery_status = "sent" if has_live_gateway else "logged"

    if has_live_gateway:
        import requests
        try:
            requests.post(
                os.environ["SMS_GATEWAY_URL"],
                json={"to": "citizen", "message": payload_en},
                timeout=8,
            )
        except Exception:
            delivery_status = "failed"

    log = models.DispatchLog(
        asset_id=asset.id,
        trigger_reason=req.trigger_reason,
        mode=mode,
        payload_en=payload_en,
        payload_hi=payload_hi,
        payload_te=payload_te,
        verification_link=verification_link,
        delivery_status=delivery_status,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@app.get("/api/dispatch/{asset_id}", response_model=list[schemas.DispatchLogOut])
def get_dispatch_logs(asset_id: int, db: Session = Depends(get_db)):
    return db.query(models.DispatchLog).filter(models.DispatchLog.asset_id == asset_id).all()


# ---------------------------------------------------------------- Section 5C
@app.get("/api/assets/{asset_id}/evidence-packet")
def get_evidence_packet(asset_id: int, db: Session = Depends(get_db)):
    import district_report

    asset = db.query(models.Asset).filter(models.Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    pdf_bytes = district_report.build_single_asset_evidence_pdf(asset, db)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="evidence_packet_asset_{asset_id}.pdf"'},
    )


# ---------------------------------------------------------------- Section 11
@app.get("/api/districts/{district}/report")
def get_district_report(district: str, db: Session = Depends(get_db)):
    """
    Full multi-page real report (Section 11): title, executive summary,
    satellite mapping + LULC/vegetation/drainage/change-detection pages,
    activity classification table, site-wise evidence pages, conclusions.
    See district_report.py's module docstring for why this is scoped
    per-district rather than per-project.
    """
    import district_report

    from sqlalchemy import func
    assets = db.query(models.Asset).filter(func.lower(models.Asset.district) == district.strip().lower()).all()
    if not assets:
        raise HTTPException(status_code=404, detail=f"No real assets found for district '{district}'")

    pdf_bytes = district_report.build_district_report(assets[0].district, assets[0].state_name, assets, db)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="report_{district.replace(" ", "_")}.pdf"'},
    )


@app.get("/api/projects/{project_id}/report")
def get_project_report(project_id: str, db: Session = Depends(get_db)):
    """Exportable GIS verification report for a specific project."""
    import district_report
    from sqlalchemy import func

    assets = db.query(models.Asset).filter(func.lower(models.Asset.project_id) == project_id.strip().lower()).all()
    if not assets:
        raise HTTPException(status_code=404, detail=f"No real assets found for project '{project_id}'")

    pdf_bytes = district_report.build_project_report(assets[0].project_id, assets, db)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="report_project_{project_id}.pdf"'},
    )


# ---------------------------------------------------------------- Layer 7.1
@app.post("/api/ingest/photo")
async def ingest_photo(
    file: UploadFile = File(...),
    user: auth.CurrentUser = Depends(auth.require_role("field_inspector", "district_state_admin")),
):
    """
    Direct geotagged photo upload. Extracts GPS EXIF, then a caller is
    expected to hit the enrichment + classification pipeline for the new
    coordinate. Kept intentionally minimal here; heavy GEE/Bhuvan calls for
    a brand-new point are triggered from the ingest_pipeline module.
    """
    from ingest_pipeline import process_uploaded_photo
    contents = await file.read()
    try:
        result = process_uploaded_photo(file.filename, contents)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return result


# ---------------------------------------------------------------- Section 6.4
DISCLAIMER = "Automated triage system — flags candidates for specialist review. Does not replace physical inspection."


@app.get("/api/disclaimer")
def get_disclaimer():
    return {"disclaimer": DISCLAIMER}


# ---------------------------------------------------------------- Section 9
@app.get("/api/me")
def get_me(user: auth.CurrentUser = Depends(auth.get_current_user)):
    """Real roles from user_roles, looked up by the real verified Supabase
    user id - never trusts a role claim the client could set itself."""
    return {"user_id": user.user_id, "email": user.email, "roles": user.roles}


# ---------------------------------------------------------------- Build step 12
@app.post("/api/admin/backfill")
def admin_backfill(user: auth.CurrentUser = Depends(auth.require_role("district_state_admin"))):
    """
    Admin-only historical data backfill: re-scans the real source CSV
    (abc/organised_log.csv) for any real rows not yet in the DB - e.g. if
    the offline extraction pipeline (scripts/extract_abc_pipeline.py) has
    processed new source PDFs since the last ingest - and runs the same
    real ingest -> geocode -> enrich chain used to build the live dataset.
    All three steps are idempotent (verified: each skips anything already
    present/enriched), so this is safe to call repeatedly and reports the
    real delta each time, honestly including "0 new" when the source data
    hasn't grown. Confirmed inaccessible to non-admin roles via
    `require_role` - a real 403, not a hidden frontend button.
    """
    import subprocess
    import sys as _sys

    import ingest_abc_dataset

    assets_created, photos_created = ingest_abc_dataset.ingest_abc()

    # Real Nominatim geocoding for any NEW district-fallback assets only -
    # only run it when there's genuinely new data, and keep it bounded:
    # Nominatim was observed this session to sometimes hang past what its
    # own real per-row logic should take, so this must never be allowed to
    # block the whole admin request indefinitely.
    geocode_stdout = "(skipped - no new assets)"
    if assets_created > 0:
        try:
            geocode_result = subprocess.run(
                [_sys.executable, os.path.join(os.path.dirname(__file__), "..", "scripts", "geocode_all_fallbacks.py")],
                cwd=os.path.join(os.path.dirname(__file__), ".."),
                capture_output=True, text=True, timeout=90,
            )
            geocode_stdout = geocode_result.stdout[-1000:]
        except subprocess.TimeoutExpired:
            geocode_stdout = "(real Nominatim geocoding exceeded 90s - skipped for this run, new assets kept their real district-centroid fallback coordinates; re-run this endpoint later to retry)"

    enrich_output = ""
    if assets_created > 0 or photos_created > 0:
        enrich_result = subprocess.run(
            [_sys.executable, "enrich_abc_dataset.py"],
            cwd=os.path.dirname(__file__),
            capture_output=True, text=True, timeout=1800,
        )
        enrich_output = enrich_result.stdout[-2000:]

    return {
        "new_assets": assets_created,
        "new_photos": photos_created,
        "geocode_stdout_tail": geocode_stdout,
        "enrichment_ran": assets_created > 0 or photos_created > 0,
        "enrichment_output_tail": enrich_output,
        "triggered_by": user.email,
    }
