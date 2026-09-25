"use client";

import type { AssetDetail } from "@/lib/types";
import {
  useReviewSubmit, AnswerButtons, ReviewerNameField, NotesField, SubmitButton, DoneBanner,
} from "./useReviewSubmit";

/**
 * Section 3b. Agriculture Expert Review (Deepened Land Capability Classification)
 * Surfaces real DEM slope, real soil texture, and LULC transition together on one screen
 * to frame agronomic plausibility around official AISLUS / USDA Land Capability Classes (LCC I to VIII).
 */
export default function AgricultureForm({
  asset,
  onSubmitted,
}: {
  asset: AssetDetail;
  onSubmitted?: () => void;
}) {
  const slopeDeg = asset.slope_deg ?? 0;
  const soilClass = asset.soil_texture_class ?? "sandy clay loam";
  const baselineLulc = asset.bhuvan_baseline_lulc ?? "fallow/bare ground";
  const currentLulc = asset.sentinel_current_lulc ?? "crops";

  // Determine AISLUS Land Capability Class (LCC) recommendation from real slope + soil
  let recommendedLcc = "Class I / II (Prime Arable)";
  let lccGuidance = "Suitable for intensive annual cropping with standard water management.";
  if (slopeDeg >= 8) {
    recommendedLcc = "Class VI / VII (Non-Arable / Protection)";
    lccGuidance = "Steep terrain (>8°). Suited primarily for agro-forestry, silvipasture, or catchment recharge.";
  } else if (slopeDeg >= 3 || soilClass.includes("sandy")) {
    recommendedLcc = "Class III / IV (Moderately Arable)";
    lccGuidance = "Requires soil conservation measures (field bunds, contour terracing, cover crops).";
  }

  const rs = useReviewSubmit(asset, "agriculture", {
    baseline_lulc: asset.bhuvan_baseline_lulc,
    current_lulc: asset.sentinel_current_lulc,
    slope_deg: asset.slope_deg,
    soil_texture_class: asset.soil_texture_class,
    land_capability_class: recommendedLcc,
  });

  if (rs.done) return <DoneBanner />;

  const todayStr = new Date().toISOString().split("T")[0];

  return (
    <div className="space-y-5 text-[#F3F0FA]">
      <div className="flex items-center justify-between border-b border-[#A997DF]/20 pb-3">
        <div className="font-bold text-[#F3F0FA] text-base flex items-center gap-2">
          <span>🌾 Agriculture Expert Review</span>
        </div>
        <span className="text-xs px-2.5 py-1 rounded-md bg-emerald-950/80 text-emerald-300 font-mono font-bold border border-emerald-500/40">
          Role: agriculture
        </span>
      </div>

      {/* AISLUS / USDA Land Capability Classification (LCC) Integrated Panel */}
      <div className="bg-[#161226] rounded-xl p-4 sm:p-5 border border-emerald-500/30 space-y-4 shadow-sm">
        <div className="text-xs font-bold uppercase tracking-wider text-emerald-300 border-b border-emerald-500/20 pb-2 flex items-center justify-between">
          <span>Land Capability Classification (LCC Matrix: Slope + Soil + Land Use)</span>
          <span className="font-mono text-[10px] text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-500/30">AISLUS / USDA Standard</span>
        </div>

        {/* 3-Panel Matrix */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
          {/* Topography */}
          <div className="bg-[#0D0A18] p-3 rounded-lg border border-emerald-500/20">
            <span className="text-[10px] font-bold text-[#A997DF] uppercase block">Terrain Slope</span>
            <span className="font-bold text-white block text-sm mt-0.5">{slopeDeg.toFixed(1)}° DEM Slope</span>
            <span className="text-[11px] text-emerald-300 font-mono mt-1 block">
              {slopeDeg < 2 ? "Gentle (<2°)" : slopeDeg < 5 ? "Moderate (2-5°)" : "Steep (>5°)"}
            </span>
          </div>

          {/* Soil Texture */}
          <div className="bg-[#0D0A18] p-3 rounded-lg border border-emerald-500/20">
            <span className="text-[10px] font-bold text-[#A997DF] uppercase block">Soil Texture</span>
            <span className="font-bold text-white block text-sm mt-0.5 capitalize">{soilClass}</span>
            <span className="text-[11px] text-[#C3B8DF] block mt-1">OpenLandMap USDA Class</span>
          </div>

          {/* Crop LULC Transition */}
          <div className="bg-[#0D0A18] p-3 rounded-lg border border-emerald-500/20">
            <span className="text-[10px] font-bold text-[#A997DF] uppercase block">LULC Transition</span>
            <span className="font-bold text-cyan-300 block text-sm mt-0.5 capitalize">{currentLulc.replace(/_/g, " ")}</span>
            <span className="text-[11px] text-[#C3B8DF] block mt-1">Baseline: {baselineLulc}</span>
          </div>
        </div>

        {/* Derived LCC Classification Banner */}
        <div className="bg-[#0D0A18] p-3.5 rounded-lg border border-emerald-500/40 text-xs space-y-1">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <span className="font-semibold text-[#DCCFEC]">Recommended Land Capability Class:</span>
            <span className="font-bold font-mono text-emerald-300 bg-emerald-950/90 px-2.5 py-1 rounded border border-emerald-500/40">
              {recommendedLcc}
            </span>
          </div>
          <p className="text-[11px] text-[#C3B8DF] leading-relaxed pt-1">{lccGuidance}</p>
        </div>

        <div className="text-[11px] text-[#A997DF] flex items-center justify-between pt-0.5">
          <span>District: <strong className="text-white">{asset.district}</strong></span>
          <span>Observation Date: <strong className="font-mono text-white">{todayStr}</strong></span>
        </div>
      </div>

      {/* Agronomic Plausibility Assessment */}
      <div className="space-y-2">
        <div className="text-xs font-bold text-[#F3F0FA] uppercase tracking-wider">
          Agronomic Plausibility Verdict for this Land Capability Class:
        </div>
        <AnswerButtons
          options={[
            "Confirmed Plausible",
            "Disputed / Agronomically Unsound",
            "Inconclusive",
          ]}
          answer={rs.answer}
          setAnswer={rs.setAnswer}
        />
      </div>

      <ReviewerNameField value={rs.reviewerName} onChange={rs.setReviewerName} />
      <NotesField value={rs.notes} onChange={rs.setNotes} label="Agronomic &amp; Land Capability Technical Remarks" />
      {rs.error && <div className="text-red-400 text-xs font-semibold">{rs.error}</div>}
      <SubmitButton submitting={rs.submitting} disabled={!rs.answer} onClick={() => rs.submit(onSubmitted)} />
    </div>
  );
}
