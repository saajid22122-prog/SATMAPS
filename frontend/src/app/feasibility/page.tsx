"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { FeasibilityResponse } from "@/lib/types";

const SOIL_OPTIONS = ["sandy clay loam", "clay loam", "loam", "clay", "silt", "sandy loam"];
const LULC_OPTIONS = [
  "Agriculture, Cropland",
  "Barren / Unculturable / Wastelands, Scrub land",
  "Builtup, Urban",
  "Forest, Deciduous",
  "Forest, Scrub Forest",
  "Agriculture, Fallow",
  "Agriculture, Plantation",
];

export default function FeasibilityPage() {
  const [meta, setMeta] = useState<{ trained_n: number; cross_val_accuracy: number | null; note: string } | null>(null);
  const [slope, setSlope] = useState(3.5);
  const [soil, setSoil] = useState(SOIL_OPTIONS[0]);
  const [lulc, setLulc] = useState(LULC_OPTIONS[0]);
  const [rainfall, setRainfall] = useState(65);
  const [result, setResult] = useState<FeasibilityResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getFeasibilityMeta().then(setMeta).catch((e) => setError(String(e)));
  }, []);

  const predict = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.predictFeasibility({
        slope_deg: slope,
        soil_texture_class: soil,
        baseline_lulc: lulc,
        rainfall_mean_mm: rainfall,
      });
      setResult(res);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6 font-sans">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-[#28214B] via-[#1F193B] to-[#161226] text-[#F3F0FA] rounded-2xl p-6 shadow-xl space-y-2 border border-[#A997DF]/40">
        <div className="flex items-center gap-2 text-[#A997DF] text-xs font-mono uppercase tracking-wider font-bold">
          <span>⚡ ML Feasibility Engine</span>
          <span>•</span>
          <span>Random Forest Classifier</span>
        </div>
        <h1 className="text-2xl font-extrabold tracking-tight lavender-gradient-text">DPR Site Feasibility Simulator</h1>
        <p className="text-sm text-[#DCCFEC] max-w-2xl leading-relaxed">
          Simulate structural water-retention feasibility for proposed watershed intervention sites using a machine-learning model trained on real Copernicus DEM slope, OpenLandMap soil texture, and Landsat RESTREND telemetry.
        </p>

        {meta && (
          <div className="inline-flex items-center gap-2 text-xs bg-[#7058B6]/20 backdrop-blur-md text-[#DCCFEC] rounded-lg px-3 py-1.5 border border-[#A997DF]/30 mt-2 font-mono">
            <span>Model Scope: N={meta.trained_n} live sites</span>
            <span>|</span>
            <span>CV Accuracy: {meta.cross_val_accuracy != null ? `${(meta.cross_val_accuracy * 100).toFixed(1)}%` : "N/A"}</span>
          </div>
        )}
      </div>

      {error && (
        <div className="bg-red-950/80 border border-red-500/40 text-red-200 text-sm p-4 rounded-xl shadow-xs">
          <strong className="text-red-100">Simulation Error:</strong> {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Parameter Sliders Panel */}
        <div className="lg:col-span-7 bg-[#161226] border border-[#A997DF]/30 rounded-2xl p-5 shadow-xl space-y-5 text-[#F3F0FA]">
          <h2 className="text-base font-bold text-[#A997DF] border-b border-[#A997DF]/20 pb-3 flex items-center gap-2">
            <span>🎛️</span>
            <span>Site Parameters</span>
          </h2>

          {/* Slope Slider */}
          <div className="space-y-1.5">
            <div className="flex justify-between items-center text-xs">
              <label className="font-semibold text-[#DCCFEC]" style={{ color: '#DCCFEC' }}>Terrain Slope (DEM)</label>
              <span className="font-mono font-bold text-purple-300 bg-[#28214B] px-2 py-0.5 rounded border border-[#A997DF]/30">{slope.toFixed(1)}°</span>
            </div>
            <input
              type="range"
              min={0}
              max={30}
              step={0.5}
              value={slope}
              onChange={(e) => setSlope(Number(e.target.value))}
              className="w-full h-2 bg-[#28214B] rounded-lg appearance-none cursor-pointer accent-purple-500"
            />
            <div className="flex justify-between text-[10px] text-[#A997DF] font-mono">
              <span>0° (Flat Basin)</span>
              <span>15° (Hilly Slope)</span>
              <span>30° (Steep Ridge)</span>
            </div>
          </div>

          {/* Rainfall Mean Slider */}
          <div className="space-y-1.5">
            <div className="flex justify-between items-center text-xs">
              <label className="font-semibold text-[#DCCFEC]" style={{ color: '#DCCFEC' }}>Mean Monthly Rainfall</label>
              <span className="font-mono font-bold text-purple-300 bg-[#28214B] px-2 py-0.5 rounded border border-[#A997DF]/30">{rainfall} mm/mo</span>
            </div>
            <input
              type="range"
              min={0}
              max={300}
              step={5}
              value={rainfall}
              onChange={(e) => setRainfall(Number(e.target.value))}
              className="w-full h-2 bg-[#28214B] rounded-lg appearance-none cursor-pointer accent-purple-500"
            />
            <div className="flex justify-between text-[10px] text-[#A997DF] font-mono">
              <span>0 mm (Arid)</span>
              <span>150 mm (Monsoon)</span>
              <span>300 mm (High Rain)</span>
            </div>
          </div>

          {/* Soil Select */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-[#DCCFEC] block" style={{ color: '#DCCFEC' }}>Soil Texture Class</label>
            <select
              value={soil}
              onChange={(e) => setSoil(e.target.value)}
              style={{ colorScheme: 'dark', backgroundColor: '#0D0A18', color: '#F3F0FA' }}
              className="w-full border border-[#A997DF]/40 rounded-xl px-3 py-2 text-xs bg-[#0D0A18] font-medium text-[#F3F0FA] focus:outline-none focus:border-purple-400 shadow-inner cursor-pointer"
            >
              {SOIL_OPTIONS.map((o) => (
                <option key={o} value={o} style={{ backgroundColor: '#161226', color: '#F3F0FA' }}>{o}</option>
              ))}
            </select>
          </div>

          {/* LULC Select */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-[#DCCFEC] block" style={{ color: '#DCCFEC' }}>Baseline Land Use / Land Cover</label>
            <select
              value={lulc}
              onChange={(e) => setLulc(e.target.value)}
              style={{ colorScheme: 'dark', backgroundColor: '#0D0A18', color: '#F3F0FA' }}
              className="w-full border border-[#A997DF]/40 rounded-xl px-3 py-2 text-xs bg-[#0D0A18] font-medium text-[#F3F0FA] focus:outline-none focus:border-purple-400 shadow-inner cursor-pointer"
            >
              {LULC_OPTIONS.map((o) => (
                <option key={o} value={o} style={{ backgroundColor: '#161226', color: '#F3F0FA' }}>{o}</option>
              ))}
            </select>
          </div>

          <button
            onClick={predict}
            disabled={loading}
            className="w-full lavender-button font-bold text-sm py-2.5 rounded-xl transition-all flex items-center justify-center gap-2 cursor-pointer"
          >
            {loading ? (
              <span>Computing Simulation…</span>
            ) : (
              <>
                <span>✨ Run Feasibility Simulation</span>
              </>
            )}
          </button>
        </div>

        {/* Prediction Results Panel */}
        <div className="lg:col-span-5 flex flex-col justify-between bg-[#0D0A18] text-[#F3F0FA] border border-[#A997DF]/30 rounded-2xl p-5 shadow-2xl space-y-4">
          <div>
            <h2 className="text-xs font-mono font-bold text-[#A997DF] uppercase tracking-wider border-b border-[#A997DF]/20 pb-2 flex items-center justify-between">
              <span>Simulation Results</span>
              <span className="text-[10px] bg-[#28214B] text-[#DCCFEC] px-2 py-0.5 rounded border border-[#A997DF]/30">Random Forest</span>
            </h2>

            {result ? (
              <div className="space-y-4 pt-3">
                <div className="flex items-center gap-3">
                  <div className={`w-3.5 h-3.5 rounded-full ${result.predicted_class === "functional" ? "bg-emerald-400 shadow-[0_0_12px_rgba(52,211,153,0.8)]" : "bg-amber-400 shadow-[0_0_12px_rgba(251,191,36,0.8)]"}`} />
                  <span className="text-lg font-extrabold tracking-tight text-[#F3F0FA]">
                    {result.predicted_class === "functional" ? "High Feasibility" : "Moderate / Site Review Needed"}
                  </span>
                </div>

                {/* Probability Bar */}
                <div className="space-y-1.5 bg-[#161226] p-3 rounded-xl border border-[#A997DF]/25">
                  <div className="flex justify-between text-xs font-semibold">
                    <span className="text-[#DCCFEC]">Feasibility Probability Score</span>
                    <span className="font-mono text-emerald-400 font-bold">{(result.predicted_probability * 100).toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-[#28214B] rounded-full h-2.5 overflow-hidden">
                    <div
                      className="bg-gradient-to-r from-emerald-500 to-teal-400 h-2.5 rounded-full transition-all duration-500"
                      style={{ width: `${Math.min(100, Math.max(5, result.predicted_probability * 100))}%` }}
                    />
                  </div>
                </div>

                <div className="text-xs text-[#DCCFEC] space-y-2 bg-[#161226]/60 p-3 rounded-xl border border-[#A997DF]/20 leading-relaxed">
                  <div>
                    <strong className="text-[#F3F0FA]">Terrain Alignment:</strong> {slope.toFixed(1)}° DEM slope paired with {soil} soil.
                  </div>
                  <div>
                    <strong className="text-[#F3F0FA]">Hydrological Regime:</strong> {rainfall} mm/month precipitation baseline.
                  </div>
                </div>
              </div>
            ) : (
              <div className="py-12 flex flex-col items-center justify-center text-center text-[#8E82B4] gap-2">
                <span className="text-3xl">📊</span>
                <span className="text-xs text-[#C3B8DF]">Adjust parameters on the left and click &quot;Run Feasibility Simulation&quot;.</span>
              </div>
            )}
          </div>

          <div className="text-[11px] text-[#8E82B4] border-t border-[#A997DF]/20 pt-3 leading-tight">
            Note: Machine learning DPR feasibility predictions supplement physical engineering site inspections.
          </div>
        </div>
      </div>
    </div>
  );
}
