"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, mediaUrl } from "@/lib/api";
import type { AssetSummary } from "@/lib/types";

export default function IngestPage() {
  const [assets, setAssets] = useState<AssetSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<string | null>(null);

  useEffect(() => {
    api
      .listAssets()
      .then(setAssets)
      .finally(() => setLoading(false));
  }, []);

  const triggerSyncSimulation = () => {
    setSyncing(true);
    setTimeout(() => {
      api.listAssets().then((res) => {
        setAssets(res);
        setSyncing(false);
      });
    }, 1200);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadMsg(null);
    try {
      const res = await api.uploadPhoto(file);
      setUploadMsg(`Photo uploaded successfully! Extracted GPS EXIF: (${res.latitude ?? "Fallback"}°N, ${res.longitude ?? "Fallback"}°E).`);
      api.listAssets().then(setAssets);
    } catch (err) {
      setUploadMsg(`Upload failed: ${err}`);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      {/* Requirement #8 MUST-HAVE PROMINENT VISIBLE BANNER */}
      <div className="bg-amber-500 text-slate-950 font-bold p-4 rounded-xl border-2 border-amber-600 shadow-md flex items-start gap-3">
        <span className="text-2xl shrink-0">⚠️</span>
        <div>
          <div className="text-sm font-extrabold uppercase tracking-wide">
            PROTOTYPE INTEGRATION NOTICE (PS 26015 Requirement 8)
          </div>
          <p className="text-xs font-semibold mt-0.5 leading-relaxed text-slate-900">
            &ldquo;Prototype integration — live DRISHTI API access not yet available; demo uses static dataset in the expected data structure.&rdquo;
          </p>
        </div>
      </div>

      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[#F3F0FA]">Satmaps Field Ingestion Layer</h1>
          <p className="text-sm text-[#C3B8DF]/80 mt-1">
            Simulated ingestion pipeline reading field assets and ground-truth photographs structured in the official ISRO / Bhuvan schema.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={triggerSyncSimulation}
            disabled={syncing}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg text-sm font-semibold shadow-xs flex items-center gap-2 transition-all"
          >
            {syncing ? (
              <>
                <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                <span>Simulating API Stream Sync…</span>
              </>
            ) : (
              <>
                <span>📡</span>
                <span>Simulate DRISHTI Feed Refresh</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Manual Upload Section */}
      <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-xs space-y-3">
        <h2 className="font-bold text-gray-900 text-sm uppercase tracking-wide">
          Direct Geotagged Field Photo Ingest (GPS EXIF Parsing)
        </h2>
        <div className="flex items-center gap-4 flex-wrap">
          <label className="cursor-pointer px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-800 rounded-lg text-xs font-semibold border border-gray-300 transition-colors inline-flex items-center gap-2">
            <span>📷</span>
            <span>Choose Geotagged Photo File</span>
            <input type="file" accept="image/*" className="hidden" onChange={handleFileUpload} />
          </label>
          {uploading && <span className="text-xs text-blue-600 font-semibold animate-pulse">Processing EXIF metadata &amp; spatial indexing…</span>}
        </div>
        {uploadMsg && <div className="text-xs font-semibold text-emerald-800 bg-emerald-50 border border-emerald-200 p-2.5 rounded-lg">{uploadMsg}</div>}
      </div>

      {/* Dataset Feed Table */}
      <div className="bg-white border border-gray-200 rounded-xl shadow-xs overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
          <h2 className="font-bold text-gray-900 text-sm">
            Ingested Asset Records ({assets.length} items in static schema)
          </h2>
          <span className="text-xs text-gray-500 font-mono">Format: DRISHTI JSON / Geopackage</span>
        </div>

        {loading ? (
          <div className="p-8 text-center text-sm text-gray-400">Loading ingested dataset records…</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-gray-700">
              <thead className="bg-gray-100 text-gray-600 font-semibold uppercase text-[10px] tracking-wider border-b">
                <tr>
                  <th className="py-3 px-4">Project ID</th>
                  <th className="py-3 px-4">District / Locality</th>
                  <th className="py-3 px-4">Intervention Type</th>
                  <th className="py-3 px-4">Coordinates</th>
                  <th className="py-3 px-4">Pairing Precision</th>
                  <th className="py-3 px-4">Triage Status</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {assets.map((asset) => (
                  <tr key={asset.id} className="hover:bg-gray-50/80 transition-colors">
                    <td className="py-3 px-4 font-mono font-bold text-blue-700">{asset.project_id}</td>
                    <td className="py-3 px-4 font-medium">{asset.district}, {asset.state_name}</td>
                    <td className="py-3 px-4 capitalize">{asset.ps_category?.replace(/_/g, " ")}</td>
                    <td className="py-3 px-4 font-mono text-[11px]">{asset.latitude.toFixed(4)}°N, {asset.longitude.toFixed(4)}°E</td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-gray-100 text-gray-700 border">
                        {asset.pairing_method}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-emerald-50 text-emerald-700 border border-emerald-200">
                        {asset.triage_status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Link
                        href={`/assets/${asset.id}`}
                        className="text-xs font-semibold text-blue-600 hover:text-blue-800 underline"
                      >
                        Inspect Asset &rarr;
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
