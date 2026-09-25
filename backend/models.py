from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Asset(Base):
    """One unique geolocation (structure/site). 98 real sites + negative controls."""
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(String, index=True)
    state_code = Column(String, index=True)
    state_name = Column(String)
    district = Column(String)
    ps_category = Column(String)

    latitude = Column(Float, index=True)
    longitude = Column(Float, index=True)

    structure_condition = Column(String)  # dominant condition across photos at this site
    pairing_method = Column(String)  # same_page (high precision) / document_fallback / negative_control

    bhuvan_baseline_lulc = Column(String)
    sentinel_current_lulc = Column(String)
    sentinel_ndwi = Column(Float, nullable=True)
    soil_texture_class = Column(String, nullable=True)
    admin_locality = Column(String, nullable=True)
    admin_subdistrict = Column(String, nullable=True)

    elevation_m = Column(Float, nullable=True)
    slope_deg = Column(Float, nullable=True)

    space_tile_path = Column(String, nullable=True)

    # Layer 3: 4-state triage output
    triage_status = Column(String, default="no_evidence")  # confirmed / rainfall_confounded / disagreement / no_evidence

    # Layer 3b: which specific mismatch pattern triggered "disagreement", and
    # which single expert role it routes to. Set once, at classification
    # time, in routing.py - never computed live when a review form opens.
    disagreement_type = Column(String, nullable=True)
    routed_role = Column(String, nullable=True)

    # Layer 4: composite confidence
    confidence_score = Column(Float, nullable=True)
    confidence_level = Column(String, nullable=True)  # High / Medium / Low

    # RESTREND summary (Layer 0) - real linear-regression outputs over the cached monthly series
    restrend_slope = Column(Float, nullable=True)
    restrend_pvalue = Column(Float, nullable=True)
    restrend_rainfall_anomaly = Column(Float, nullable=True)
    restrend_precip_source = Column(String, nullable=True)  # "imd" or "open-meteo" - whichever real source was actually used

    created_at = Column(DateTime, default=utcnow)

    photos = relationship("Photo", back_populates="asset", cascade="all, delete-orphan")
    restrend_points = relationship("RestrendPoint", back_populates="asset", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="asset", cascade="all, delete-orphan")
    dispatch_logs = relationship("DispatchLog", back_populates="asset", cascade="all, delete-orphan")


class Photo(Base):
    """Individual geotagged DRISHTI ground photo. 257 rows in the source CSV."""
    __tablename__ = "photos"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), index=True)

    ground_photo_path = Column(String)
    structure_condition = Column(String)
    page_num = Column(Integer, nullable=True)
    point_idx = Column(Integer, nullable=True)
    pairing_method = Column(String)
    pixel_variance_stddev = Column(Float, nullable=True)

    # Drishti metadata
    drishti_id = Column(String, nullable=True, index=True)
    mws_code = Column(String, nullable=True, index=True)
    activity_type = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Layer 2: active-learning CLIP linear-probe output
    predicted_label = Column(String, nullable=True)
    predicted_confidence = Column(Float, nullable=True)
    corrected_label = Column(String, nullable=True)  # set when an expert corrects it in Layer 5

    # Layer 2b: independent CLIP zero-shot pass over CONDITION_LABELS (same
    # cached embedding, different text prompts) - see ml_engine.py. This is
    # what makes a real satellite-vs-photo "disagreement" possible for the
    # abc dataset, which carries no pre/post condition label of its own.
    predicted_condition = Column(String, nullable=True)
    predicted_condition_confidence = Column(Float, nullable=True)

    asset = relationship("Asset", back_populates="photos")


class RestrendPoint(Base):
    """One monthly sample of the pre-computed 10-year RESTREND series for an asset."""
    __tablename__ = "restrend_points"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), index=True)

    year = Column(Integer)
    month = Column(Integer)
    ndvi_observed = Column(Float, nullable=True)
    precipitation_mm = Column(Float, nullable=True)
    ndvi_modeled = Column(Float, nullable=True)
    residual = Column(Float, nullable=True)

    asset = relationship("Asset", back_populates="restrend_points")


class Review(Base):
    """Layer 5 expert review submission, routed to a specific specialist role."""
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), index=True)

    role = Column(String, index=True)  # water_management / agriculture / soil_science / social_mobilization / committee_member
    reviewer_name = Column(String, nullable=True)
    responses = Column(JSON)  # form-specific answers
    corrected_photo_label = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    submitted_at = Column(DateTime, default=utcnow)

    asset = relationship("Asset", back_populates="reviews")


class DispatchLog(Base):
    """Citizen SMS/WhatsApp dispatch trail (Section 5B) - real send or simulated audit entry."""
    __tablename__ = "dispatch_logs"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), index=True)

    trigger_reason = Column(String)
    mode = Column(String)  # "live" (real gateway credentials present) / "simulated"
    payload_en = Column(Text)
    payload_hi = Column(Text)
    payload_te = Column(Text)
    verification_link = Column(String, nullable=True)
    delivery_status = Column(String, default="logged")

    created_at = Column(DateTime, default=utcnow)

    asset = relationship("Asset", back_populates="dispatch_logs")


class UserRole(Base):
    """
    Section 9 role-based access. `user_id` is the real Supabase Auth user
    id (the `sub` claim of the verified JWT) - no separate password/identity
    storage here, Supabase Auth owns that entirely. One row per
    (user, role) pair, so one real person can hold multiple roles (e.g. a
    Field Inspector who is also a Water Management Expert) without
    duplicating their account.
    """
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    email = Column(String, nullable=True)  # convenience copy from the JWT claim, not the source of truth
    role = Column(String, index=True, nullable=False)
    # District/State Admin only: restricts their admin scope to one real state; NULL = unrestricted admin
    state_scope = Column(String, nullable=True)
    created_at = Column(DateTime, default=utcnow)


class CrossValidation(Base):
    """
    Layer 3b audit trail (spec Section 3's "routing logic that ties all
    five [roles] together"): one real row per classification run,
    recording exactly what was compared and what it produced. Written by
    routing.py at classification time - never computed live when a review
    form opens. `Asset.disagreement_type`/`Asset.routed_role` remain the
    fast summary fields the API reads (avoids an extra join on every list
    request); this table is the inspectable record of *why*.
    """
    __tablename__ = "cross_validations"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), index=True)

    satellite_verdict = Column(String, nullable=True)  # e.g. "wet" / "dry", derived from real sentinel_ndwi at write time
    photo_classification = Column(String, nullable=True)  # the real dominant CLIP predicted_condition used
    disagreement_type = Column(String, nullable=True)
    routed_role = Column(String, nullable=True)
    rule_applied = Column(String, nullable=True)  # which real routing.py rule fired, for a human audit trail

    created_at = Column(DateTime, default=utcnow)

    asset = relationship("Asset")
