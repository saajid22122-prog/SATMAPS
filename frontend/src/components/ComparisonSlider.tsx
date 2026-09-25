"use client";

import { useRef, useState, useEffect } from "react";
import type { Photo } from "@/lib/types";

export interface BoundingBox {
  minLon: number;
  minLat: number;
  maxLon: number;
  maxLat: number;
}

interface ComparisonSliderProps {
  beforeSrc: string;
  afterSrc: string;
  beforeLabel?: string;
  afterLabel?: string;
  targetCoords?: { lat: number; lon: number } | null;
  structureName?: string | null;
  drishtiId?: string | null;
  mwsCode?: string | null;
  bbox?: BoundingBox | null;
  photos?: Photo[];
  selectedPhotoIdx?: number;
  onSelectPhoto?: (idx: number) => void;
  onUpdateCoords?: (lat: number, lon: number) => void;
}

export default function ComparisonSlider({
  beforeSrc,
  afterSrc,
  beforeLabel = "Satellite Imagery",
  afterLabel = "Ground Truth Photo",
  targetCoords,
  structureName: _structureName,
  drishtiId,
  mwsCode: _mwsCode,
  bbox,
  photos = [],
  selectedPhotoIdx = 0,
  onSelectPhoto,
  onUpdateCoords,
}: ComparisonSliderProps) {
  const [pct, setPct] = useState(50);
  const isPdfCrop = beforeSrc.includes("satellite_images") || beforeSrc.includes("_t1");
  const [showMarker, setShowMarker] = useState(!isPdfCrop);
  const [pinpointMode, setPinpointMode] = useState(false);
  const [pinpointSavedNotice, setPinpointSavedNotice] = useState<string | null>(null);

  const containerRef = useRef<HTMLDivElement | null>(null);
  const dragging = useRef(false);
  const [containerWidth, setContainerWidth] = useState<number>(800);
  const [fallbackSrc, setFallbackSrc] = useState<string | null>(null);
  const imgSrc = fallbackSrc ?? beforeSrc;

  useEffect(() => {
    const updateSize = () => {
      if (containerRef.current) {
        setContainerWidth(containerRef.current.clientWidth);
      }
    };
    updateSize();
    window.addEventListener("resize", updateSize);
    return () => window.removeEventListener("resize", updateSize);
  }, []);

  const updateFromClientX = (clientX: number) => {
    const el = containerRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const ratio = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
    setPct(ratio * 100);
  };

  const lat = targetCoords?.lat;
  const lon = targetCoords?.lon;

  // Calculate dynamic pixel percentage of the target pin inside the satellite bounding box
  const pinLeft =
    bbox && lon != null
      ? Math.min(96, Math.max(4, ((lon - bbox.minLon) / (bbox.maxLon - bbox.minLon)) * 100))
      : 50;

  const pinTop =
    bbox && lat != null
      ? Math.min(96, Math.max(4, ((bbox.maxLat - lat) / (bbox.maxLat - bbox.minLat)) * 100))
      : 50;

  const handleSatelliteClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!pinpointMode || !bbox || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    const clickedLon = bbox.minLon + (clickX / rect.width) * (bbox.maxLon - bbox.minLon);
    const clickedLat = bbox.maxLat - (clickY / rect.height) * (bbox.maxLat - bbox.minLat);

    if (onUpdateCoords) {
      onUpdateCoords(clickedLat, clickedLon);
      setPinpointSavedNotice(`Updated pin to ${clickedLat.toFixed(5)}°N, ${clickedLon.toFixed(5)}°E`);
      setTimeout(() => setPinpointSavedNotice(null), 3500);
    }
  };

  return (
    <div className="space-y-2">
      <div
        ref={containerRef}
        className={`relative w-full aspect-video select-none overflow-hidden rounded-xl bg-gray-900 shadow-md border border-gray-200 ${
          pinpointMode ? "cursor-crosshair ring-2 ring-amber-400" : ""
        }`}
        onMouseDown={(e) => {
          if (pinpointMode) {
            handleSatelliteClick(e);
            return;
          }
          dragging.current = true;
          updateFromClientX(e.clientX);
        }}
        onMouseMove={(e) => {
          if (!pinpointMode && dragging.current) updateFromClientX(e.clientX);
        }}
        onMouseUp={() => (dragging.current = false)}
        onMouseLeave={() => (dragging.current = false)}
        onTouchStart={(e) => {
          if (!pinpointMode) updateFromClientX(e.touches[0].clientX);
        }}
        onTouchMove={(e) => {
          if (!pinpointMode) updateFromClientX(e.touches[0].clientX);
        }}
      >
        {/* RIGHT LAYER: Ground Truth Field Photo */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={afterSrc}
          alt={afterLabel}
          className="absolute inset-0 w-full h-full object-cover"
        />

        {/* LEFT LAYER: Satellite Image with Dynamic Moving Pin Overlay */}
        <div
          className="absolute inset-0 overflow-hidden"
          style={{ width: `${pct}%` }}
        >
          {/* Base Satellite Tile */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={imgSrc}
            alt={beforeLabel}
            className="absolute inset-0 h-full object-cover"
            style={{ width: containerWidth }}
            onError={() => {
              if (!fallbackSrc) {
                const targetLat = lat ?? 14.65;
                const targetLon = lon ?? 77.60;
                setFallbackSrc(
                  `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export?bbox=${targetLon - 0.0035},${targetLat - 0.0035},${targetLon + 0.0035},${targetLat + 0.0035}&bboxSR=4326&imageSR=4326&size=800,600&f=image`
                );
              }
            }}
          />

          {/* SATELLITE PINS & ANNOTATIONS LAYER */}
          {showMarker && (
            <div
              className="absolute inset-0 pointer-events-none"
              style={{ width: containerWidth }}
            >
              {/* Site Photos Markers (for context across the project area) */}
              {bbox &&
                photos.map((p, idx) => {
                  if (idx === selectedPhotoIdx) return null;
                  if (p.latitude == null || p.longitude == null) return null;
                  const pLeft = ((p.longitude - bbox.minLon) / (bbox.maxLon - bbox.minLon)) * 100;
                  const pTop = ((bbox.maxLat - p.latitude) / (bbox.maxLat - bbox.minLat)) * 100;
                  if (pLeft < 2 || pLeft > 98 || pTop < 2 || pTop > 98) return null;

                  return (
                    <button
                      key={p.id}
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (onSelectPhoto) onSelectPhoto(idx);
                      }}
                      className="absolute -translate-x-1/2 -translate-y-1/2 w-6 h-6 rounded-full bg-blue-600/90 hover:bg-blue-500 text-white font-bold text-[10px] flex items-center justify-center border-2 border-white shadow-md hover:scale-125 transition-transform pointer-events-auto cursor-pointer"
                      style={{ left: `${pLeft}%`, top: `${pTop}%` }}
                      title={`Photo #${idx + 1}: ${p.activity_type ?? "Structure"}`}
                    >
                      {idx + 1}
                    </button>
                  );
                })}

              {/* Dynamic Active Pin: Smoothly Moves Across Screen to Exact Photo Coordinates */}
              <div
                className="absolute -translate-x-1/2 -translate-y-full flex flex-col items-center transition-all duration-300 pointer-events-none z-10"
                style={{ left: `${pinLeft}%`, top: `${pinTop}%` }}
              >
                {/* Visual Location Target Marker */}
                <div className="relative flex flex-col items-center">
                  <div className="w-8 h-8 flex items-center justify-center text-red-600 drop-shadow-md">
                    <svg className="w-8 h-8 filter drop-shadow" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z" />
                    </svg>
                  </div>
                  {/* Pin Tip Anchor Dot */}
                  <div className="w-2 h-2 rounded-full bg-red-600 ring-2 ring-white shadow-xs -mt-1" />
                </div>
              </div>

              {/* Clean Telemetry Tag (Bottom Left) */}
              {lat != null && lon != null && (
                <div className="absolute bottom-2.5 left-2.5 bg-black/80 backdrop-blur-md text-white text-[11px] px-2.5 py-1.5 rounded-md border border-white/15 font-mono flex items-center gap-2 shadow-lg">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  <span>
                    {lat.toFixed(5)}°N, {lon.toFixed(5)}°E
                  </span>
                  {drishtiId && <span className="text-gray-400">· #{drishtiId}</span>}
                  <span className="text-emerald-300 font-sans font-medium text-[10px] ml-1">
                    Photo #{selectedPhotoIdx + 1}
                  </span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Draggable Divider Handle */}
        <div
          className="absolute top-0 bottom-0 w-0.5 bg-white shadow-md cursor-ew-resize z-20"
          style={{ left: `${pct}%` }}
        >
          <div className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-7 h-7 bg-white rounded-full shadow-lg flex items-center justify-center text-xs text-gray-700 font-bold border border-gray-300">
            ↔
          </div>
        </div>

        {/* Header Badges */}
        <div className="absolute top-2.5 left-2.5 bg-black/60 backdrop-blur-xs text-white text-xs px-2.5 py-0.5 rounded z-20">
          {beforeLabel}
        </div>
        <div className="absolute top-2.5 right-2.5 bg-black/60 backdrop-blur-xs text-white text-xs px-2.5 py-0.5 rounded z-20">
          {afterLabel}
        </div>

        {/* Pinpoint Mode Banner */}
        {pinpointMode && (
          <div className="absolute top-2.5 left-1/2 -translate-x-1/2 bg-amber-500/95 backdrop-blur-md text-white text-xs font-semibold px-3 py-1 rounded-full shadow-lg z-30 animate-pulse flex items-center gap-1.5">
            <span>🎯</span>
            <span>Click directly on the satellite structure to pinpoint location</span>
          </div>
        )}

        {/* Pinpoint Saved Notice Toast */}
        {pinpointSavedNotice && (
          <div className="absolute top-11 left-1/2 -translate-x-1/2 bg-emerald-600 text-white text-xs font-semibold px-3 py-1 rounded-full shadow-lg z-30 flex items-center gap-1.5 animate-fade-in">
            <span>✓</span>
            <span>{pinpointSavedNotice}</span>
          </div>
        )}
      </div>

      {/* Clean Controls Toolbar */}
      <div className="flex items-center justify-between text-xs text-gray-600 px-1 flex-wrap gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <button
            type="button"
            onClick={() => setShowMarker(!showMarker)}
            className={`px-2.5 py-1 rounded border transition-colors font-medium flex items-center gap-1.5 ${
              showMarker
                ? "bg-red-50 text-red-700 border-red-200 shadow-2xs"
                : "bg-gray-50 text-gray-600 border-gray-200 hover:bg-gray-100"
            }`}
          >
            <span>📍</span>
            <span>{showMarker ? "GPS Pin: Visible" : "GPS Pin: Hidden"}</span>
          </button>

          {onUpdateCoords && (
            <button
              type="button"
              onClick={() => setPinpointMode(!pinpointMode)}
              className={`px-2.5 py-1 rounded border transition-colors font-medium flex items-center gap-1.5 ${
                pinpointMode
                  ? "bg-amber-100 text-amber-900 border-amber-300 ring-2 ring-amber-400"
                  : "bg-gray-50 text-gray-700 border-gray-200 hover:bg-gray-100"
              }`}
            >
              <span>🎯</span>
              <span>{pinpointMode ? "Pinpoint Active (Click Map)" : "Adjust Pinpoint"}</span>
            </button>
          )}

          <span className="text-gray-400">·</span>
          <span className="text-gray-500">
            {pinpointMode
              ? "Click anywhere on the satellite image to set the exact coordinate for this photo."
              : "Drag ↔ handle to swipe between satellite view and ground photo."}
          </span>
        </div>
      </div>
    </div>
  );
}
