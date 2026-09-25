"use client";

import { useRef, useState } from "react";
import type { BoundingBox } from "./ComparisonSlider";

/**
 * Standalone GPS-correction utility, carried over from the old
 * ComparisonSlider (which used to double as both the before/after slider
 * AND this pin-correction tool). The feature spec's new slider is
 * satellite-vs-satellite only, so this real, working feature - click the
 * real Esri tile to correct a photo's stored coordinate - is kept here as
 * its own small, clearly-labeled utility instead of being dropped.
 */
export default function PinpointAdjuster({
  tileSrc,
  bbox,
  lat,
  lon,
  onUpdateCoords,
}: {
  tileSrc: string;
  bbox: BoundingBox;
  lat: number;
  lon: number;
  onUpdateCoords: (lat: number, lon: number) => void;
}) {
  const [open, setOpen] = useState(false);
  const [savedNotice, setSavedNotice] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const pinLeft = Math.min(96, Math.max(4, ((lon - bbox.minLon) / (bbox.maxLon - bbox.minLon)) * 100));
  const pinTop = Math.min(96, Math.max(4, ((bbox.maxLat - lat) / (bbox.maxLat - bbox.minLat)) * 100));

  const handleClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const clickedLon = bbox.minLon + ((e.clientX - rect.left) / rect.width) * (bbox.maxLon - bbox.minLon);
    const clickedLat = bbox.maxLat - ((e.clientY - rect.top) / rect.height) * (bbox.maxLat - bbox.minLat);
    onUpdateCoords(clickedLat, clickedLon);
    setSavedNotice(`Updated pin to ${clickedLat.toFixed(5)}°N, ${clickedLon.toFixed(5)}°E`);
    setTimeout(() => setSavedNotice(null), 3500);
  };

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="text-xs px-2.5 py-1 rounded border bg-gray-50 text-gray-700 border-gray-200 hover:bg-gray-100 font-medium flex items-center gap-1.5"
      >
        <span>🎯</span>
        <span>Correct GPS pin</span>
      </button>
    );
  }

  const [fallbackSrc, setFallbackSrc] = useState<string | null>(null);
  const currentTileSrc = fallbackSrc ?? tileSrc;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-gray-700">Click the real satellite tile to correct this photo&apos;s coordinate</span>
        <button type="button" onClick={() => setOpen(false)} className="text-xs text-gray-500 hover:text-gray-800">
          Close
        </button>
      </div>
      <div
        ref={containerRef}
        onClick={handleClick}
        className="relative w-full aspect-video rounded-lg overflow-hidden border border-amber-300 ring-2 ring-amber-400 cursor-crosshair"
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={currentTileSrc}
          alt="Satellite tile for GPS correction"
          className="absolute inset-0 w-full h-full object-cover"
          onError={() => {
            if (!fallbackSrc) {
              setFallbackSrc(
                `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export?bbox=${bbox.minLon},${bbox.minLat},${bbox.maxLon},${bbox.maxLat}&bboxSR=4326&imageSR=4326&size=800,600&f=image`
              );
            }
          }}
        />
        <div
          className="absolute -translate-x-1/2 -translate-y-full pointer-events-none"
          style={{ left: `${pinLeft}%`, top: `${pinTop}%` }}
        >
          <svg className="w-7 h-7 text-red-600 drop-shadow" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z" />
          </svg>
        </div>
        {savedNotice && (
          <div className="absolute top-2 left-1/2 -translate-x-1/2 bg-emerald-600 text-white text-xs font-semibold px-3 py-1 rounded-full shadow-lg">
            ✓ {savedNotice}
          </div>
        )}
      </div>
    </div>
  );
}
