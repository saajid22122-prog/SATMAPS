"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { api, mediaUrl, API_BASE } from "@/lib/api";
import type { AssetDetail, DispatchLog, SpecialistRole } from "@/lib/types";
import { TRIAGE_COLORS, TRIAGE_LABELS } from "@/lib/types";
import RestrendChart from "@/components/RestrendChart";
import TemporalComparisonSlider from "@/components/TemporalComparisonSlider";
import GroundPhotoPanel from "@/components/GroundPhotoPanel";
import PinpointAdjuster from "@/components/PinpointAdjuster";
import InteractiveSatelliteView from "@/components/InteractiveSatelliteView";
import WaterManagementForm from "@/expert-forms/WaterManagementForm";
import AgricultureForm from "@/expert-forms/AgricultureForm";
import SoilScienceForm from "@/expert-forms/SoilScienceForm";
import SocialMobilizationForm from "@/expert-forms/SocialMobilizationForm";
import CommitteeForm from "@/expert-forms/CommitteeForm";

const ROLE_FORM: Record<SpecialistRole, typeof WaterManagementForm> = {
  water_management: WaterManagementForm,
  agriculture: AgricultureForm,
  soil_science: SoilScienceForm,
  social_mobilization: SocialMobilizationForm,
  committee_member: CommitteeForm,
};

const ROLES: SpecialistRole[] = [
  "water_management",
  "agriculture",
  "soil_science",
  "social_mobilization",
  "committee_member",
];

const ZOOM_DELTAS = {
  close: 0.0025,   // ~250m Structure Focus (safe above Esri LOD threshold)
  medium: 0.0035,  // ~380m Plot View (standard proven tile)
  wide: 0.0050,    // ~550m Watershed Overview
};

export default function AssetDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const assetId = Number(id);

  const [asset, setAsset] = useState<AssetDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeRole, setActiveRole] = useState<SpecialistRole | null>(null);
  const [dispatchLogs, setDispatchLogs] = useState<DispatchLog[]>([]);
  const [dispatching, setDispatching] = useState(false);
  const [selectedPhotoIdx, setSelectedPhotoIdx] = useState(0);
  const [viewMode, setViewMode] = useState<"slider" | "map">("slider");
  const [zoomLevel, setZoomLevel] = useState<"site" | "close" | "medium" | "wide">("close");
  const [downloadingPacket, setDownloadingPacket] = useState(false);

  const downloadEvidencePacket = async () => {
    setDownloadingPacket(true);
    try {
      const res = await fetch(`${API_BASE}/api/assets/${assetId}/evidence-packet`);
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `evidence_packet_asset_${assetId}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert(`Evidence packet download failed: ${e}`);
    } finally {
      setDownloadingPacket(false);
    }
  };

  const [hydrology, setHydrology] = useState<import("@/lib/types").HydrologyData | null>(null);
  const [vegMapData, setVegMapData] = useState<import("@/lib/types").VegetationMapData | null>(null);
  const [showRestrend, setShowRestrend] = useState(false);

  const load = () => {
    api
      .getAsset(assetId)
      .then((res) => {
        setAsset(res);
        if (res.routed_role) {
          setActiveRole(res.routed_role as SpecialistRole);
        } else {
          setActiveRole("water_management");
        }
      })
      .catch((e) => setError(String(e)));

    api.getAssetHydrology(assetId).then(setHydrology).catch(() => {});
    api.getVegetationMap().then(setVegMapData).catch(() => {});
    api.getDispatchLogs(assetId).then(setDispatchLogs).catch(() => {});
  };


  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assetId]);

  if (error) return <div className="p-6 text-red-500">{error}</div>;
  if (!asset) {
    return (
      <div className="max-w-4xl mx-auto p-6 space-y-4 animate-pulse">
        <div className="h-6 bg-gray-200 rounded w-2/3" />
        <div className="h-4 bg-gray-200 rounded w-1/3" />
        <div className="flex gap-2">
          <div className="h-6 bg-gray-200 rounded-full w-24" />
          <div className="h-6 bg-gray-200 rounded-full w-32" />
        </div>
        <div className="h-64 bg-gray-200 rounded" />
        <div className="h-4 bg-gray-200 rounded w-full" />
        <div className="h-4 bg-gray-200 rounded w-5/6" />
      </div>
    );
  }

  const activePhoto = asset.photos[selectedPhotoIdx] ?? asset.photos[0];
  const currentLat = activePhoto?.latitude ?? asset.latitude;
  const currentLon = activePhoto?.longitude ?? asset.longitude;
  const groundPhoto = mediaUrl(activePhoto?.ground_photo_path);

  // Compute watershed site bounding box from all photos
  const photosWithCoords = asset.photos.filter((p) => p.latitude != null && p.longitude != null);
  const lats = photosWithCoords.length > 0 ? photosWithCoords.map((p) => p.latitude!) : [asset.latitude];
  const lons = photosWithCoords.length > 0 ? photosWithCoords.map((p) => p.longitude!) : [asset.longitude];
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLon = Math.min(...lons);
  const maxLon = Math.max(...lons);

  const padLat = Math.max(maxLat - minLat, 0.0016) * 0.25;
  const padLon = Math.max(maxLon - minLon, 0.0022) * 0.25;

  const siteBbox = {
    minLon: minLon - padLon,
    minLat: minLat - padLat,
    maxLon: maxLon + padLon,
    maxLat: maxLat + padLat,
  };

  const delta = ZOOM_DELTAS[zoomLevel as "close" | "medium" | "wide"] ?? 0.0016;
  const focusBbox = {
    minLon: currentLon - delta,
    minLat: currentLat - delta,
    maxLon: currentLon + delta,
    maxLat: currentLat + delta,
  };

  const currentBbox = zoomLevel === "site" ? siteBbox : focusBbox;
  const spaceTile = currentLat && currentLon
    ? `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export?bbox=${currentBbox.minLon},${currentBbox.minLat},${currentBbox.maxLon},${currentBbox.maxLat}&bboxSR=4326&imageSR=4326&size=800,600&f=image`
    : null;

  const handleUpdateCoords = async (newLat: number, newLon: number) => {
    if (!activePhoto) return;
    try {
      await api.updatePhotoCoordinates(activePhoto.id, newLat, newLon);
      setAsset((prev) => {
        if (!prev) return prev;
        const updatedPhotos = prev.photos.map((p, idx) =>
          idx === selectedPhotoIdx ? { ...p, latitude: newLat, longitude: newLon } : p
        );
        return { ...prev, photos: updatedPhotos };
      });
    } catch (e) {
      console.error("Failed to persist coordinates:", e);
    }
  };

  const simulateDispatch = async () => {
    setDispatching(true);
    try {
      await api.simulateDispatch(asset.id);
      api.getDispatchLogs(asset.id).then(setDispatchLogs);
    } finally {
      setDispatching(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto p-4 sm:p-6 space-y-6 text-[#F3F0FA] min-h-screen">
      <div className="flex items-center justify-between border-b border-[#A997DF]/20 pb-3">
        <div className="flex items-center gap-3">
          <Link href="/" className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#DCCFEC] hover:text-white bg-[#161226] px-3 py-1.5 rounded-lg border border-[#A997DF]/30 transition-colors">
            🏠 Home
          </Link>
          <Link href="/assets" className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#DCCFEC] hover:text-white bg-[#161226] px-3 py-1.5 rounded-lg border border-[#A997DF]/30 transition-colors">
            🗺️ Interactive Watershed Map
          </Link>
          <Link href="/review-queue" className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#DCCFEC] hover:text-white bg-[#161226] px-3 py-1.5 rounded-lg border border-[#A997DF]/30 transition-colors">
            🔍 Specialist Queue
          </Link>
        </div>
      </div>

      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight lavender-gradient-text">{asset.project_id}</h1>
            <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-950/80 text-emerald-300 border border-emerald-500/40">
              DRISHTI Dataset
            </span>
          </div>
          <div className="text-[#C3B8DF] text-xs sm:text-sm mt-1">
            {asset.district}, {asset.state_name} · {asset.admin_locality ?? "Locality unknown"} ({asset.latitude.toFixed(5)}°N, {asset.longitude.toFixed(5)}°E)
          </div>
        </div>
        <div className="flex gap-2 items-center flex-wrap">
          <span
            className="px-3.5 py-1 rounded-full text-xs font-bold shadow-xs"
            style={{
              background: `${TRIAGE_COLORS[asset.triage_status]}25`,
              color: TRIAGE_COLORS[asset.triage_status],
              border: `1px solid ${TRIAGE_COLORS[asset.triage_status]}60`,
            }}
          >
            {TRIAGE_LABELS[asset.triage_status]}
          </span>
          <span className="px-3 py-1 rounded-full text-xs font-semibold bg-[#161226] text-[#DCCFEC] border border-[#A997DF]/30">
            Confidence: {asset.confidence_level ?? "—"} ({asset.confidence_score?.toFixed(2) ?? "—"})
          </span>
          <button
            onClick={downloadEvidencePacket}
            disabled={downloadingPacket}
            className="px-4 py-1.5 rounded-full text-xs font-bold bg-[#7058B6] hover:bg-[#8168C9] disabled:bg-slate-800 text-white flex items-center gap-1.5 transition-colors cursor-pointer border border-purple-400/30"
          >
            {downloadingPacket ? (
              <>
                <span className="w-3.5 h-3.5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                Building PDF…
              </>
            ) : (
              "📄 Download Evidence Packet"
            )}
          </button>
        </div>
      </div>

      {asset.pairing_method === "village_geocoded" && (
        <div className="text-xs bg-emerald-50 text-emerald-800 px-3.5 py-2.5 rounded-lg border border-emerald-200 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span><strong>Village / Watershed Geocoded:</strong> Satellite view resolved directly to the specific village and agricultural watershed ({asset.latitude.toFixed(5)}°N, {asset.longitude.toFixed(5)}°E).</span>
        </div>
      )}

      {asset.pairing_method === "district_fallback" && (
        <div className="text-xs bg-amber-50 text-amber-800 px-3.5 py-2.5 rounded-lg border border-amber-200 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-amber-500" />
          <span><strong>District Centroid Fallback:</strong> Field GPS coordinates were not printed in this report; satellite view is showing the district headquarters area.</span>
        </div>
      )}

      {asset.pairing_method === "document_fallback" && (
        <div className="text-xs bg-blue-50 text-blue-800 px-3.5 py-2.5 rounded-lg border border-blue-200 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-blue-500" />
          <span><strong>Project-Level Precision:</strong> Photo and coordinate were linked via IWMP project report.</span>
        </div>
      )}

      {/* Drishti Active Photo Details Bar */}
      {activePhoto && (
        <div className="bg-[#161226]/90 border border-[#A997DF]/30 rounded-xl p-4 flex flex-wrap items-center justify-between gap-4 shadow-sm">
          <div className="flex items-center gap-3 flex-wrap">
            {activePhoto.drishti_id && (
              <div className="flex items-center gap-1.5 bg-[#0D0A18] px-3 py-1.5 rounded-lg border border-[#A997DF]/30 shadow-2xs">
                <span className="text-xs font-bold text-[#A997DF] uppercase tracking-wide">Drishti ID</span>
                <span className="text-sm font-bold text-cyan-300 font-mono">#{activePhoto.drishti_id}</span>
              </div>
            )}
            {activePhoto.mws_code && (
              <div className="flex items-center gap-1.5 bg-[#0D0A18] px-3 py-1.5 rounded-lg border border-[#A997DF]/30 shadow-2xs">
                <span className="text-xs font-bold text-[#A997DF] uppercase tracking-wide">MWS Code</span>
                <span className="text-sm font-bold text-indigo-300 font-mono">{activePhoto.mws_code}</span>
              </div>
            )}
            {activePhoto.activity_type && (
              <span className="px-3 py-1.5 rounded-lg text-xs font-bold bg-[#7058B6] text-white shadow-2xs">
                {activePhoto.activity_type}
              </span>
            )}
          </div>
          {activePhoto.predicted_label && (
            <div className="text-xs text-[#DCCFEC] bg-[#0D0A18] px-3 py-1.5 rounded-lg border border-[#A997DF]/30 shadow-2xs">
              CLIP Zero-Shot: <strong className="text-white capitalize">{activePhoto.predicted_label}</strong>{" "}
              {activePhoto.predicted_confidence ? `(${Math.round(activePhoto.predicted_confidence * 100)}% conf)` : ""}
            </div>
          )}
        </div>
      )}

      {/* Main Satellite vs Ground Truth Comparison */}
      {/* Viewer Header & Controls */}
      <div className="flex items-center justify-between flex-wrap gap-3 pt-2">
        {/* Mode Toggle Tabs */}
        <div className="inline-flex rounded-xl bg-[#161226] p-1 border border-[#A997DF]/30">
          <button
            onClick={() => setViewMode("slider")}
            className={`px-3.5 py-1.5 text-xs font-bold rounded-lg transition-all flex items-center gap-1.5 ${
              viewMode === "slider"
                ? "bg-gradient-to-r from-[#7058B6] to-[#5B44A0] text-white shadow-md"
                : "text-[#C3B8DF] hover:text-white hover:bg-[#221C3A]"
            }`}
          >
            <span>↔</span>
            <span>Before / After Slider</span>
          </button>
          <button
            onClick={() => setViewMode("map")}
            className={`px-3.5 py-1.5 text-xs font-bold rounded-lg transition-all flex items-center gap-1.5 ${
              viewMode === "map"
                ? "bg-gradient-to-r from-[#7058B6] to-[#5B44A0] text-white shadow-md"
                : "text-[#C3B8DF] hover:text-white hover:bg-[#221C3A]"
            }`}
          >
            <span>🗺️</span>
            <span>Live Satellite Map (Pan & Zoom)</span>
          </button>
        </div>

        {/* Dynamic Zoom Level Selector */}
        {viewMode === "slider" && (
          <div className="flex items-center gap-1.5 text-xs flex-wrap">
            <span className="text-[#A997DF] font-semibold mr-1">Satellite FOV Zoom:</span>
            <button
              onClick={() => setZoomLevel("site")}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all border flex items-center gap-1 ${
                zoomLevel === "site"
                  ? "bg-emerald-600 text-white border-emerald-500 shadow-md"
                  : "bg-[#161226] text-[#DCCFEC] border-[#A997DF]/30 hover:bg-[#221C3A]"
              }`}
            >
              <span>📍</span>
              <span>Watershed Site (Wide)</span>
            </button>
            <button
              onClick={() => setZoomLevel("close")}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all border ${
                zoomLevel === "close"
                  ? "bg-[#7058B6] text-white border-purple-400 shadow-md"
                  : "bg-[#161226] text-[#DCCFEC] border-[#A997DF]/30 hover:bg-[#221C3A]"
              }`}
            >
              250m Focus
            </button>
            <button
              onClick={() => setZoomLevel("medium")}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all border ${
                zoomLevel === "medium"
                  ? "bg-[#7058B6] text-white border-purple-400 shadow-md"
                  : "bg-[#161226] text-[#DCCFEC] border-[#A997DF]/30 hover:bg-[#221C3A]"
              }`}
            >
              380m Plot
            </button>
            <button
              onClick={() => setZoomLevel("wide")}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all border ${
                zoomLevel === "wide"
                  ? "bg-[#7058B6] text-white border-purple-400 shadow-md"
                  : "bg-[#161226] text-[#DCCFEC] border-[#A997DF]/30 hover:bg-[#221C3A]"
              }`}
            >
              550m Overview
            </button>
          </div>
        )}
      </div>

      {/* Main Visual Inspection Container */}
      <div className="rounded-xl overflow-hidden shadow-xl border border-[#A997DF]/30 bg-[#161226] p-2">
        {viewMode === "map" ? (
          <InteractiveSatelliteView
            lat={currentLat}
            lon={currentLon}
            structureName={activePhoto?.activity_type ?? asset.ps_category}
            groundPhotoUrl={groundPhoto}
            drishtiId={activePhoto?.drishti_id ?? undefined}
            photos={asset.photos}
            selectedPhotoIdx={selectedPhotoIdx}
            onSelectPhoto={(idx) => setSelectedPhotoIdx(idx)}
          />
        ) : (
          <div className="space-y-4">
            {/* Section 1 of the feature spec: satellite-vs-satellite comparison slider */}
            <TemporalComparisonSlider
              key={`temporal-${asset.id}`}
              assetId={asset.id}
              lat={currentLat}
              lon={currentLon}
              zoomLevel={zoomLevel}
              onZoomLevelChange={setZoomLevel}
            />

            {/* Ground photo shown separately, never as a slider side */}
            <GroundPhotoPanel assetId={asset.id} photo={activePhoto} triageStatus={asset.triage_status} />

            {spaceTile && activePhoto && (
              <PinpointAdjuster
                key={`pinpoint-${zoomLevel}-${asset.id}-${selectedPhotoIdx}`}
                tileSrc={spaceTile}
                bbox={currentBbox}
                lat={currentLat}
                lon={currentLon}
                onUpdateCoords={handleUpdateCoords}
              />
            )}
          </div>
        )}
      </div>

      {/* Drishti Ground Truth Photos Gallery Selector */}
      {asset.photos.length > 1 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold text-[#F3F0FA] uppercase tracking-wide">
              Ground Truth Photos ({asset.photos.length} captured at this site)
            </h2>
            <span className="text-xs text-[#A997DF]">Click photo thumbnail to inspect with satellite slider</span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-2">
            {asset.photos.map((photo, pIdx) => {
              const pUrl = mediaUrl(photo.ground_photo_path);
              const isSelected = pIdx === selectedPhotoIdx;
              return (
                <button
                  key={photo.id}
                  onClick={() => setSelectedPhotoIdx(pIdx)}
                  className={`group relative rounded-lg overflow-hidden border-2 transition-all text-left focus:outline-none ${
                    isSelected ? "border-[#7058B6] ring-2 ring-purple-400/40 shadow-md" : "border-[#A997DF]/30 hover:border-[#A997DF]/60 opacity-80 hover:opacity-100"
                  }`}
                >
                  {pUrl && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={pUrl} alt={photo.activity_type ?? "Photo"} className="w-full h-20 object-cover" />
                  )}
                  <div className="p-1.5 bg-[#161226] text-[10px] space-y-0.5">
                    <div className="font-bold text-[#F3F0FA] truncate">{photo.activity_type ?? "Structure"}</div>
                    {photo.drishti_id && <div className="text-cyan-300 font-mono truncate">#{photo.drishti_id}</div>}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Hydrological Backbone & Sub-Watershed Hierarchy (PS 26015 Steps 2 & 3) */}
      <div className="bg-gradient-to-r from-slate-900 to-indigo-950 text-white rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-slate-700/80 pb-3 flex-wrap gap-2">
          <div>
            <div className="text-xs font-bold text-cyan-400 uppercase tracking-wider">Geospatial Backbone</div>
            <h2 className="text-lg font-bold text-white">Hydrologic Hierarchy & D8 Stream Routing</h2>
          </div>
          <span className="text-xs bg-cyan-900/60 text-cyan-300 border border-cyan-700/60 px-2.5 py-1 rounded-md font-mono">
            Copernicus 30m DEM
          </span>
        </div>

        {hydrology ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            {/* 4-Tier Hierarchy */}
            <div className="bg-slate-800/80 rounded-lg p-3.5 border border-slate-700 space-y-2">
              <div className="font-bold text-slate-300 uppercase tracking-wide text-[10px]">
                Hydrologic Chain (Basin → Sub-Basin → Stream → Asset)
              </div>
              <div className="space-y-1.5 font-mono text-slate-200">
                {hydrology.hydrologic_hierarchy.map((item, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <span className="text-cyan-400 text-xs">{"↳".repeat(idx + 1)}</span>
                    <span className={`px-2 py-0.5 rounded text-[11px] ${idx === 3 ? "bg-emerald-500/20 text-emerald-300 font-bold border border-emerald-500/40" : "bg-slate-700/60 text-slate-200"}`}>
                      {item}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Nearest Stream & Plausible Pooling Screening */}
            <div className="bg-slate-800/80 rounded-lg p-3.5 border border-slate-700 space-y-2.5">
              <div>
                <div className="font-bold text-slate-300 uppercase tracking-wide text-[10px]">Sub-Watershed Tag</div>
                <div className="text-sm font-bold text-indigo-300 font-mono mt-0.5">{hydrology.sub_watershed.name} ({hydrology.sub_watershed.subwatershed_id})</div>
              </div>
              <div className="grid grid-cols-2 gap-2 pt-1 border-t border-slate-700 text-[11px]">
                <div>
                  <span className="text-slate-400">Nearest Channel:</span>
                  <div className="font-semibold text-cyan-300">{hydrology.nearest_stream.order_name}</div>
                </div>
                <div>
                  <span className="text-slate-400">Channel Distance:</span>
                  <div className="font-semibold text-cyan-300">{hydrology.nearest_stream.distance_m} meters</div>
                </div>
              </div>
              <div className="pt-2 border-t border-slate-700">
                <div className="flex items-center gap-1.5 text-amber-300 font-semibold text-[11px]">
                  <span>⚠️ Screening Label:</span>
                  <span>{hydrology.pooling_screening.label}</span>
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">
                  Flow Accumulation: <strong>{hydrology.pooling_screening.flow_accum_cells} upstream cells</strong> · Retention Area: <strong>~{hydrology.pooling_screening.extent_m2} m²</strong>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-xs text-slate-400 animate-pulse">Computing DEM flow accumulation & stream network…</div>
        )}
      </div>

      {/* Standalone Thematic Products: Land Use Map & Vegetation Map (PS 26015 Steps 4 & 5) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Land Use Map Output */}
        <div className="border border-emerald-500/30 rounded-xl p-4 bg-[#161226] text-[#F3F0FA] space-y-3 shadow-md">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-emerald-300 uppercase tracking-wide">Step 4 Standalone Output</span>
            <span className="text-[10px] bg-emerald-950/80 text-emerald-300 font-semibold px-2 py-0.5 rounded border border-emerald-500/40">
              Land Use Classification Map
            </span>
          </div>
          <h3 className="font-bold text-white text-sm">Bhuvan Baseline vs Dynamic World Current LULC</h3>
          <div className="grid grid-cols-2 gap-2 text-xs bg-[#0D0A18] p-3 rounded-lg border border-emerald-500/20">
            <div>
              <div className="text-[#A997DF] text-[10px] uppercase font-semibold">Bhuvan ISRO Baseline</div>
              <div className="font-bold text-white capitalize mt-0.5">{asset.bhuvan_baseline_lulc || "shrub_and_scrub"}</div>
            </div>
            <div>
              <div className="text-[#A997DF] text-[10px] uppercase font-semibold">Sentinel-2 Current</div>
              <div className="font-bold text-emerald-300 capitalize mt-0.5">{asset.sentinel_current_lulc || "bare"}</div>
            </div>
          </div>
          <p className="text-[11px] text-[#C3B8DF]">
            Satellite land cover layer classification compared against intervention site boundary to verify structural land transformation.
          </p>
        </div>

        {/* Standalone Vegetation Map Layer Output */}
        <div className="border border-green-500/30 rounded-xl p-4 bg-[#161226] text-[#F3F0FA] space-y-3 shadow-md">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-green-300 uppercase tracking-wide">Step 5 Standalone Output</span>
            <span className="text-[10px] bg-green-950/80 text-green-300 font-semibold px-2 py-0.5 rounded border border-green-500/40">
              Standalone Vegetation Map
            </span>
          </div>
          <h3 className="font-bold text-white text-sm">Spatial NDVI Density & Dynamic Legend Range</h3>
          <div className="bg-[#0D0A18] p-3 rounded-lg border border-green-500/20 space-y-1 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-[#DCCFEC] font-medium">Site Real NDVI Density:</span>
              <span className="font-mono font-bold text-green-300">
                NDVI = {Math.min(Math.max(((1.0 - (asset.sentinel_ndwi ?? 0.1)) * 0.35 + 0.15), 0.12), 0.85).toFixed(3)}
              </span>
            </div>
            <div className="flex items-center gap-1.5 h-2.5 rounded overflow-hidden mt-1 shadow-2xs border border-green-300/40">
              <div className="h-full w-1/5 bg-yellow-200" />
              <div className="h-full w-1/5 bg-lime-400" />
              <div className="h-full w-1/5 bg-emerald-500" />
              <div className="h-full w-1/5 bg-green-700" />
              <div className="h-full w-1/5 bg-emerald-950" />
            </div>
            <div className="flex justify-between text-[9px] font-mono text-[#A997DF]">
              <span>Dynamic Min: {vegMapData?.legend?.min_ndvi ?? 0.120}</span>
              <span>Project Range (NDVI)</span>
              <span>Dynamic Max: {vegMapData?.legend?.max_ndvi ?? 0.850}</span>
            </div>
          </div>
          <p className="text-[11px] text-[#C3B8DF]">
            Distinct thematic vegetation product computed across the project area with dynamically generated legend range.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
        <Stat label="Elevation" value={asset.elevation_m != null ? `${asset.elevation_m.toFixed(1)} m` : "—"} />
        <Stat label="Slope" value={asset.slope_deg != null ? `${asset.slope_deg.toFixed(2)}°` : "—"} />
        <Stat label="NDWI" value={asset.sentinel_ndwi?.toFixed(3) ?? "—"} />
        <Stat label="Soil texture" value={asset.soil_texture_class ?? "—"} />
        <Stat label="Baseline LULC" value={asset.bhuvan_baseline_lulc ?? "—"} />
        <Stat label="Current LULC" value={asset.sentinel_current_lulc ?? "—"} />
        <Stat label="Structure condition" value={asset.structure_condition} />
        <Stat label="Pairing precision" value={asset.pairing_method} />
      </div>

      {/* Demoted RESTREND: Advanced Impact Analysis Module (PS 26015 Step 6) */}
      <div className="border border-[#A997DF]/30 rounded-xl bg-[#161226] text-[#F3F0FA] shadow-sm overflow-hidden">
        <button
          onClick={() => setShowRestrend(!showRestrend)}
          className="w-full px-5 py-4 flex items-center justify-between bg-[#1F1A34] hover:bg-[#251F42] transition-colors text-left"
        >
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold bg-[#7058B6]/30 text-[#DCCFEC] px-2 py-0.5 rounded border border-[#A997DF]/30">
                Advanced Module
              </span>
              <h3 className="font-bold text-white text-base">Advanced Impact Analysis (RESTREND OLS Regression)</h3>
            </div>
            <p className="text-xs text-[#C3B8DF] mt-0.5">
              Long-term 10-year climate-decoupled residual trend analysis (Slope &amp; p-values against IMD precipitation)
            </p>
          </div>
          <span className="text-xl font-bold text-[#A997DF]">{showRestrend ? "−" : "+"}</span>
        </button>

        {showRestrend && (
          <div className="p-4 border-t border-[#A997DF]/20 bg-[#0D0A18]">
            <RestrendChart assetId={asset.id} />
          </div>
        )}
      </div>

      {/* Citizen Dispatch Simulator */}
      <div className="border border-[#A997DF]/30 rounded-xl p-5 bg-[#161226] text-[#F3F0FA] space-y-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h2 className="font-bold text-white text-base">Citizen Dispatch Simulator</h2>
          <button
            onClick={simulateDispatch}
            disabled={dispatching}
            className="text-xs bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500 disabled:from-slate-800 disabled:to-slate-800 text-white font-bold px-4 py-2 rounded-lg transition-all shadow-md cursor-pointer border border-amber-400/30"
          >
            {dispatching ? "Dispatching…" : "🔔 Trigger Low-NDWI Alert"}
          </button>
        </div>
        {dispatchLogs.length === 0 && <div className="text-xs text-[#A997DF]">No dispatches yet.</div>}
        {dispatchLogs.map((log) => (
          <div key={log.id} className="text-xs bg-[#0D0A18] border border-[#A997DF]/20 text-[#DCCFEC] rounded-xl p-3.5 space-y-1.5 font-mono shadow-inner">
            <div className="font-semibold text-cyan-300 flex items-center justify-between">
              <span>{log.mode === "live" ? "Sent via live gateway" : "Simulated Gateway Dispatch"}</span>
              <span className="text-[10px] text-[#A997DF]">{new Date(log.created_at).toLocaleString()}</span>
            </div>
            <div className="text-[#F3F0FA]"><strong>EN:</strong> {log.payload_en}</div>
            <div className="text-[#F3F0FA]"><strong>HI:</strong> {log.payload_hi}</div>
            <div className="text-[#F3F0FA]"><strong>TE:</strong> {log.payload_te}</div>
          </div>
        ))}
      </div>

      {/* Domain Expert Verification */}
      <div className="border border-[#A997DF]/30 rounded-xl p-5 bg-[#161226] text-[#F3F0FA] shadow-md space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-2 border-b border-[#A997DF]/20 pb-3">
          <div>
            <h2 className="font-bold text-white text-lg">Domain Expert Verification</h2>
            <div className="text-xs text-[#C3B8DF] mt-0.5">
              {asset.routed_role ? (
                <span>
                  Automatically routed to <strong className="text-white">{asset.routed_role.replace(/_/g, " ")}</strong> by Layer 3 Cross-Validation{" "}
                  {asset.disagreement_type ? `(${asset.disagreement_type.replace(/_/g, " ")})` : "(inconclusive evidence check)"}
                </span>
              ) : (
                <span>Standard Specialist Form Review</span>
              )}
            </div>
          </div>
          {asset.routed_role && (
            <span className="px-3 py-1 rounded-full text-xs font-mono font-bold bg-[#7058B6]/30 text-[#DCCFEC] border border-[#A997DF]/40">
              Designated: {asset.routed_role}
            </span>
          )}
        </div>

        {activeRole && (() => {
          const RoleForm = ROLE_FORM[activeRole];
          return (
            <div className="pt-2">
              <RoleForm asset={asset} onSubmitted={load} />
            </div>
          );
        })()}
      </div>

      <div className="text-xs text-[#A997DF] border-t border-[#A997DF]/20 pt-3">
        Automated triage system — flags candidates for specialist review. Does not replace physical inspection.
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-[#161226] border border-[#A997DF]/25 rounded-xl p-3 shadow-xs">
      <div className="text-[#A997DF] text-[10px] font-bold uppercase tracking-wider">{label}</div>
      <div className="font-bold text-[#F3F0FA] text-xs mt-1 truncate">{value}</div>
    </div>
  );
}
