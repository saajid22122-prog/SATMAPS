"use client";

import type { AssetDetail } from "@/lib/types";
import { useReviewSubmit, AnswerButtons, SubmitButton, DoneBanner } from "./useReviewSubmit";

/**
 * Section 3e. Watershed Committee Member Review (Local Villager)
 * Sees: structure name, village, location pin — deliberately minimal.
 * Can do: simple Yes / No / Needs Repair functional check.
 */
export default function CommitteeForm({
  asset,
  onSubmitted,
}: {
  asset: AssetDetail;
  onSubmitted?: () => void;
}) {
  const rs = useReviewSubmit(asset, "committee_member", {});

  if (rs.done) return <DoneBanner />;

  return (
    <div className="space-y-4 text-[#F3F0FA]">
      <div className="flex items-center justify-between border-b border-[#A997DF]/20 pb-3">
        <div className="font-bold text-[#F3F0FA] text-base">🏛️ Watershed Committee Local Check</div>
        <span className="text-xs px-2.5 py-1 rounded-md bg-emerald-950/80 text-emerald-300 font-mono font-bold border border-emerald-500/40">
          Local Villager Form
        </span>
      </div>

      <div className="text-xs bg-[#161226] rounded-xl p-4 space-y-1.5 border border-[#A997DF]/25 text-[#DCCFEC]">
        <div>Structure Name: <strong className="text-white">{asset.project_id}</strong></div>
        <div>Village: <strong className="text-white">{asset.admin_locality ?? asset.district}</strong></div>
        <div className="text-xs text-[#A997DF] font-mono">
          Location: {asset.latitude.toFixed(5)}°N, {asset.longitude.toFixed(5)}°E
        </div>
      </div>

      <div className="text-xs font-bold text-[#F3F0FA] uppercase tracking-wider">
        Is this structure still in place and working properly?
      </div>
      <AnswerButtons options={["Yes", "No", "Needs Repair"]} answer={rs.answer} setAnswer={rs.setAnswer} />

      {rs.error && <div className="text-red-400 text-xs font-semibold">{rs.error}</div>}
      <SubmitButton submitting={rs.submitting} disabled={!rs.answer} onClick={() => rs.submit(onSubmitted)} />
    </div>
  );
}
