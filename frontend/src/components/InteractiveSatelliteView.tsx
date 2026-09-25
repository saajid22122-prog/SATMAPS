"use client";

import { useEffect, useRef } from "react";
import { maplibregl } from "@/lib/maplibreSetup";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Photo } from "@/lib/types";

interface InteractiveSatelliteViewProps {
  lat: number;
  lon: number;
  structureName?: string;
  groundPhotoUrl?: string | null;
  drishtiId?: string;
  photos?: Photo[];
  selectedPhotoIdx?: number;
  onSelectPhoto?: (idx: number) => void;
}

export default function InteractiveSatelliteView({
  lat,
  lon,
  structureName = "Watershed Structure",
  groundPhotoUrl,
  drishtiId,
  photos = [],
  selectedPhotoIdx = 0,
  onSelectPhoto,
}: InteractiveSatelliteViewProps) {
  // Real check: this dataset has 0 photos (out of 1514, verified against the
  // live DB) with their own lat/lon - every photo at a site falls back to
  // one shared project-level coordinate. The pin never actually "moves" or
  // has other numbered markers to click unless a photo genuinely has its
  // own distinct coordinate, so the on-map copy below must reflect which
  // case is real for this asset, not always claim per-photo movement.
  const otherPhotosWithOwnCoords = photos.filter(
    (p, idx) => idx !== selectedPhotoIdx && p.latitude != null && p.longitude != null
  );
  const hasDistinctMarkers = otherPhotosWithOwnCoords.length > 0;
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const activeMarkerRef = useRef<maplibregl.Marker | null>(null);
  const siteMarkersRef = useRef<maplibregl.Marker[]>([]);

  // 1. Initialize MapLibre GL map once
  useEffect(() => {
    if (!mapContainerRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: {
        version: 8,
        sources: {
          "esri-satellite": {
            type: "raster",
            tiles: [
              "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            ],
            tileSize: 256,
            attribution: "Esri World Imagery",
          },
        },
        layers: [
          {
            id: "satellite-layer",
            type: "raster",
            source: "esri-satellite",
            minzoom: 0,
            maxzoom: 19,
          },
        ],
      },
      center: [lon, lat],
      zoom: 18,
      maxZoom: 19,
      minZoom: 12,
    });

    mapRef.current = map;
    map.addControl(new maplibregl.NavigationControl({ showCompass: true }), "top-right");

    map.on("load", () => {
      // Create active target marker
      const el = document.createElement("div");
      el.className = "flex items-center justify-center pointer-events-auto cursor-pointer";
      el.innerHTML = `
        <div class="relative flex items-center justify-center">
          <div class="absolute w-12 h-12 rounded-full border-2 border-red-500 bg-red-500/20 animate-ping"></div>
          <div class="relative w-7 h-7 rounded-full border-2 border-dashed border-red-500 bg-red-500/30 flex items-center justify-center shadow-lg">
            <div class="w-2.5 h-2.5 rounded-full bg-fuchsia-600 border border-white shadow"></div>
          </div>
        </div>
      `;

      const activeMarker = new maplibregl.Marker({ element: el })
        .setLngLat([lon, lat])
        .addTo(map);

      activeMarkerRef.current = activeMarker;
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 2. Smoothly fly to new coordinates whenever the user switches photos
  useEffect(() => {
    if (!mapRef.current) return;
    mapRef.current.flyTo({
      center: [lon, lat],
      zoom: 18,
      speed: 1.5,
      curve: 1,
      essential: true,
    });

    if (activeMarkerRef.current) {
      activeMarkerRef.current.setLngLat([lon, lat]);
    }
  }, [lat, lon]);

  // 3. Render markers for all photos across the watershed project site
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    // Clear old site markers
    siteMarkersRef.current.forEach((m) => m.remove());
    siteMarkersRef.current = [];

    photos.forEach((p, idx) => {
      const pLat = p.latitude;
      const pLon = p.longitude;
      if (pLat == null || pLon == null) return;
      if (idx === selectedPhotoIdx) return; // Active marker handles the selected one

      const el = document.createElement("div");
      el.className = "flex items-center justify-center cursor-pointer group";
      el.innerHTML = `
        <div class="w-5 h-5 rounded-full bg-blue-600/80 border-2 border-white shadow flex items-center justify-center text-[9px] font-bold text-white hover:scale-125 transition-transform hover:bg-blue-500">
          ${idx + 1}
        </div>
      `;

      el.addEventListener("click", () => {
        if (onSelectPhoto) onSelectPhoto(idx);
      });

      const popup = new maplibregl.Popup({ offset: 15, closeButton: false }).setText(
        `#${idx + 1}: ${p.activity_type ?? "Structure"}`
      );

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([pLon, pLat])
        .setPopup(popup)
        .addTo(map);

      siteMarkersRef.current.push(marker);
    });
  }, [photos, selectedPhotoIdx, onSelectPhoto]);

  return (
    <div className="relative w-full h-[480px] sm:h-[540px] rounded-lg overflow-hidden bg-gray-900 border border-gray-300">
      {/* Interactive Map Canvas */}
      <div ref={mapContainerRef} className="w-full h-full" />

      {/* Top Banner with HUD Telemetry */}
      <div className="absolute top-3 left-3 z-10 bg-black/80 backdrop-blur-md text-white text-xs px-3 py-1.5 rounded-md border border-white/20 font-mono shadow-md flex items-center gap-2.5">
        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
        <span className="font-semibold text-emerald-300">Photo #{selectedPhotoIdx + 1}: {structureName}</span>
        <span className="text-gray-400">·</span>
        <span>{lat.toFixed(5)}°N, {lon.toFixed(5)}°E</span>
        <span className="text-gray-400">·</span>
        <span className="text-emerald-400 font-sans font-medium text-[11px]">
          {hasDistinctMarkers ? "Pin Moves to Selected Structure" : "Shared project-level location (no per-photo GPS in source data)"}
        </span>
      </div>

      {/* Ground Truth Photo Picture-in-Picture Preview */}
      {groundPhotoUrl && (
        <div className="absolute bottom-3 right-3 z-10 bg-black/85 backdrop-blur-md p-2 rounded-lg border border-white/20 shadow-xl max-w-[200px] sm:max-w-[240px]">
          <div className="text-[10px] text-gray-300 font-semibold mb-1 px-1 flex items-center justify-between">
            <span>Ground Truth Photo</span>
            <span className="text-emerald-400 font-mono">#{selectedPhotoIdx + 1}</span>
          </div>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={groundPhotoUrl}
            alt="Ground reference"
            className="w-full h-28 sm:h-32 object-cover rounded border border-white/10"
          />
        </div>
      )}

      {/* Instructions Overlay Bottom Left */}
      <div className="absolute bottom-3 left-3 z-10 bg-black/75 backdrop-blur-xs text-white/90 text-[11px] px-2.5 py-1 rounded border border-white/10 shadow pointer-events-none">
        {hasDistinctMarkers
          ? "Click any numbered marker on the map to switch photos · Use mouse wheel to zoom"
          : "Use the photo gallery below to switch photos · Use mouse wheel to zoom"}
      </div>
    </div>
  );
}
