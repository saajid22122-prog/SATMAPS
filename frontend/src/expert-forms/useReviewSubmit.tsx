"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { AssetDetail, SpecialistRole } from "@/lib/types";

/**
 * Shared real submit logic for all 5 role forms (Section 3). Each role file
 * owns its own JSX/questions/data panel; this hook only owns the actual
 * POST /api/reviews call and its state, so the 5 real files aren't each
 * reimplementing the same network/error/corrected-label logic.
 */
export function useReviewSubmit(asset: AssetDetail, role: SpecialistRole, extraFields: Record<string, unknown>) {
  const [reviewerName, setReviewerName] = useState("");
  const [notes, setNotes] = useState("");
  const [answer, setAnswer] = useState<string>("");
  const [correctedLabel, setCorrectedLabel] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (onSubmitted?: () => void) => {
    setSubmitting(true);
    setError(null);
    try {
      await api.submitReview({
        asset_id: asset.id,
        role,
        reviewer_name: reviewerName || undefined,
        responses: { answer, ...extraFields },
        corrected_photo_label: Object.keys(correctedLabel).length ? correctedLabel : undefined,
        notes: notes || undefined,
      });
      setDone(true);
      onSubmitted?.();
    } catch (e) {
      setError(String(e));
    } finally {
      setSubmitting(false);
    }
  };

  return {
    reviewerName, setReviewerName: (v: string) => { setError(null); setReviewerName(v); },
    notes, setNotes: (v: string) => { setError(null); setNotes(v); },
    answer, setAnswer: (v: string) => { setError(null); setAnswer(v); },
    correctedLabel, setCorrectedLabel,
    submitting, done, error, setError,
    submit,
  };
}

export function AnswerButtons({
  options, answer, setAnswer,
}: { options: string[]; answer: string; setAnswer: (v: string) => void }) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((opt) => (
        <button
          key={opt}
          type="button"
          onClick={() => setAnswer(opt)}
          className={`px-3.5 py-1.5 rounded-lg border text-xs font-bold transition-all shadow-xs ${
            answer === opt
              ? "bg-gradient-to-r from-[#7058B6] to-[#5B44A0] text-white border-purple-400 shadow-purple-500/20 ring-2 ring-purple-400/40"
              : "bg-[#1E1938] text-[#DCCFEC] border-[#A997DF]/30 hover:bg-[#28214B] hover:text-white"
          }`}
        >
          {opt}
        </button>
      ))}
    </div>
  );
}

export function ReviewerNameField({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <div>
      <label className="text-xs font-semibold text-[#C3B8DF] block mb-1">Reviewer name (optional)</label>
      <input
        type="text"
        className="bg-[#161226] text-[#F3F0FA] border border-[#A997DF]/30 rounded-lg px-3 py-2 text-xs w-full focus:outline-none focus:border-purple-400 focus:ring-1 focus:ring-purple-400/50 placeholder-[#A997DF]/50"
        placeholder="e.g. Dr. A. Sharma (Senior Hydrologist)"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}

export function NotesField({
  value, onChange, label = "Notes",
}: { value: string; onChange: (v: string) => void; label?: string }) {
  return (
    <div>
      <label className="text-xs font-semibold text-[#C3B8DF] block mb-1">{label}</label>
      <textarea
        className="bg-[#161226] text-[#F3F0FA] border border-[#A997DF]/30 rounded-lg px-3 py-2 text-xs w-full focus:outline-none focus:border-purple-400 focus:ring-1 focus:ring-purple-400/50 placeholder-[#A997DF]/50"
        rows={3}
        placeholder="Enter technical observations, field recommendations, or operational notes..."
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}

export function SubmitButton({
  submitting, disabled, onClick,
}: { submitting: boolean; disabled: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={submitting || disabled}
      className="bg-gradient-to-r from-[#7058B6] to-[#5B44A0] hover:from-[#8168C9] hover:to-[#6C50B3] disabled:from-slate-800 disabled:to-slate-800 disabled:text-slate-500 text-white font-bold text-xs px-5 py-2.5 rounded-lg shadow-md transition-all cursor-pointer border border-purple-400/30"
    >
      {submitting ? "Submitting Review…" : "Submit Official Review"}
    </button>
  );
}

export function DoneBanner() {
  return (
    <div className="text-emerald-300 text-xs font-semibold p-4 bg-emerald-950/70 border border-emerald-500/40 rounded-xl flex items-center gap-2">
      <span className="text-base">✅</span>
      <span>Official specialist review submitted and recorded in database audit ledger. Thank you.</span>
    </div>
  );
}
