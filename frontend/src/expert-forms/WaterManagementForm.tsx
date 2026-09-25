"use client";

import { useState } from "react";
import { mediaUrl } from "@/lib/api";
import type { AssetDetail } from "@/lib/types";
import {
  useReviewSubmit, AnswerButtons, ReviewerNameField, NotesField, SubmitButton, DoneBanner,
} from "./useReviewSubmit";

/**
 * Section 3a. Water Management Expert Review (Deepened Professional Assessment)
 * Surfaces real telemetry (NDWI, photo, structure type) and replaces single button
 * with a structured 5-part engineering checklist:
 * 1. Embankment condition
 * 2. Spillway/outlet obstruction
 * 3. Visible seepage
 * 4. Reservoir sedimentation/debris
 * 5. Downstream erosion
 */
export default function WaterManagementForm({
  asset,
  onSubmitted,
}: {
  asset: AssetDetail;
  onSubmitted?: () => void;
}) {
  const photo = asset.photos[0];

  // Checklist state
  const [embankment, setEmbankment] = useState("Sound / Intact");
  const [spillway, setSpillway] = useState("Clear / Fully Functional");
  const [seepage, setSeepage] = useState("None / Dry Toe");
  const [sedimentation, setSedimentation] = useState("Minimal (<10% capacity loss)");
  const [erosion, setErosion] = useState("Stable / Protected Bed");

  const rs = useReviewSubmit(asset, "water_management", {
    sentinel_ndwi: asset.sentinel_ndwi,
    checklist: {
      embankment_condition: embankment,
      spillway_obstruction: spillway,
      visible_seepage: seepage,
      reservoir_sedimentation: sedimentation,
      downstream_erosion: erosion,
    },
  });

  if (rs.done) return <DoneBanner />;

  return (
    <div className="space-y-5 text-[#F3F0FA]">
      <div className="flex items-center justify-between border-b border-[#A997DF]/20 pb-3">
        <div className="font-bold text-[#F3F0FA] text-base flex items-center gap-2">
          <span>💧 Water Management Expert Review</span>
        </div>
        <span className="text-xs px-2.5 py-1 rounded-md bg-[#7058B6]/30 text-[#DCCFEC] font-mono font-bold border border-[#A997DF]/30">
          Role: water_management
        </span>
      </div>

      {/* Real Telemetry Panel */}
      <div className="text-sm bg-[#161226] rounded-xl p-4 space-y-3 border border-[#A997DF]/25 shadow-sm">
        {photo && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={mediaUrl(photo.ground_photo_path) ?? undefined}
            alt="ground photo"
            className="w-full max-h-60 object-contain bg-[#0D0A18] rounded-lg border border-[#A997DF]/20"
          />
        )}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-[#DCCFEC] pt-1">
          <div>Structure Category: <strong className="text-white">{photo?.activity_type ?? asset.ps_category ?? "—"}</strong></div>
          <div>Sentinel-2 NDWI Reading: <strong className="font-mono text-cyan-300">{asset.sentinel_ndwi != null ? asset.sentinel_ndwi.toFixed(4) : "—"}</strong></div>
          <div className="col-span-2 text-[#A997DF]/80">
            Sanction / Build date: <em>Not recorded in source IWMP PDF extracts (anchored to Sentinel-2 baseline)</em>
          </div>
        </div>
        {asset.disagreement_type === "water_signal_mismatch" && (
          <div className="text-xs bg-amber-950/70 text-amber-200 p-3 rounded-lg border border-amber-500/40 font-medium">
            <strong>Cross-Validation Flag:</strong> CLIP photo-condition ({photo?.predicted_condition ?? "—"}) does not match satellite water presence.
          </div>
        )}
      </div>

      {/* Structured Engineering Assessment Checklist */}
      <div className="space-y-4 bg-[#1A152E] p-4 sm:p-5 rounded-xl border border-[#A997DF]/30 shadow-inner">
        <div className="text-xs font-bold uppercase tracking-wider text-[#A997DF] border-b border-[#A997DF]/25 pb-2">
          Engineering &amp; Hydraulic Assessment Checklist
        </div>

        {/* 1. Embankment Condition */}
        <div>
          <label className="text-xs font-semibold text-[#DCCFEC] block mb-1.5">
            1. Embankment / Bund Condition:
          </label>
          <select
            value={embankment}
            onChange={(e) => setEmbankment(e.target.value)}
            className="w-full border border-[#A997DF]/30 rounded-lg px-3 py-2 text-xs bg-[#161226] text-[#F3F0FA] font-medium focus:border-purple-400 focus:outline-none"
          >
            <option value="Sound / Intact">Sound / Intact (No visible structural distress)</option>
            <option value="Minor Surface Cracks">Minor Surface Cracks / Superficial Erosion</option>
            <option value="Settlement / Sloughing">Settlement / Sloughing / Crest Depression</option>
            <option value="Overgrown Vegetation / Burrowing">Overgrown Vegetation / Animal Burrowing Hazard</option>
          </select>
        </div>

        {/* 2. Spillway Obstruction */}
        <div>
          <label className="text-xs font-semibold text-[#DCCFEC] block mb-1.5">
            2. Spillway &amp; Waste Weir Outlet:
          </label>
          <select
            value={spillway}
            onChange={(e) => setSpillway(e.target.value)}
            className="w-full border border-[#A997DF]/30 rounded-lg px-3 py-2 text-xs bg-[#161226] text-[#F3F0FA] font-medium focus:border-purple-400 focus:outline-none"
          >
            <option value="Clear / Fully Functional">Clear / Fully Functional (Unobstructed discharge)</option>
            <option value="Partially Silted / Debris Obstruction">Partially Silted / Minor Debris Obstruction</option>
            <option value="Severely Blocked / Flow Restriction">Severely Blocked / Heavy Silt / Flow Restriction</option>
          </select>
        </div>

        {/* 3. Visible Seepage */}
        <div>
          <label className="text-xs font-semibold text-[#DCCFEC] block mb-1.5">
            3. Visible Seepage / Piping Risk:
          </label>
          <select
            value={seepage}
            onChange={(e) => setSeepage(e.target.value)}
            className="w-full border border-[#A997DF]/30 rounded-lg px-3 py-2 text-xs bg-[#161226] text-[#F3F0FA] font-medium focus:border-purple-400 focus:outline-none"
          >
            <option value="None / Dry Toe">None / Dry Toe (No seepage signature)</option>
            <option value="Dampness / Minor Wet Spot">Dampness / Minor Wet Spot at downstream toe</option>
            <option value="Active Seepage / Piping Risk">Active Seepage / Boiling / Piping Risk</option>
          </select>
        </div>

        {/* 4. Reservoir Sedimentation */}
        <div>
          <label className="text-xs font-semibold text-[#DCCFEC] block mb-1.5">
            4. Reservoir Sedimentation &amp; Siltation Level:
          </label>
          <select
            value={sedimentation}
            onChange={(e) => setSedimentation(e.target.value)}
            className="w-full border border-[#A997DF]/30 rounded-lg px-3 py-2 text-xs bg-[#161226] text-[#F3F0FA] font-medium focus:border-purple-400 focus:outline-none"
          >
            <option value="Minimal (<10% capacity loss)">Minimal (&lt;10% capacity loss)</option>
            <option value="Moderate (10-40% capacity loss)">Moderate (10–40% storage capacity loss)</option>
            <option value="Severe (>40% capacity loss)">Severe (&gt;40% capacity loss / Silt Surcharged)</option>
          </select>
        </div>

        {/* 5. Downstream Channel Erosion */}
        <div>
          <label className="text-xs font-semibold text-[#DCCFEC] block mb-1.5">
            5. Downstream Channel &amp; Apron Scouring:
          </label>
          <select
            value={erosion}
            onChange={(e) => setErosion(e.target.value)}
            className="w-full border border-[#A997DF]/30 rounded-lg px-3 py-2 text-xs bg-[#161226] text-[#F3F0FA] font-medium focus:border-purple-400 focus:outline-none"
          >
            <option value="Stable / Protected Bed">Stable / Protected Bed &amp; Energy Dissipator</option>
            <option value="Moderate Scouring">Moderate Downstream Scouring / Apron Undermining</option>
            <option value="Severe Gully Head-cutting">Severe Gully Head-cutting / Active Channel Retrogression</option>
          </select>
        </div>
      </div>

      {/* Final Overall Operational Verdict */}
      <div className="space-y-2">
        <div className="text-xs font-bold text-[#F3F0FA] uppercase tracking-wider">
          OVERALL STRUCTURE OPERATIONAL VERDICT (OVERRIDES AUTOMATED TRIAGE STATUS):
        </div>
        <AnswerButtons
          options={["Functional", "Requires Maintenance", "Breached / Compromised", "Inconclusive"]}
          answer={rs.answer}
          setAnswer={rs.setAnswer}
        />
      </div>

      {photo && (
        <div>
          <label className="text-xs font-semibold text-[#C3B8DF] block mb-1">
            Correct structure type classification (feeds active-learning classifier):
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
      <NotesField value={rs.notes} onChange={rs.setNotes} label="Engineering Technical Notes & Recommendations" />
      {rs.error && <div className="text-red-400 text-xs font-semibold">{rs.error}</div>}
      <SubmitButton submitting={rs.submitting} disabled={!rs.answer} onClick={() => rs.submit(onSubmitted)} />
    </div>
  );
}
