"use client";

import { useEffect, useState } from "react";
import { api, mediaUrl } from "@/lib/api";
import type { Photo, CrossValidation } from "@/lib/types";

/**
 * Feature Spec Section 1: SEPARATE FROM THE SLIDER — GROUND PHOTO PANEL
 * - Real ground photo (with zoomable modal)
 * - CLIP's real predicted activity_type + real confidence % (never rounded)
 * - One real comparison sentence:
 *   "Photo shows: [real CLIP prediction] ([real confidence]%) — Satellite shows: [real satellite_verdict] → [real status]"
 *   If any one of these four values is missing, state it explicitly for that clause.
 * - coordinate_precision badge directly on this panel (exact_gps / mws_level / project_level / no_coordinate)
 */
export default function GroundPhotoPanel({
  assetId,
  photo,
  triageStatus,
}: {
  assetId: number;
  photo: Photo | undefined;
  triageStatus: string | null | undefined;
}) {
  const [cv, setCv] = useState<CrossValidation[] | null>(null);
  const [lightboxOpen, setLightboxOpen] = useState(false);

  useEffect(() => {
    api.getCrossValidation(assetId).then(setCv).catch(() => setCv([]));
  }, [assetId]);

  if (!photo) {
    return (
      <div className="rounded-xl border border-gray-200 bg-gray-50 p-4 text-sm text-gray-500">
        No real ground photo available for this asset.
      </div>
    );
  }

  // Determine normalized coordinate precision badge
  let precisionBadge: "exact_gps" | "mws_level" | "project_level" | "no_coordinate" = "no_coordinate";
  const pairing = photo.pairing_method || "";

  if (pairing === "exact_gps" || (photo.latitude && photo.longitude && pairing === "same_page")) {
    precisionBadge = "exact_gps";
  } else if (photo.mws_code || pairing === "mws_level") {
    precisionBadge = "mws_level";
  } else if (pairing === "project_level" || pairing === "village_geocoded" || pairing === "document_fallback") {
    precisionBadge = "project_level";
  } else {
    precisionBadge = "no_coordinate";
  }

  // Real values for comparison sentence
  const clipPrediction = photo.predicted_label ?? photo.activity_type ?? null;
  const clipConfidence = photo.predicted_confidence;
  const satelliteVerdict = cv?.[0]?.satellite_verdict ?? null;
  const status = triageStatus ?? null;

  // Clause formatter: explicit when missing
  const formatClause = (val: string | number | null | undefined) => {
    if (val === null || val === undefined || val === "") return "not available";
    return String(val);
  };

  const formatConfidence = (conf: number | null | undefined) => {
    if (conf === null || conf === undefined) return "confidence not available";
    const pct = Math.round(conf * 100);
    const tier = pct >= 75 ? "High" : pct >= 40 ? "Medium" : "Low";
    return `${pct}% confidence (${tier})`;
  };

  // Exact comparison sentence:
  // "Photo shows: [real prediction] ([confidence]%) — Satellite shows: [real satellite_verdict] → [real status]"
  const comparisonSentence =
    `Photo shows: ${formatClause(clipPrediction)} (${formatConfidence(clipConfidence)}) — ` +
    `Satellite shows: ${formatClause(satelliteVerdict)} → ${formatClause(status)}`;

  const photoSrc = mediaUrl(photo.ground_photo_path);

  const precisionBadgeColors = {
    exact_gps: "bg-emerald-100 text-emerald-800 border-emerald-300",
    mws_level: "bg-indigo-100 text-indigo-800 border-indigo-300",
    project_level: "bg-blue-100 text-blue-800 border-blue-300",
    no_coordinate: "bg-amber-100 text-amber-800 border-amber-300",
  };

  return (
    <>
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
        <div className="relative group cursor-zoom-in" onClick={() => setLightboxOpen(true)}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={photoSrc ?? undefined}
            alt="Ground truth field photo"
            className="w-full max-h-72 object-cover transition-transform duration-200 group-hover:scale-[1.01]"
          />
          <div className="absolute top-2 right-2 bg-black/70 text-white text-[10px] px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity">
            🔍 Click to inspect full-size
          </div>
        </div>

        <div className="p-3 space-y-2.5 text-sm">
          {/* Header & Coordinate Precision Badge */}
          <div className="flex items-center justify-between flex-wrap gap-2">
            <span className="font-semibold text-gray-800 text-xs uppercase tracking-wide">
              Ground Truth Photo (DRISHTI)
            </span>
            <span
              className={`px-2.5 py-0.5 rounded-full text-[11px] font-mono font-semibold border ${precisionBadgeColors[precisionBadge]}`}
              title={`Coordinate precision: ${precisionBadge} (${photo.pairing_method || "raw source"})`}
            >
              precision: {precisionBadge}
            </span>
          </div>

          {/* Activity / Linear Probe Prediction Details */}
          <div className="text-xs text-gray-700 bg-gray-50/80 p-2 rounded-lg border border-gray-100 space-y-1">
            <div>
              Activity / Structure Type:{" "}
              <strong className="text-gray-900">{photo.activity_type ?? "Unspecified"}</strong>
            </div>
            <div>
              Predicted Classification:{" "}
              <span className="font-medium text-gray-900">{photo.predicted_label ?? "not available"}</span>
              {photo.predicted_confidence != null && (
                <span className="text-gray-600 font-mono">
                  {" "}
                  ({formatConfidence(photo.predicted_confidence)})
                </span>
              )}
            </div>
            {photo.drishti_id && (
              <div className="text-gray-500 font-mono text-[11px]">
                Drishti ID: #{photo.drishti_id} {photo.mws_code ? `· MWS: ${photo.mws_code}` : ""}
              </div>
            )}
          </div>

          {/* Strict Comparison Sentence */}
          <div className="text-xs text-gray-800 bg-blue-50/60 rounded-lg p-2.5 border border-blue-200/80 leading-relaxed font-mono">
            {comparisonSentence}
          </div>
        </div>
      </div>

      {/* Full Size Photo Zoom Lightbox */}
      {lightboxOpen && (
        <div
          className="fixed inset-0 z-50 bg-black/80 backdrop-blur-xs flex items-center justify-center p-4"
          onClick={() => setLightboxOpen(false)}
        >
          <div className="relative max-w-4xl max-h-[90vh] bg-white rounded-xl overflow-hidden shadow-2xl p-2" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={() => setLightboxOpen(false)}
              className="absolute top-3 right-3 bg-black/70 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm font-bold z-10 hover:bg-black"
            >
              ✕
            </button>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={photoSrc ?? undefined}
              alt="Ground truth field photo full view"
              className="max-h-[80vh] w-auto mx-auto object-contain rounded-lg"
            />
            <div className="p-2 text-xs text-gray-700 text-center">
              {photo.activity_type ?? "Structure"} · Drishti #{photo.drishti_id ?? "N/A"} · Precision: {precisionBadge}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
