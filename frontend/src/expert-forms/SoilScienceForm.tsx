"use client";

import { mediaUrl } from "@/lib/api";
import type { AssetDetail } from "@/lib/types";
import {
  useReviewSubmit, AnswerButtons, ReviewerNameField, NotesField, SubmitButton, DoneBanner,
} from "./useReviewSubmit";

/**
 * Section 3c. Soil Science Expert Review (Deepened USLE/RUSLE Assessment)
 * Surfaces soil_texture_class, real DEM slope_deg, and real LULC together on one screen
 * to mirror the Universal Soil Loss Equation (USLE: A = R * K * LS * C * P) factors.
 */
export default function SoilScienceForm({
  asset,
  onSubmitted,
}: {
  asset: AssetDetail;
  onSubmitted?: () => void;
}) {
  const photo = asset.photos[0];

  // Derive USLE indicators from real existing DB columns
  const slopeDeg = asset.slope_deg ?? 0;
  const slopePercent = (Math.tan((slopeDeg * Math.PI) / 180) * 100).toFixed(1);
  const soilClass = asset.soil_texture_class ?? "sandy clay loam";
  const currentLulc = asset.sentinel_current_lulc ?? "crops";

  // USLE Factor estimates derived directly from real data
  const lsFactor = slopeDeg < 2 ? "Low (< 0.5)" : slopeDeg < 5 ? "Moderate (0.5 – 1.5)" : "High (> 1.5)";
  const kFactor = soilClass.includes("sandy") ? "Moderate-High (0.28–0.35)" : soilClass.includes("clay") ? "Moderate (0.20–0.28)" : "High (0.35+)";

  const rs = useReviewSubmit(asset, "soil_science", {
    soil_texture_class: asset.soil_texture_class,
    slope_deg: asset.slope_deg,
    current_lulc: asset.sentinel_current_lulc,
    usle_factors: {
      k_factor_estimate: kFactor,
      ls_topographic_factor: lsFactor,
      cover_c_factor: currentLulc,
    },
  });

  if (rs.done) return <DoneBanner />;

  return (
    <div className="space-y-5 text-[#F3F0FA]">
      <div className="flex items-center justify-between border-b border-[#A997DF]/20 pb-3">
        <div className="font-bold text-[#F3F0FA] text-base flex items-center gap-2">
          <span>🏜️ Soil Science Expert Review</span>
        </div>
        <span className="text-xs px-2.5 py-1 rounded-md bg-amber-950/80 text-amber-300 font-mono font-bold border border-amber-500/40">
          Role: soil_science
        </span>
      </div>

      {/* Real Photo */}
      {photo && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={mediaUrl(photo.ground_photo_path) ?? undefined}
          alt="ground photo"
          className="w-full max-h-56 object-contain bg-[#0D0A18] rounded-xl border border-[#A997DF]/25"
        />
      )}

      {/* USLE / RUSLE Combined Multi-Factor Assessment Panel */}
      <div className="bg-[#161226] rounded-xl p-4 sm:p-5 border border-amber-500/30 space-y-4 shadow-sm">
        <div className="text-xs font-bold uppercase tracking-wider text-amber-300 border-b border-amber-500/20 pb-2 flex items-center justify-between">
          <span>USLE / RUSLE Soil Erosion Factors (Combined Multi-Factor Matrix)</span>
          <span className="font-mono text-[10px] text-amber-400 bg-amber-950/60 px-2 py-0.5 rounded border border-amber-500/30">A = R × K × LS × C × P</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
          {/* Soil Erodibility K */}
          <div className="bg-[#0D0A18] p-3 rounded-lg border border-amber-500/20">
            <span className="text-[10px] font-bold text-[#A997DF] uppercase block">Soil Erodibility (K Factor)</span>
            <span className="font-bold text-white block text-sm mt-0.5">{soilClass}</span>
            <span className="text-[11px] text-amber-300 font-mono mt-1 block">Est. K: {kFactor}</span>
          </div>

          {/* Topographic LS Factor */}
          <div className="bg-[#0D0A18] p-3 rounded-lg border border-amber-500/20">
            <span className="text-[10px] font-bold text-[#A997DF] uppercase block">Topography (LS Factor)</span>
            <span className="font-bold text-white block text-sm mt-0.5">{slopeDeg.toFixed(1)}° DEM Slope</span>
            <span className="text-[11px] text-amber-300 font-mono mt-1 block">Incline: {slopePercent}% · LS: {lsFactor}</span>
          </div>

          {/* Cover Management C Factor */}
          <div className="bg-[#0D0A18] p-3 rounded-lg border border-amber-500/20">
            <span className="text-[10px] font-bold text-[#A997DF] uppercase block">Cover-Management (C Factor)</span>
            <span className="font-bold text-white block text-sm mt-0.5 capitalize">{currentLulc.replace(/_/g, " ")}</span>
            <span className="text-[11px] text-[#C3B8DF] block mt-1">Baseline: {asset.bhuvan_baseline_lulc ?? "fallow/bare"}</span>
          </div>
        </div>

        <div className="text-[11px] text-amber-200 bg-amber-950/60 p-3 rounded-lg border border-amber-500/30">
          <strong>Structure Compatibility:</strong> {asset.ps_category?.replace(/_/g, " ") ?? "check dam"} siting evaluated against slope ({slopeDeg.toFixed(1)}°) and {soilClass} foundation texture.
        </div>
      </div>

      {/* Professional Soil Siting & Erosion Verdict */}
      <div className="space-y-2">
        <div className="text-xs font-bold text-[#F3F0FA] uppercase tracking-wider">
          USLE Soil Erosion &amp; Structural Siting Verdict:
        </div>
        <AnswerButtons
          options={[
            "Appropriate / Stable",
            "Erosion Risk Flagged",
            "Siltation Concern Flagged",
            "Unsuitable Soil Fit",
          ]}
          answer={rs.answer}
          setAnswer={rs.setAnswer}
        />
      </div>

      {photo && (
        <div>
          <label className="text-xs font-semibold text-[#C3B8DF] block mb-1">
            Correct structure type classification if mislabeled:
          </label>
          <input
            type="text"
            placeholder={photo.predicted_label ?? photo.activity_type ?? "e.g. check dam"}
            className="bg-[#161226] text-[#F3F0FA] border border-[#A997DF]/30 rounded-lg px-3 py-2 text-xs w-full focus:outline-none focus:border-purple-400 placeholder-[#A997DF]/50"
            onChange={(e) => rs.setCorrectedLabel({ [String(photo.id)]: e.target.value })}
          />
        </div>
      )}

      <ReviewerNameField value={rs.reviewerName} onChange={rs.setReviewerName} />
      <NotesField value={rs.notes} onChange={rs.setNotes} label="Soil Mechanics &amp; USLE Technical Remarks" />
      {rs.error && <div className="text-red-400 text-xs font-semibold">{rs.error}</div>}
      <SubmitButton submitting={rs.submitting} disabled={!rs.answer} onClick={() => rs.submit(onSubmitted)} />
    </div>
  );
}
