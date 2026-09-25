export type TriageStatus = "confirmed" | "rainfall_confounded" | "disagreement" | "no_evidence";
export type ConfidenceLevel = "High" | "Medium" | "Low";

export interface AssetSummary {
  id: number;
  project_id: string;
  state_code: string;
  state_name: string;
  district: string;
  ps_category: string;
  latitude: number;
  longitude: number;
  structure_condition: string;
  pairing_method: "same_page" | "document_fallback" | "negative_control" | "village_geocoded" | "district_fallback" | string;
  triage_status: TriageStatus;
  disagreement_type: string | null;
  routed_role: SpecialistRole | null;
  confidence_score: number | null;
  confidence_level: ConfidenceLevel | null;
  admin_locality: string | null;
  admin_subdistrict: string | null;
  elevation_m: number | null;
  slope_deg: number | null;
  bhuvan_baseline_lulc?: string | null;
  sentinel_current_lulc?: string | null;
}

export interface Photo {
  id: number;
  ground_photo_path: string;
  structure_condition: string;
  page_num: number | null;
  point_idx: number | null;
  pairing_method: string;
  drishti_id?: string | null;
  mws_code?: string | null;
  activity_type?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  predicted_label: string | null;
  predicted_confidence: number | null;
  predicted_condition: string | null;
  predicted_condition_confidence: number | null;
  corrected_label: string | null;
}

export interface AssetDetail extends AssetSummary {
  bhuvan_baseline_lulc: string | null;
  sentinel_current_lulc: string | null;
  sentinel_ndwi: number | null;
  soil_texture_class: string | null;
  space_tile_path: string | null;
  restrend_slope: number | null;
  restrend_pvalue: number | null;
  restrend_rainfall_anomaly: number | null;
  photos: Photo[];
}

export interface RestrendPoint {
  year: number;
  month: number;
  ndvi_observed: number | null;
  precipitation_mm: number | null;
  ndvi_modeled: number | null;
  residual: number | null;
}

export interface RestrendSeries {
  asset_id: number;
  restrend_slope: number | null;
  restrend_pvalue: number | null;
  rainfall_anomaly: number | null;
  points: RestrendPoint[];
}

export interface TemporalSide {
  available: boolean;
  sensor: string | null;
  resolution_m: number | null;
  date: string | null;
  thumb_url: string | null;
}

export interface TemporalComparison {
  before: TemporalSide;
  after: TemporalSide;
  highres_ortho_url?: string | null;
  buffer_m?: number;
  sensor_mismatch: boolean;
  months_apart: number | null;
  t0_is_documented_project_date: boolean;
  t0_note: string;
}

export interface CrossValidation {
  id: number;
  asset_id: number;
  satellite_verdict: string | null;
  photo_classification: string | null;
  disagreement_type: string | null;
  routed_role: string | null;
  rule_applied: string | null;
  created_at: string;
}

export interface ReviewRouting {
  asset: AssetSummary;
  recommended_roles: string[];
}

export type SpecialistRole =
  | "water_management"
  | "agriculture"
  | "soil_science"
  | "social_mobilization"
  | "committee_member";

export interface FeasibilityResponse {
  predicted_class: string;
  predicted_probability: number;
  trained_n: number;
  cross_val_accuracy: number | null;
  note: string;
}

export interface DispatchLog {
  id: number;
  asset_id: number;
  trigger_reason: string;
  mode: "live" | "simulated";
  payload_en: string;
  payload_hi: string;
  payload_te: string;
  verification_link: string | null;
  delivery_status: string;
  created_at: string;
}

export const TRIAGE_COLORS: Record<TriageStatus, string> = {
  confirmed: "#16a34a",
  rainfall_confounded: "#d97706",
  disagreement: "#dc2626",
  no_evidence: "#6b7280",
};

export const TRIAGE_LABELS: Record<TriageStatus, string> = {
  confirmed: "Confirmed",
  rainfall_confounded: "Rainfall-Confounded",
  disagreement: "Disagreement",
  no_evidence: "No Evidence",
};

export interface HydrologyData {
  sub_watershed: {
    subwatershed_id: string;
    name: string;
    area_sqkm: number;
    slope_avg_deg: number;
    color: string;
  };
  nearest_stream: {
    distance_m: number;
    order: number;
    order_name: string;
    flow_accumulation: number;
  };
  pooling_screening: {
    label: string;
    extent_m2: number;
    flow_accum_cells: number;
    dem_slope_status: string;
  };
  hydrologic_hierarchy: string[];
  streams_geojson: GeoJSON.FeatureCollection;
  subwatersheds_geojson: GeoJSON.FeatureCollection;
  pooling_geojson?: GeoJSON.FeatureCollection;
}

export interface VegetationMapData {
  type: "FeatureCollection";
  features: GeoJSON.Feature[];
  legend: {
    min_ndvi: number;
    max_ndvi: number;
    unit: string;
    gradient: string[];
    labels: string[];
  };
}

export interface LandUseMapData {
  type: "FeatureCollection";
  features: GeoJSON.Feature[];
  class_breakdown: Record<string, number>;
  total_sites: number;
}

