"use client";

import { useState } from "react";
import type { AssetDetail } from "@/lib/types";
import {
  useReviewSubmit, AnswerButtons, ReviewerNameField, NotesField, SubmitButton, DoneBanner,
} from "./useReviewSubmit";

/**
 * Section 3d. Social Mobilization Expert Review (Deepened WDT Process Stage Assessment)
 * Surfaces project ID, district, village locality, and replaces generic engagement buttons
 * with structured WDT (Watershed Development Team) institutional process stage evaluation.
 * HARD RULE: never auto-generate a Watershed Committee name or community detail.
 */
export default function SocialMobilizationForm({
  asset,
  onSubmitted,
}: {
  asset: AssetDetail;
  onSubmitted?: () => void;
}) {
  const [wdtStage, setWdtStage] = useState("Stage 2: Watershed Committee Formed & Registered");

  const rs = useReviewSubmit(asset, "social_mobilization", {
    wdt_process_stage: wdtStage,
  });

  if (rs.done) return <DoneBanner />;

  return (
    <div className="space-y-5 text-[#F3F0FA]">
      <div className="flex items-center justify-between border-b border-[#A997DF]/20 pb-3">
        <div className="font-bold text-[#F3F0FA] text-base flex items-center gap-2">
          <span>👥 Social Mobilization Expert Review</span>
        </div>
        <span className="text-xs px-2.5 py-1 rounded-md bg-purple-950/80 text-purple-300 font-mono font-bold border border-purple-500/40">
          Role: social_mobilization
        </span>
      </div>

      {/* Project & Administrative Context Panel */}
      <div className="text-xs bg-[#161226] rounded-xl p-4 space-y-2 border border-[#A997DF]/25 shadow-sm">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[#DCCFEC]">
          <div>Project ID: <strong className="font-mono text-purple-300">{asset.project_id}</strong></div>
          <div>District: <strong className="text-white">{asset.district}</strong></div>
          <div className="col-span-2">
            Village / Locality (Reverse-Geocoded): <strong className="text-white">{asset.admin_locality ?? "—"}</strong>
          </div>
        </div>
      </div>

      {/* WDT (Watershed Development Team) Staged Process Assessment */}
      <div className="space-y-4 bg-[#1A152E] p-4 sm:p-5 rounded-xl border border-[#A997DF]/30 shadow-inner">
        <div className="text-xs font-bold uppercase tracking-wider text-[#A997DF] border-b border-[#A997DF]/25 pb-2 flex items-center justify-between">
          <span>WDT Institutional Process Stage (Official Guidelines Baseline)</span>
          <span className="font-mono text-[10px] text-[#DCCFEC] bg-[#28214B] px-2 py-0.5 rounded border border-[#A997DF]/30">WDPM / IWMP Guidelines</span>
        </div>

        <div>
          <label className="text-xs font-semibold text-[#DCCFEC] block mb-1.5">
            Current WDT Institutional Lifecycle Stage:
          </label>
          <select
            value={wdtStage}
            onChange={(e) => setWdtStage(e.target.value)}
            className="w-full border border-[#A997DF]/30 rounded-lg px-3 py-2 text-xs bg-[#161226] text-[#F3F0FA] font-medium focus:border-purple-400 focus:outline-none"
          >
            <option value="Stage 1: Initial Entry / PRA Completed">
              Stage 1: Initial Entry / PRA (Participatory Rural Appraisal) & Net Planning Completed
            </option>
            <option value="Stage 2: Watershed Committee Formed & Registered">
              Stage 2: Watershed Committee (WC) Formed & Bank Account Registered
            </option>
            <option value="Stage 3: User Groups / SHGs Active & Executing Works">
              Stage 3: User Groups (UGs) & SHGs Active in Implementation & Asset Construction
            </option>
            <option value="Stage 4: Post-Project O&M Handover Active">
              Stage 4: Post-Project Operation & Maintenance (O&M) & Watershed Development Fund (WDF) Active
            </option>
          </select>
        </div>
      </div>

      {/* Community Stewardship Level Assessment */}
      <div className="space-y-2">
        <div className="text-xs font-bold text-[#F3F0FA] uppercase tracking-wider">
          Community Stewardship &amp; Ownership Assessment:
        </div>
        <AnswerButtons
          options={[
            "Active Stewardship",
            "Partial / Inactive Committee",
            "Disengaged / Neglected",
            "Uncertain",
          ]}
          answer={rs.answer}
          setAnswer={rs.setAnswer}
        />
      </div>

      <ReviewerNameField value={rs.reviewerName} onChange={rs.setReviewerName} />
      <NotesField
        value={rs.notes}
        onChange={rs.setNotes}
        label="Community &amp; Watershed Committee Field Notes (blank free-text, no auto-generated names)"
      />
      {rs.error && <div className="text-red-400 text-xs font-semibold">{rs.error}</div>}
      <SubmitButton submitting={rs.submitting} disabled={!rs.answer} onClick={() => rs.submit(onSubmitted)} />
    </div>
  );
}
