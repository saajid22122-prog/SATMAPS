from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class PhotoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ground_photo_path: str
    structure_condition: str
    page_num: Optional[int]
    point_idx: Optional[int]
    pairing_method: str
    drishti_id: Optional[str] = None
    mws_code: Optional[str] = None
    activity_type: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    predicted_label: Optional[str] = None
    predicted_confidence: Optional[float] = None
    predicted_condition: Optional[str] = None
    predicted_condition_confidence: Optional[float] = None
    corrected_label: Optional[str] = None


class PhotoCoordinatesIn(BaseModel):
    latitude: float
    longitude: float


class RestrendPointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    year: int
    month: int
    ndvi_observed: Optional[float]
    precipitation_mm: Optional[float]
    ndvi_modeled: Optional[float]
    residual: Optional[float]


class AssetSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: str
    state_code: str
    state_name: str
    district: str
    ps_category: str
    latitude: float
    longitude: float
    structure_condition: str
    pairing_method: str
    triage_status: Optional[str] = None
    disagreement_type: Optional[str] = None
    routed_role: Optional[str] = None
    confidence_score: Optional[float]
    confidence_level: Optional[str]
    admin_locality: Optional[str]
    admin_subdistrict: Optional[str]
    elevation_m: Optional[float]
    slope_deg: Optional[float]
    bhuvan_baseline_lulc: Optional[str] = None
    sentinel_current_lulc: Optional[str] = None


class AssetDetailOut(AssetSummaryOut):
    bhuvan_baseline_lulc: Optional[str]
    sentinel_current_lulc: Optional[str]
    sentinel_ndwi: Optional[float]
    soil_texture_class: Optional[str]
    space_tile_path: Optional[str]
    restrend_slope: Optional[float]
    restrend_pvalue: Optional[float]
    restrend_rainfall_anomaly: Optional[float]
    photos: list[PhotoOut] = []


class CrossValidationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    satellite_verdict: Optional[str]
    photo_classification: Optional[str]
    disagreement_type: Optional[str]
    routed_role: Optional[str]
    rule_applied: Optional[str]
    created_at: datetime


class RestrendSeriesOut(BaseModel):
    asset_id: int
    restrend_slope: Optional[float]
    restrend_pvalue: Optional[float]
    rainfall_anomaly: Optional[float]
    points: list[RestrendPointOut]


class ReviewIn(BaseModel):
    asset_id: int
    role: str
    reviewer_name: Optional[str] = None
    responses: dict[str, Any]
    corrected_photo_label: Optional[dict[str, str]] = None  # {photo_id: new_label}
    notes: Optional[str] = None


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    role: str
    reviewer_name: Optional[str]
    responses: dict[str, Any]
    notes: Optional[str]
    submitted_at: datetime


class FeasibilityRequest(BaseModel):
    slope_deg: float
    soil_texture_class: str
    baseline_lulc: str
    rainfall_mean_mm: float


class FeasibilityResponse(BaseModel):
    predicted_class: str
    predicted_probability: float
    trained_n: int
    cross_val_accuracy: float
    note: str


class DispatchSimulateRequest(BaseModel):
    asset_id: int
    trigger_reason: str = "3 consecutive low-NDWI readings at a functional water structure"


class DispatchLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    trigger_reason: str
    mode: str
    payload_en: str
    payload_hi: str
    payload_te: str
    verification_link: Optional[str]
    delivery_status: str
    created_at: datetime
