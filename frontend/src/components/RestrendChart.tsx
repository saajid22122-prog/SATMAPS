"use client";

import { useEffect, useState } from "react";
import {
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "@/lib/api";
import type { RestrendSeries } from "@/lib/types";

export default function RestrendChart({ assetId }: { assetId: number }) {
  const [series, setSeries] = useState<RestrendSeries | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getRestrend(assetId)
      .then(setSeries)
      .catch((e) => setError(String(e)));
  }, [assetId]);

  if (error) return <div className="text-sm text-red-500">{error}</div>;
  if (!series) return <div className="text-sm text-gray-400">Loading RESTREND series…</div>;

  if (series.points.length === 0) {
    return (
      <div className="text-sm text-gray-500 italic">
        No RESTREND history available yet for this site (recently ingested, or a coastal/no-data
        pixel where the precipitation record has no coverage).
      </div>
    );
  }

  const data = series.points.map((p) => ({
    label: `${p.year}-${String(p.month).padStart(2, "0")}`,
    ndvi_observed: p.ndvi_observed,
    ndvi_modeled: p.ndvi_modeled,
    residual: p.residual,
    precipitation_mm: p.precipitation_mm,
  }));

  const significant = series.restrend_pvalue != null && series.restrend_pvalue < 0.1;

  return (
    <div>
      <div className="mb-2 text-sm">
        <span className="font-semibold">RESTREND Residual Trend Analysis</span>{" "}
        <span className="text-gray-500">(Decoupled Precipitation Signal)</span>
        <div className="text-xs text-gray-500 mt-1">
          Residual slope: {series.restrend_slope?.toFixed(6) ?? "—"} · p-value:{" "}
          {series.restrend_pvalue?.toFixed(4) ?? "—"} ({significant ? "significant" : "not significant"}
          ) · 12-mo rainfall anomaly: {series.rainfall_anomaly?.toFixed(1) ?? "—"} mm
        </div>
      </div>
      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
          <XAxis dataKey="label" tick={{ fontSize: 10 }} interval={11} />
          <YAxis yAxisId="ndvi" tick={{ fontSize: 10 }} />
          <YAxis yAxisId="precip" orientation="right" tick={{ fontSize: 10 }} />
          <Tooltip />
          <Legend />
          <Line yAxisId="ndvi" type="monotone" dataKey="ndvi_observed" stroke="#16a34a" dot={false} name="NDVI observed" />
          <Line yAxisId="ndvi" type="monotone" dataKey="ndvi_modeled" stroke="#9ca3af" strokeDasharray="4 3" dot={false} name="NDVI modeled (rainfall-only)" />
          <Line yAxisId="ndvi" type="monotone" dataKey="residual" stroke="#2563eb" dot={false} name="Residual" />
          <Line yAxisId="precip" type="monotone" dataKey="precipitation_mm" stroke="#93c5fd" dot={false} name="Precipitation (mm)" strokeWidth={1} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
