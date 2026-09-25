"use client";

import { useRef, useState } from "react";
import { api } from "@/lib/api";

export default function UploadModalLauncher() {
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const submit = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.uploadPhoto(file);
      setResult(res);
    } catch (e) {
      setError(String(e));
    } finally {
      setUploading(false);
    }
  };

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="absolute bottom-14 right-4 z-10 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2.5 rounded-full shadow-lg"
      >
        + Upload geotagged photo
      </button>

      {open && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-5">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold text-gray-800">Direct Geotagged Photo Upload</h2>
              <button onClick={() => setOpen(false)} className="text-gray-400 hover:text-gray-600">
                ✕
              </button>
            </div>
            <p className="text-xs text-gray-500 mb-3">
              Drop a smartphone field photo with GPS EXIF data. The backend extracts the
              coordinates, queries live LULC/NDWI/soil/slope, classifies the structure, and plots
              it on the map.
            </p>

            <div
              className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center text-sm text-gray-500 cursor-pointer hover:border-blue-400"
              onClick={() => inputRef.current?.click()}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                const f = e.dataTransfer.files?.[0];
                if (f) setFile(f);
              }}
            >
              {file ? file.name : "Click or drag a photo here"}
              <input
                ref={inputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
            </div>

            {error && <div className="text-red-500 text-xs mt-3">{error}</div>}
            {result && (
              <div className="text-xs bg-green-50 rounded p-3 mt-3 space-y-1">
                <div className="font-medium text-green-800">Asset #{String(result.asset_id)} created</div>
                <div>Predicted structure: {String(result.predicted_structure_label ?? "—")}</div>
                <div>Triage status: {String(result.triage_status)}</div>
                <div>Confidence: {String(result.confidence_level)}</div>
                {typeof result.note === "string" && <div className="text-gray-500 italic">{result.note}</div>}
              </div>
            )}

            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => setOpen(false)} className="text-sm px-3 py-1.5 rounded text-gray-600">
                Close
              </button>
              <button
                onClick={submit}
                disabled={!file || uploading}
                className="text-sm px-4 py-1.5 rounded bg-blue-600 disabled:bg-gray-300 text-white"
              >
                {uploading ? "Processing…" : "Upload"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
