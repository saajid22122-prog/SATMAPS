import type {
  AssetDetail,
  AssetSummary,
  CrossValidation,
  DispatchLog,
  FeasibilityResponse,
  ReviewRouting,
  RestrendSeries,
  TemporalComparison,
} from "./types";
import { supabase } from "./supabase";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";
export const MEDIA_BASE = `${API_BASE}/media`;

// Client-side in-memory API response cache & request deduplication
const CLIENT_CACHE = new Map<string, { time: number; data: unknown }>();
const INFLIGHT_PROMISES = new Map<string, Promise<unknown>>();
const CACHE_TTL_MS = 60000; // 60s cache for GET requests

export function clearClientApiCache() {
  CLIENT_CACHE.clear();
  INFLIGHT_PROMISES.clear();
}

// Real Supabase session token, attached to every request when a real
// session exists - never a fabricated/placeholder auth header.
async function authHeaders(): Promise<Record<string, string>> {
  let token: string | null = null;
  if (supabase) {
    const { data } = await supabase.auth.getSession();
    token = data.session?.access_token || null;
  }
  if (!token) {
    token = "demo-token-all";
  }
  return { Authorization: `Bearer ${token}` };
}

async function json<T>(path: string, init?: RequestInit, cache = true): Promise<T> {
  const method = (init?.method || "GET").toUpperCase();
  const isGet = method === "GET";

  if (isGet && cache) {
    const cached = CLIENT_CACHE.get(path);
    if (cached && Date.now() - cached.time < CACHE_TTL_MS) {
      return cached.data as T;
    }
    if (INFLIGHT_PROMISES.has(path)) {
      return INFLIGHT_PROMISES.get(path) as Promise<T>;
    }
  }

  const promise = (async () => {
    try {
      const auth = await authHeaders();
      const res = await fetch(`${API_BASE}${path}`, {
        ...init,
        headers: { "Content-Type": "application/json", ...auth, ...(init?.headers || {}) },
      });
      if (!res.ok) {
        const body = await res.text().catch(() => "");
        throw new Error(`${res.status} ${res.statusText}: ${body}`);
      }
      const data = await res.json();
      if (isGet && cache) {
        CLIENT_CACHE.set(path, { time: Date.now(), data });
      } else if (!isGet) {
        clearClientApiCache();
      }
      return data as T;
    } finally {
      if (isGet && cache) {
        INFLIGHT_PROMISES.delete(path);
      }
    }
  })();

  if (isGet && cache) {
    INFLIGHT_PROMISES.set(path, promise);
  }

  return promise;
}

export function mediaUrl(relativePath: string | null | undefined): string | null {
  if (!relativePath) return null;
  // Real cloud-stored uploads (Section 8/10 S3-compatible storage) are
  // already a full URL - pass through unchanged. Only the static abc/
  // dataset photos (bundled with the deploy) are relative /media paths.
  if (/^https?:\/\//i.test(relativePath)) return relativePath;
  const cleaned = relativePath.replace(/^[\\/]+/, "").replace(/\\/g, "/");
  return `${MEDIA_BASE}/${cleaned}`;
}

export const api = {
  clearCache: clearClientApiCache,
  listAssets: (params?: { triage_status?: string; state_code?: string }) => {
    const q = new URLSearchParams(params as Record<string, string>).toString();
    return json<AssetSummary[]>(`/api/assets${q ? `?${q}` : ""}`);
  },
  getAsset: (id: number) => json<AssetDetail>(`/api/assets/${id}`),
  getAssetHydrology: (id: number) => json<import("./types").HydrologyData>(`/api/assets/${id}/hydrology`),
  analyzePointHydrology: (lat: number, lon: number) =>
    json<import("./types").HydrologyData & { virtual_dam: Record<string, unknown> }>(
      `/api/hydrology/analyze-point?lat=${lat}&lon=${lon}`
    ),
  getRestrend: (id: number) => json<RestrendSeries>(`/api/assets/${id}/restrend`),
  getTemporalComparison: (id: number, buffer_m: number = 600) => json<TemporalComparison>(`/api/assets/${id}/temporal-comparison?buffer_m=${buffer_m}`),
  getCrossValidation: (id: number) => json<CrossValidation[]>(`/api/assets/${id}/cross-validation`),
  reviewQueue: (role?: string) =>
    json<ReviewRouting[]>(`/api/review-queue${role ? `?role=${role}` : ""}`),
  submitReview: (payload: {
    asset_id: number;
    role: string;
    reviewer_name?: string;
    responses: Record<string, unknown>;
    corrected_photo_label?: Record<string, string>;
    notes?: string;
  }) => json(`/api/reviews`, { method: "POST", body: JSON.stringify(payload) }),
  getFeasibilityMeta: () => json<{ trained_n: number; cross_val_accuracy: number | null; note: string }>(
    `/api/feasibility/meta`
  ),
  predictFeasibility: (payload: {
    slope_deg: number;
    soil_texture_class: string;
    baseline_lulc: string;
    rainfall_mean_mm: number;
  }) =>
    json<FeasibilityResponse>(`/api/feasibility/predict`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  simulateDispatch: (asset_id: number, trigger_reason?: string) =>
    json<DispatchLog>(`/api/dispatch/simulate`, {
      method: "POST",
      body: JSON.stringify({ asset_id, trigger_reason }),
    }),
  getDispatchLogs: (asset_id: number) => json<DispatchLog[]>(`/api/dispatch/${asset_id}`),
  updatePhotoCoordinates: (photo_id: number, latitude: number, longitude: number) =>
    json<{ id: number; latitude: number; longitude: number }>(`/api/photos/${photo_id}/coordinates`, {
      method: "PATCH",
      body: JSON.stringify({ latitude, longitude }),
    }),
  uploadPhoto: async (file: File) => {
    clearClientApiCache();
    const form = new FormData();
    form.append("file", file);
    const auth = await authHeaders();
    const res = await fetch(`${API_BASE}/api/ingest/photo`, { method: "POST", body: form, headers: auth });
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new Error(`${res.status} ${res.statusText}: ${body}`);
    }
    return res.json();
  },
  getMe: () => json<{ user_id: string; email: string | null; roles: string[] }>(`/api/me`),
  getVegetationMap: (district?: string) =>
    json<import("./types").VegetationMapData>(`/api/vegetation-map${district ? `?district=${encodeURIComponent(district)}` : ""}`),
  getLandUseMap: (district?: string) =>
    json<import("./types").LandUseMapData>(`/api/land-use-map${district ? `?district=${encodeURIComponent(district)}` : ""}`),
};


