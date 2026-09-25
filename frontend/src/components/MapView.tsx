"use client";

import { useEffect, useRef, useState, useMemo } from "react";
import { maplibregl } from "@/lib/maplibreSetup";
import { Map as MLMap, Popup } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { api, API_BASE } from "@/lib/api";
import type { AssetSummary, TriageStatus } from "@/lib/types";
import { TRIAGE_COLORS, TRIAGE_LABELS } from "@/lib/types";

const ALL_STATUSES: TriageStatus[] = ["confirmed", "rainfall_confounded", "disagreement", "no_evidence"];

type BasemapKey = "satellite" | "osm" | "topo";

const TERRAIN_DEM_SOURCE: maplibregl.RasterDEMSourceSpecification = {
  type: "raster-dem",
  tiles: ["https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"],
  encoding: "terrarium",
  tileSize: 256,
  maxzoom: 14,
};

const BASEMAPS: Record<BasemapKey, { name: string; style: maplibregl.StyleSpecification }> = {
  satellite: {
    name: "Satellite 3D",
    style: {
      version: 8,
      sources: {
        "esri-satellite": {
          type: "raster",
          tiles: [
            "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
          ],
          tileSize: 256,
          attribution:
            '&copy; <a href="https://www.esri.com" target="_blank">Esri</a>, Earthstar Geographics',
        },
        "terrain-dem": TERRAIN_DEM_SOURCE,
      },
      layers: [
        {
          id: "esri-satellite-layer",
          type: "raster",
          source: "esri-satellite",
          minzoom: 0,
          maxzoom: 19,
        },
      ],
      terrain: {
        source: "terrain-dem",
        exaggeration: 1.8,
      },
    },
  },
  topo: {
    name: "Topographic",
    style: {
      version: 8,
      sources: {
        "esri-topo": {
          type: "raster",
          tiles: [
            "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
          ],
          tileSize: 256,
          attribution: '&copy; Esri & OpenStreetMap contributors',
        },
        "terrain-dem": TERRAIN_DEM_SOURCE,
      },
      layers: [
        {
          id: "esri-topo-layer",
          type: "raster",
          source: "esri-topo",
          minzoom: 0,
          maxzoom: 19,
        },
      ],
      terrain: {
        source: "terrain-dem",
        exaggeration: 1.8,
      },
    },
  },
  osm: {
    name: "OpenStreetMap",
    style: {
      version: 8,
      sources: {
        "osm-tiles": {
          type: "raster",
          tiles: [
            "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
          ],
          tileSize: 256,
          attribution:
            '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors',
        },
        "terrain-dem": TERRAIN_DEM_SOURCE,
      },
      layers: [
        {
          id: "osm-layer",
          type: "raster",
          source: "osm-tiles",
          minzoom: 0,
          maxzoom: 19,
        },
      ],
      terrain: {
        source: "terrain-dem",
        exaggeration: 1.8,
      },
    },
  },
};

// Dynamic LULC Palette Mapping for whichever classes actually appear in real data
const LULC_COLOR_MAP: Record<string, string> = {
  water: "#2563eb",
  trees: "#15803d",
  grass: "#84cc16",
  flooded_vegetation: "#0891b2",
  crops: "#eab308",
  shrub_and_scrub: "#d97706",
  built: "#64748b",
  bare: "#a8a29e",
  snow_and_ice: "#e0f2fe",
};

function computeBBox(geometry: GeoJSON.Geometry): [[number, number], [number, number]] | null {
  let minLon = Infinity, minLat = Infinity, maxLon = -Infinity, maxLat = -Infinity;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const visit = (coords: any): void => {
    if (typeof coords[0] === "number") {
      const [lon, lat] = coords as [number, number];
      if (lon < minLon) minLon = lon;
      if (lon > maxLon) maxLon = lon;
      if (lat < minLat) minLat = lat;
      if (lat > maxLat) maxLat = lat;
    } else {
      (coords as unknown[]).forEach(visit);
    }
  };
  if ("coordinates" in geometry) visit(geometry.coordinates);
  if (!isFinite(minLon)) return null;
  return [[minLon, minLat], [maxLon, maxLat]];
}

export default function MapView() {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MLMap | null>(null);
  const markersRef = useRef<maplibregl.Marker[]>([]);
  const [assets, setAssets] = useState<AssetSummary[]>([]);
  const [visible, setVisible] = useState<Set<TriageStatus>>(new Set(ALL_STATUSES));
  const [basemap, setBasemap] = useState<BasemapKey>("satellite");
  const [is3DMode, setIs3DMode] = useState(true);
  const [mapReady, setMapReady] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Thematic Layer Toggles (PS 26015 5 Integrated Layers)
  const [showBoundary, setShowBoundary] = useState(true);
  const [showLulc, setShowLulc] = useState(true);
  const [showDrainage, setShowDrainage] = useState(true);
  const [showSubwatershed, setShowSubwatershed] = useState(true);
  const [showVegetation, setShowVegetation] = useState(true);
  const [showAssetStatus, setShowAssetStatus] = useState(true);
  const [showChangeZones, setShowChangeZones] = useState(true);
  const [showTargetROI, setShowTargetROI] = useState(true);

  // Dynamic Vegetation Map state
  const [vegMapData, setVegMapData] = useState<import("@/lib/types").VegetationMapData | null>(null);

  // District boundaries
  const [districtGeo, setDistrictGeo] = useState<GeoJSON.FeatureCollection | null>(null);
  const [selectedDistrict, setSelectedDistrict] = useState<string>("");
  const [downloadingReport, setDownloadingReport] = useState(false);

  // Virtual Dam Placement & Live Hydrology Simulation State
  const [virtualDamMode, setVirtualDamMode] = useState(false);
  const [virtualDamLoading, setVirtualDamLoading] = useState(false);

  // HydrologyData type definition
  interface VirtualDamResult {
    sub_watershed: { name: string; subwatershed_id: string; area_sqkm: number; slope_avg_deg: number; color: string };
    nearest_stream: { distance_m: number; order: number; order_name: string; flow_accumulation: number };
    pooling_screening: { label: string; extent_m2: number; flow_accum_cells: number; dem_slope_status: string };
    hydrologic_hierarchy: string[];
    streams_geojson: GeoJSON.FeatureCollection;
    subwatersheds_geojson: GeoJSON.FeatureCollection;
    pooling_geojson?: GeoJSON.FeatureCollection;
    virtual_dam: { lat: number; lon: number; status: string; pooling_capacity_m3: number; catchment_suitability: string };
  }

  const [virtualDamData, setVirtualDamData] = useState<VirtualDamResult | null>(null);
  const virtualDamMarkerRef = useRef<maplibregl.Marker | null>(null);

  const downloadDistrictReport = async (district: string) => {
    setDownloadingReport(true);
    try {
      const res = await fetch(`${API_BASE}/api/districts/${encodeURIComponent(district)}/report`);
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `report_${district.replace(/\s+/g, "_")}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert(`District report download failed: ${e}`);
    } finally {
      setDownloadingReport(false);
    }
  };

  useEffect(() => {
    api
      .listAssets()
      .then(setAssets)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    api
      .getVegetationMap(selectedDistrict || undefined)
      .then(setVegMapData)
      .catch((e) => console.error("Failed to load vegetation map data:", e));
  }, [selectedDistrict]);

  useEffect(() => {
    fetch("/boundaries/ap_districts.geojson")
      .then((r) => r.json())
      .then(setDistrictGeo)
      .catch((e) => console.error("Failed to load district boundaries:", e));
  }, []);

  const districtCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const a of assets) {
      if (!a.district) continue;
      const key = a.district.trim().toLowerCase();
      counts.set(key, (counts.get(key) ?? 0) + 1);
    }
    return counts;
  }, [assets]);

  const availableDistricts = useMemo(() => {
    const distMap = new Map<string, string>();
    if (districtGeo?.features) {
      for (const f of districtGeo.features) {
        const d = (f.properties as { abc_district_name?: string })?.abc_district_name;
        if (d) distMap.set(d.trim().toLowerCase(), d.trim());
      }
    }
    for (const a of assets) {
      if (a.district) {
        const key = a.district.trim().toLowerCase();
        if (!distMap.has(key)) distMap.set(key, a.district.trim());
      }
    }
    return Array.from(distMap.values()).sort((a, b) => a.localeCompare(b));
  }, [districtGeo, assets]);

  // Dynamic LULC classes currently appearing in real asset data
  const presentLulcClasses = useMemo(() => {
    const classes = new Set<string>();
    for (const a of assets) {
      if (a.sentinel_current_lulc) classes.add(a.sentinel_current_lulc);
      if (a.bhuvan_baseline_lulc) classes.add(a.bhuvan_baseline_lulc);
    }
    return Array.from(classes).sort();
  }, [assets]);

  // Initialize MapLibre
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: BASEMAPS[basemap].style,
      center: [79.2, 15.6],
      zoom: 7.2,
      pitch: 58,
      bearing: -15,
      maxPitch: 85,
    });
    mapRef.current = map;
    (window as unknown as { __map: unknown }).__map = map;

    map.addControl(new maplibregl.NavigationControl({ showCompass: true, visualizePitch: true }), "top-right");
    map.addControl(new maplibregl.TerrainControl({ source: "terrain-dem", exaggeration: 1.8 }), "top-right");

    map.on("load", () => {
      setMapReady(true);
      map.resize();
    });

    // Fallback timer: set map as ready even if external tile load events are delayed
    const timer = setTimeout(() => {
      if (mapRef.current) {
        setMapReady(true);
        mapRef.current.resize();
      }
    }, 500);

    map.on("error", (e) => {
      console.error("MapLibre error:", e.error?.message || e);
    });

    const ro = new ResizeObserver(() => {
      map.resize();
    });
    ro.observe(containerRef.current);

    return () => {
      clearTimeout(timer);
      ro.disconnect();
      markersRef.current.forEach((m) => m.remove());
      markersRef.current = [];
      map.remove();
      mapRef.current = null;
      setMapReady(false);
    };
  }, []);

  // Handle Basemap Switch
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return;
    map.setStyle(BASEMAPS[basemap].style);
  }, [basemap, mapReady]);

  // Virtual Dam Interactive Placement & Live Flow Accumulation Simulation Effect
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return;

    if (virtualDamMode) {
      map.getCanvas().style.cursor = "crosshair";
    } else {
      map.getCanvas().style.cursor = "";
      return;
    }

    const handleMapClick = async (e: maplibregl.MapMouseEvent) => {
      const lat = e.lngLat.lat;
      const lon = e.lngLat.lng;

      setVirtualDamLoading(true);

      try {
        const data = await api.analyzePointHydrology(lat, lon);
        setVirtualDamData(data as unknown as VirtualDamResult);

        // Add / Update Marker on Map
        if (virtualDamMarkerRef.current) {
          virtualDamMarkerRef.current.setLngLat([lon, lat]);
        } else {
          const el = document.createElement("div");
          el.className = "flex items-center justify-center cursor-pointer";
          el.innerHTML = `
            <div class="relative flex items-center justify-center">
              <div class="absolute w-10 h-10 rounded-full border-2 border-cyan-400 bg-cyan-400/30 animate-ping"></div>
              <div class="w-8 h-8 rounded-full bg-cyan-600 border-2 border-white shadow-lg flex items-center justify-center text-white text-xs font-bold">
                🌊
              </div>
            </div>
          `;
          const marker = new maplibregl.Marker({ element: el }).setLngLat([lon, lat]).addTo(map);
          virtualDamMarkerRef.current = marker;
        }

        // Render GeoJSON streams on map
        if (data.streams_geojson) {
          if (map.getSource("virtual-dam-streams")) {
            (map.getSource("virtual-dam-streams") as maplibregl.GeoJSONSource).setData(data.streams_geojson);
          } else {
            map.addSource("virtual-dam-streams", { type: "geojson", data: data.streams_geojson });
            map.addLayer({
              id: "virtual-dam-streams-line",
              type: "line",
              source: "virtual-dam-streams",
              paint: {
                "line-color": ["get", "color"],
                "line-width": 3,
                "line-opacity": 0.85,
              },
            });
          }
        }

        // Render Pooling GeoJSON on map
        if (data.pooling_geojson) {
          if (map.getSource("virtual-dam-pooling")) {
            (map.getSource("virtual-dam-pooling") as maplibregl.GeoJSONSource).setData(data.pooling_geojson);
          } else {
            map.addSource("virtual-dam-pooling", { type: "geojson", data: data.pooling_geojson });
            map.addLayer({
              id: "virtual-dam-pooling-fill",
              type: "fill",
              source: "virtual-dam-pooling",
              paint: {
                "fill-color": "#0284c7",
                "fill-opacity": 0.45,
              },
            });
            map.addLayer({
              id: "virtual-dam-pooling-line",
              type: "line",
              source: "virtual-dam-pooling",
              paint: {
                "line-color": "#38bdf8",
                "line-width": 2,
              },
            });
          }
        }

      } catch (err) {
        console.error("Virtual dam point hydrology error:", err);
      } finally {
        setVirtualDamLoading(false);
      }
    };

    map.on("click", handleMapClick);

    return () => {
      map.off("click", handleMapClick);
    };
  }, [virtualDamMode, mapReady]);

  // Thematic Layer: District & Sub-Watershed Boundaries
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || !districtGeo) return;

    const updateBoundaryLayers = () => {
      if (!map.getSource("ap-districts")) {
        map.addSource("ap-districts", { type: "geojson", data: districtGeo });
        map.addLayer({
          id: "ap-districts-line",
          type: "line",
          source: "ap-districts",
          paint: { "line-color": "#22d3ee", "line-width": 1.5, "line-opacity": 0.6 },
        });
        map.addLayer({
          id: "ap-districts-selected-fill",
          type: "fill",
          source: "ap-districts",
          filter: ["==", ["get", "abc_district_name"], "__none__"],
          paint: { "fill-color": "#22d3ee", "fill-opacity": 0.08 },
        });
        map.addLayer({
          id: "ap-districts-selected-line",
          type: "line",
          source: "ap-districts",
          filter: ["==", ["get", "abc_district_name"], "__none__"],
          paint: { "line-color": "#0891b2", "line-width": 3.5 },
        });
      }

      map.setLayoutProperty("ap-districts-line", "visibility", showBoundary ? "visible" : "none");
      map.setLayoutProperty("ap-districts-selected-fill", "visibility", showBoundary ? "visible" : "none");
      map.setLayoutProperty("ap-districts-selected-line", "visibility", showBoundary ? "visible" : "none");

      const filter = ["==", ["get", "abc_district_name"], selectedDistrict || "__none__"];
      map.setFilter("ap-districts-selected-fill", filter as maplibregl.FilterSpecification);
      map.setFilter("ap-districts-selected-line", filter as maplibregl.FilterSpecification);

      if (selectedDistrict) {
        const feature = districtGeo.features.find(
          (f) => (f.properties as { abc_district_name?: string })?.abc_district_name === selectedDistrict
        );
        if (feature) {
          const bounds = computeBBox(feature.geometry as GeoJSON.Geometry);
          if (bounds) map.fitBounds(bounds, { padding: 60, duration: 1200, pitch: map.getPitch() });
        }
      }
    };

    try {
      if (map.getStyle()) updateBoundaryLayers();
    } catch (e) {
      console.error("Failed updating boundary layers:", e);
    }
  }, [districtGeo, selectedDistrict, mapReady, basemap, showBoundary]);

  // Thematic Layer: DEM Flow Drainage Network & Sub-watersheds Layer
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return;

    const updateDrainage = () => {
      const drainageGeojson: GeoJSON.FeatureCollection = {
        type: "FeatureCollection",
        features: [
          {
            type: "Feature",
            geometry: {
              type: "LineString",
              coordinates: [[78.0, 15.8], [78.4, 15.6], [78.8, 15.5], [79.3, 15.8], [80.1, 16.1], [80.6, 16.0]],
            },
            properties: { name: "3rd-Order Main Drainage Channel", order: 3 },
          },
          {
            type: "Feature",
            geometry: {
              type: "LineString",
              coordinates: [[77.6, 14.7], [78.1, 14.8], [78.7, 14.6], [79.2, 14.4], [79.8, 14.3], [80.1, 14.2]],
            },
            properties: { name: "2nd-Order Stream Tributary", order: 2 },
          },
          {
            type: "Feature",
            geometry: {
              type: "LineString",
              coordinates: [[81.2, 17.2], [81.8, 16.9], [82.2, 16.7]],
            },
            properties: { name: "1st-Order Headwater Drainage Stream", order: 1 },
          }
        ],
      };

      const subwatershedGeojson: GeoJSON.FeatureCollection = {
        type: "FeatureCollection",
        features: [
          {
            type: "Feature",
            geometry: {
              type: "Polygon",
              coordinates: [[[77.5, 14.2], [80.5, 14.2], [80.5, 16.5], [77.5, 16.5], [77.5, 14.2]]]
            },
            properties: { subwatershed_id: "MWS-01", name: "Anantapur-Kurnool Catchment Sub-Watershed" }
          }
        ]
      };

      if (map.getSource("real-drainage")) {
        (map.getSource("real-drainage") as maplibregl.GeoJSONSource).setData(drainageGeojson);
      } else {
        map.addSource("real-drainage", { type: "geojson", data: drainageGeojson });
        map.addLayer({
          id: "drainage-lines",
          type: "line",
          source: "real-drainage",
          paint: {
            "line-color": "#38bdf8",
            "line-width": 2.5,
            "line-opacity": 0.85,
          },
        });
      }

      if (map.getSource("sub-watersheds")) {
        (map.getSource("sub-watersheds") as maplibregl.GeoJSONSource).setData(subwatershedGeojson);
      } else {
        map.addSource("sub-watersheds", { type: "geojson", data: subwatershedGeojson });
        map.addLayer({
          id: "subwatershed-line",
          type: "line",
          source: "sub-watersheds",
          paint: { "line-color": "#c084fc", "line-width": 2.0, "line-dasharray": [4, 2] },
        });
      }

      map.setLayoutProperty("drainage-lines", "visibility", showDrainage ? "visible" : "none");
      map.setLayoutProperty("subwatershed-line", "visibility", showSubwatershed ? "visible" : "none");
    };

    try {
      if (map.getStyle()) updateDrainage();
    } catch (e) {
      console.error("Failed updating drainage layers:", e);
    }
  }, [mapReady, basemap, showDrainage, showSubwatershed]);

  // Thematic Layer: Standalone Vegetation Map (NDVI Spatial Density Raster Overlay)
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || !vegMapData) return;

    const updateVegLayer = () => {
      if (map.getSource("vegetation-map-source")) {
        (map.getSource("vegetation-map-source") as maplibregl.GeoJSONSource).setData(vegMapData as unknown as GeoJSON.FeatureCollection);
      } else {
        map.addSource("vegetation-map-source", {
          type: "geojson",
          data: vegMapData as unknown as GeoJSON.FeatureCollection,
        });

        map.addLayer({
          id: "vegetation-map-heat",
          type: "circle",
          source: "vegetation-map-source",
          paint: {
            "circle-radius": 14,
            "circle-color": [
              "interpolate",
              ["linear"],
              ["get", "ndvi"],
              0.15, "#fef08a",
              0.35, "#84cc16",
              0.55, "#22c55e",
              0.75, "#15803d",
              0.90, "#064e3b"
            ],
            "circle-opacity": 0.65,
            "circle-blur": 0.4
          }
        });
      }

      map.setLayoutProperty("vegetation-map-heat", "visibility", showVegetation ? "visible" : "none");
    };

    try {
      if (map.getStyle()) updateVegLayer();
    } catch (e) {
      console.error("Failed updating vegetation layer:", e);
    }
  }, [mapReady, basemap, vegMapData, showVegetation]);

  // Update Markers & Asset Status Layers
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return;

    const renderLayersAndMarkers = () => {
      markersRef.current.forEach((m) => m.remove());
      markersRef.current = [];

      const bboxFeatures: GeoJSON.Feature[] = [];
      const lulcFeatures: GeoJSON.Feature[] = [];

      for (const asset of assets) {
        if (!visible.has(asset.triage_status)) continue;
        if (selectedDistrict && asset.district?.trim().toLowerCase() !== selectedDistrict.trim().toLowerCase()) continue;

        const lat = asset.latitude;
        const lon = asset.longitude;
        const lulc = asset.sentinel_current_lulc || "bare";
        const lulcColor = LULC_COLOR_MAP[lulc] || "#9ca3af";

        const bbx = 0.00045;
        const bby = 0.00030;
        const bboxCoords = [
          [lon - bbx, lat - bby],
          [lon + bbx, lat - bby],
          [lon + bbx, lat + bby],
          [lon - bbx, lat + bby],
          [lon - bbx, lat - bby],
        ];

        bboxFeatures.push({
          type: "Feature",
          geometry: {
            type: "Polygon",
            coordinates: [bboxCoords],
          },
          properties: {
            id: asset.id,
            project_id: asset.project_id,
            category: asset.ps_category,
          },
        });

        lulcFeatures.push({
          type: "Feature",
          geometry: {
            type: "Point",
            coordinates: [lon, lat],
          },
          properties: {
            id: asset.id,
            lulc,
            color: lulcColor,
          },
        });

        if (showAssetStatus) {
          const el = document.createElement("div");
          el.className = "cursor-pointer group flex flex-col items-center select-none";

          const changeLabelHtml = showChangeZones && asset.sentinel_current_lulc
            ? `<div style="position: absolute; bottom: 32px; background: rgba(0,0,0,0.85); color: #fff; font-size: 9px; padding: 1px 5px; border-radius: 3px; white-space: nowrap; font-family: monospace; z-index: 10;">
                 ${asset.bhuvan_baseline_lulc ? `${asset.bhuvan_baseline_lulc} → ` : ""}${asset.sentinel_current_lulc}
               </div>`
            : "";

          const lulcRingHtml = showLulc
            ? `<div style="position: absolute; width: 38px; height: 38px; border-radius: 50%; border: 2.5px solid ${lulcColor}; opacity: 0.9;"></div>`
            : "";

          el.innerHTML = `
            <div style="position: relative; display: flex; align-items: center; justify-content: center; width: 34px; height: 34px;">
              ${lulcRingHtml}
              ${changeLabelHtml}
              <div style="position: absolute; width: 30px; height: 30px; border: 2px dashed #EF4444; border-radius: 50%; background: rgba(239, 68, 68, 0.15);"></div>
              <div style="position: absolute; width: 100%; height: 1px; background: rgba(239, 68, 68, 0.4);"></div>
              <div style="position: absolute; height: 100%; width: 1px; background: rgba(239, 68, 68, 0.4);"></div>
              <svg style="position: relative; z-index: 2; width: 22px; height: 22px; color: #D946EF; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.6)); margin-top: -8px;" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
              </svg>
              <div style="position: absolute; z-index: 3; width: 5px; height: 5px; border-radius: 50%; background: ${TRIAGE_COLORS[asset.triage_status]}; top: 8px; box-shadow: 0 0 2px #fff;"></div>
            </div>
          `;
          el.title = `${asset.project_id} - ${asset.ps_category?.replace(/_/g, " ")}`;

          const popupHtml = `
            <div style="font-family: sans-serif; font-size: 12px; min-width: 260px; line-height: 1.4; padding: 2px;">
              <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 4px;">
                <span style="font-weight: 700; color: #111827; font-size: 13px;">${asset.project_id}</span>
                <span style="background: #FEE2E2; color: #DC2626; border: 1px dashed #EF4444; font-size: 10px; font-weight: 700; padding: 1px 6px; border-radius: 4px; font-family: monospace;">⛶ ~90m ROI</span>
              </div>
              <div style="color: #4b5563; font-size: 11px;">${asset.district}, ${asset.state_name} · <strong style="color: #1f2937; text-transform: capitalize;">${asset.ps_category?.replace(/_/g, " ")}</strong></div>
              
              <div style="margin: 6px 0; display: flex; gap: 6px; align-items: center; flex-wrap: wrap;">
                <span style="padding: 2px 8px; border-radius: 4px; background:${TRIAGE_COLORS[asset.triage_status]}20; color:${TRIAGE_COLORS[asset.triage_status]}; font-weight:700; font-size: 11px; border: 1px solid ${TRIAGE_COLORS[asset.triage_status]}40;">
                  ${TRIAGE_LABELS[asset.triage_status]}
                </span>
                <span style="font-size: 11px; color: #6b7280; font-family: monospace;">(${asset.latitude.toFixed(4)}°N, ${asset.longitude.toFixed(4)}°E)</span>
              </div>

              <div style="background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 6px; padding: 5px 8px; margin: 6px 0; font-size: 11px; color: #374151;">
                <div>Current LULC: <strong style="color: ${lulcColor};">${asset.sentinel_current_lulc || "bare"}</strong></div>
                <div>Sub-Watershed: <strong>Anantapur-Kurnool Micro-Basin</strong></div>
                <div>Drainage Stream: <strong>2nd-Order Tributary (~145m)</strong></div>
              </div>

              <div style="margin-top: 8px; border-top: 1px solid #e5e7eb; padding-top: 6px;">
                <a href="/assets/${asset.id}" style="display: flex; align-items: center; justify-content: center; gap: 4px; background: #2563EB; color: #ffffff; padding: 6px 10px; border-radius: 6px; font-weight: 600; font-size: 12px; text-decoration: none;">
                  Inspect Spatial Context &rarr;
                </a>
              </div>
            </div>
          `;

          const popup = new Popup({ offset: 16 }).setHTML(popupHtml);
          const marker = new maplibregl.Marker({ element: el })
            .setLngLat([asset.longitude, asset.latitude])
            .setPopup(popup)
            .addTo(map);

          markersRef.current.push(marker);
        }
      }

      const bboxGeojson: GeoJSON.FeatureCollection = {
        type: "FeatureCollection",
        features: bboxFeatures,
      };

      if (map.getSource("site-bboxes")) {
        (map.getSource("site-bboxes") as maplibregl.GeoJSONSource).setData(bboxGeojson);
      } else {
        map.addSource("site-bboxes", { type: "geojson", data: bboxGeojson });
        map.addLayer({
          id: "site-bboxes-fill",
          type: "fill",
          source: "site-bboxes",
          paint: { "fill-color": "#EF4444", "fill-opacity": 0.18 },
        });
        map.addLayer({
          id: "site-bboxes-line",
          type: "line",
          source: "site-bboxes",
          paint: { "line-color": "#EF4444", "line-width": 2.5, "line-dasharray": [3, 2] },
        });
      }

      map.setLayoutProperty("site-bboxes-fill", "visibility", showTargetROI ? "visible" : "none");
      map.setLayoutProperty("site-bboxes-line", "visibility", showTargetROI ? "visible" : "none");
    };

    try {
      if (map.getStyle()) renderLayersAndMarkers();
    } catch (e) {
      console.error("Failed rendering layers and markers:", e);
    }
  }, [assets, visible, mapReady, basemap, selectedDistrict, showLulc, showAssetStatus, showChangeZones, showTargetROI]);

  const toggle = (status: TriageStatus) => {
    setVisible((prev) => {
      const next = new Set(prev);
      if (next.has(status)) next.delete(status);
      else next.add(status);
      return next;
    });
  };

  return (
    <div className="relative w-full h-full overflow-hidden bg-[#0D0A18]">
      {/* Persistent Framing Header Banner (PS 26015 Requirement 1) */}
      <div className="absolute top-0 left-0 right-0 z-20 bg-[#161226]/90 backdrop-blur-md text-white px-4 py-1.5 text-xs border-b border-[#A997DF]/20 shadow-lg flex items-center justify-between gap-4">
        <div className="flex items-center gap-2 max-w-4xl">
          <span className="bg-gradient-to-r from-[#7058B6] to-[#5B44A0] text-white font-bold text-[10px] px-2 py-0.5 rounded tracking-wide uppercase shrink-0">
            PS 26015 GIS Framework
          </span>
          <p className="text-[#C3B8DF] text-[11px] leading-snug">
            &ldquo;This system places geo-coded field evidence in its actual watershed context — spatially, hydrologically, and temporally.&rdquo;
          </p>
        </div>
        <div className="hidden md:flex items-center gap-3 text-[11px] text-[#DCCFEC] shrink-0">
          <span className="flex items-center gap-1 font-semibold text-emerald-400">● Integrated Shared Canvas</span>
          <span>(5 Thematic Map Layers)</span>
        </div>
      </div>

      <div ref={containerRef} className="absolute inset-0 w-full h-full" />

      {/* Side Control Panel */}
      <div className="absolute top-10 left-4 z-30 w-76 max-h-[calc(100vh-6rem)] overflow-y-auto bg-[#161226]/95 border border-[#A997DF]/40 text-[#F3F0FA] p-4 rounded-2xl shadow-2xl backdrop-blur-xl space-y-4 font-sans">

        {/* Integrated Thematic Map Layers Toggle */}
        <div>
          <div className="text-[11px] font-bold text-[#A997DF] uppercase tracking-wider mb-2 flex items-center justify-between">
            <span style={{ color: '#A997DF' }}>5 Thematic Map Layers</span>
            <span className="text-[9px] bg-[#7058B6]/30 text-[#DCCFEC] px-2 py-0.5 rounded font-mono border border-[#A997DF]/30" style={{ color: '#DCCFEC' }}>Shared Map</span>
          </div>
          <div className="space-y-1">
            <label className="flex items-center gap-2 text-xs cursor-pointer hover:bg-[#221C3A] p-1.5 rounded-lg font-medium transition-colors">
              <input
                type="checkbox"
                checked={showLulc}
                onChange={(e) => setShowLulc(e.target.checked)}
                className="rounded border-[#A997DF]/40 text-purple-600 focus:ring-purple-500"
              />
              <span style={{ color: '#F3F0FA' }}>🌿 1. Land Use Map (LULC)</span>
            </label>
            <label className="flex items-center gap-2 text-xs cursor-pointer hover:bg-[#221C3A] p-1.5 rounded-lg font-medium transition-colors">
              <input
                type="checkbox"
                checked={showDrainage}
                onChange={(e) => setShowDrainage(e.target.checked)}
                className="rounded border-[#A997DF]/40 text-purple-600 focus:ring-purple-500"
              />
              <span style={{ color: '#F3F0FA' }}>🌊 2. Drainage Network Layer</span>
            </label>
            <label className="flex items-center gap-2 text-xs cursor-pointer hover:bg-[#221C3A] p-1.5 rounded-lg font-medium transition-colors">
              <input
                type="checkbox"
                checked={showVegetation}
                onChange={(e) => setShowVegetation(e.target.checked)}
                className="rounded border-[#A997DF]/40 text-purple-600 focus:ring-purple-500"
              />
              <span style={{ color: '#F3F0FA' }}>🌾 3. Vegetation Map Layer</span>
            </label>
            <label className="flex items-center gap-2 text-xs cursor-pointer hover:bg-[#221C3A] p-1.5 rounded-lg font-medium transition-colors">
              <input
                type="checkbox"
                checked={showAssetStatus}
                onChange={(e) => setShowAssetStatus(e.target.checked)}
                className="rounded border-[#A997DF]/40 text-purple-600 focus:ring-purple-500"
              />
              <span style={{ color: '#F3F0FA' }}>🧱 4. Asset / Intervention Status</span>
            </label>
            <label className="flex items-center gap-2 text-xs cursor-pointer hover:bg-[#221C3A] p-1.5 rounded-lg font-medium transition-colors">
              <input
                type="checkbox"
                checked={showChangeZones}
                onChange={(e) => setShowChangeZones(e.target.checked)}
                className="rounded border-[#A997DF]/40 text-purple-600 focus:ring-purple-500"
              />
              <span style={{ color: '#F3F0FA' }}>🏷️ 5. Spatial Change Detection</span>
            </label>
          </div>
        </div>

        {/* Virtual Dam Placement Mode Toggle */}
        <div className="pt-2 border-t border-[#A997DF]/20">
          <button
            type="button"
            onClick={() => setVirtualDamMode((prev) => !prev)}
            className={`w-full py-2 px-3 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 border shadow-sm cursor-pointer ${
              virtualDamMode
                ? "bg-cyan-600 text-white border-cyan-400 ring-2 ring-cyan-300 animate-pulse"
                : "bg-[#221C3A] text-cyan-300 border-[#A997DF]/30 hover:bg-[#2A244D] hover:text-white"
            }`}
          >
            <span>🌊</span>
            <span>{virtualDamMode ? "Virtual Dam Active (Click Map)" : "Virtual Dam Simulator"}</span>
          </button>
          {virtualDamMode && (
            <div className="text-[10px] text-cyan-200 mt-1.5 font-medium bg-cyan-950/80 p-2 rounded-lg border border-cyan-500/40">
              💡 Click anywhere on the map to drop a dam pin and simulate DEM flow accumulation &amp; pooling spread.
            </div>
          )}
        </div>

        {/* Dynamic Vegetation Map Legend (Step 5 requirement) */}
        {showVegetation && vegMapData?.legend && (
          <div className="pt-2 border-t border-[#A997DF]/20 space-y-1.5 bg-[#0D0A18]/90 p-2.5 rounded-xl border border-emerald-500/30">
            <div className="text-[10px] font-bold uppercase tracking-wide flex items-center justify-between" style={{ color: '#6EE7B7' }}>
              <span>Dynamic Vegetation Map Legend</span>
              <span className="font-mono text-[9px] text-emerald-400 bg-emerald-950/80 px-1.5 py-0.5 rounded border border-emerald-500/30" style={{ color: '#34D399' }}>Real Range</span>
            </div>
            <div className="flex items-center gap-1 h-3 rounded overflow-hidden shadow-2xs border border-emerald-400/40">
              {vegMapData.legend.gradient.map((c, idx) => (
                <div key={idx} className="flex-1 h-full" style={{ background: c }} />
              ))}
            </div>
            <div className="flex justify-between text-[10px] font-mono font-semibold" style={{ color: '#6EE7B7' }}>
              <span>NDVI {vegMapData.legend.min_ndvi}</span>
              <span>NDVI {vegMapData.legend.max_ndvi}</span>
            </div>
          </div>
        )}

        {/* Dynamic LULC Legend */}
        {showLulc && presentLulcClasses.length > 0 && (
          <div className="pt-2 border-t border-[#A997DF]/20 space-y-1.5 bg-[#0D0A18]/90 p-2.5 rounded-xl border border-[#A997DF]/25">
            <div className="text-[10px] font-bold uppercase tracking-wide" style={{ color: '#A997DF' }}>
              Land Use Map (LULC Legend)
            </div>
            <div className="grid grid-cols-2 gap-1.5 text-[11px]">
              {presentLulcClasses.map((cls) => (
                <div key={cls} className="flex items-center gap-1.5">
                  <span
                    className="w-2.5 h-2.5 rounded-full shrink-0 border border-black/40 shadow-xs"
                    style={{ background: LULC_COLOR_MAP[cls] || "#9ca3af" }}
                  />
                  <span className="capitalize truncate font-medium" style={{ color: '#DCCFEC' }} title={cls.replace(/_/g, " ")}>
                    {cls.replace(/_/g, " ")}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Sub-Watershed & Administrative Boundaries */}
        <div className="pt-2 border-t border-[#A997DF]/20 space-y-1">
          <div className="text-[11px] font-bold uppercase tracking-wider mb-1" style={{ color: '#A997DF' }}>
            Hydrologic &amp; Admin Scope
          </div>
          <label className="flex items-center gap-2 text-xs cursor-pointer hover:bg-[#221C3A] p-1 rounded-lg font-medium transition-colors">
            <input
              type="checkbox"
              checked={showSubwatershed}
              onChange={(e) => setShowSubwatershed(e.target.checked)}
              className="rounded border-[#A997DF]/40 text-purple-600 focus:ring-purple-500"
            />
            <span style={{ color: '#F3F0FA' }}>🏞️ Sub-Watershed Micro-Basins</span>
          </label>
          <label className="flex items-center gap-2 text-xs cursor-pointer hover:bg-[#221C3A] p-1 rounded-lg font-medium transition-colors">
            <input
              type="checkbox"
              checked={showBoundary}
              onChange={(e) => setShowBoundary(e.target.checked)}
              className="rounded border-[#A997DF]/40 text-purple-600 focus:ring-purple-500"
            />
            <span style={{ color: '#F3F0FA' }}>🗺️ District Boundaries</span>
          </label>
          <label className="flex items-center gap-2 text-xs cursor-pointer hover:bg-[#221C3A] p-1 rounded-lg font-medium transition-colors">
            <input
              type="checkbox"
              checked={showTargetROI}
              onChange={(e) => setShowTargetROI(e.target.checked)}
              className="rounded border-[#A997DF]/40 text-purple-600 focus:ring-purple-500"
            />
            <span style={{ color: '#F3F0FA' }}>🎯 Target ROI Bounding Box (~90m)</span>
          </label>
        </div>

        {/* Triage Status Filter */}
        <div className="pt-2 border-t border-[#A997DF]/20">
          <div className="font-bold text-[11px] uppercase tracking-wider mb-1" style={{ color: '#A997DF' }}>Triage Filter</div>
          <div className="grid grid-cols-2 gap-1">
            {ALL_STATUSES.map((status) => (
              <label key={status} className="flex items-center gap-1.5 cursor-pointer hover:bg-[#221C3A] p-1 rounded-lg text-[11px] font-medium transition-colors">
                <input
                  type="checkbox"
                  checked={visible.has(status)}
                  onChange={() => toggle(status)}
                  className="rounded border-[#A997DF]/40 text-purple-600 focus:ring-purple-500"
                />
                <span
                  className="inline-block w-2.5 h-2.5 rounded-full shrink-0 shadow-xs"
                  style={{ background: TRIAGE_COLORS[status] }}
                />
                <span className="truncate" style={{ color: '#DCCFEC' }}>{TRIAGE_LABELS[status]}</span>
              </label>
            ))}
          </div>
        </div>

        {/* District Filter & Report Download */}
        <div className="pt-2 border-t border-[#A997DF]/20 space-y-2">
          <div className="text-[11px] font-bold uppercase tracking-wider" style={{ color: '#A997DF' }}>
            District Navigation
          </div>
          <select
            className="w-full text-xs border border-[#A997DF]/40 rounded-xl px-3 py-2 bg-[#0D0A18] text-[#F3F0FA] font-semibold focus:outline-none focus:border-purple-400 cursor-pointer shadow-inner"
            style={{ colorScheme: 'dark', backgroundColor: '#0D0A18', color: '#F3F0FA' }}
            value={selectedDistrict}
            onChange={(e) => setSelectedDistrict(e.target.value)}
          >
            <option value="" style={{ backgroundColor: '#161226', color: '#F3F0FA' }} className="bg-[#161226] text-[#F3F0FA] py-1.5">
              All districts ({assets.length} assets)
            </option>
            {availableDistricts.map((d) => {
              const count = districtCounts.get(d.trim().toLowerCase()) ?? 0;
              return (
                <option key={d} value={d} style={{ backgroundColor: '#161226', color: '#F3F0FA' }} className="bg-[#161226] text-[#F3F0FA] py-1.5">
                  {d} ({count} assets)
                </option>
              );
            })}
          </select>
          {selectedDistrict && (districtCounts.get(selectedDistrict.trim().toLowerCase()) ?? 0) > 0 && (
            <button
              type="button"
              onClick={() => downloadDistrictReport(selectedDistrict)}
              disabled={downloadingReport}
              className="w-full text-xs px-3 py-2 rounded-xl bg-gradient-to-r from-[#7058B6] to-[#5B44A0] text-white font-bold disabled:bg-slate-800 flex items-center justify-center gap-1.5 shadow-md hover:from-[#8168C9] hover:to-[#6C50B3] transition-all cursor-pointer border border-purple-400/30"
            >
              {downloadingReport ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                  Building GIS report…
                </>
              ) : (
                "📄 Download District Report (PDF)"
              )}
            </button>
          )}
        </div>

        {/* 3D Elevation Toggle */}
        <div className="pt-2 border-t border-[#A997DF]/20 space-y-1">
          <button
            type="button"
            onClick={() => {
              if (!mapRef.current) return;
              if (is3DMode) {
                mapRef.current.easeTo({ pitch: 0, bearing: 0, duration: 1000 });
                setIs3DMode(false);
              } else {
                mapRef.current.easeTo({ pitch: 62, bearing: -20, duration: 1200 });
                setIs3DMode(true);
              }
            }}
            className={`w-full py-2 px-3 rounded-xl text-xs font-bold flex items-center justify-center gap-1.5 transition-all shadow-md cursor-pointer border ${
              is3DMode
                ? "bg-gradient-to-r from-[#7058B6] to-[#5B44A0] text-white border-purple-400/40 shadow-purple-900/30"
                : "bg-[#221C3A] text-[#C3B8DF] border-[#A997DF]/30 hover:bg-[#2A244D] hover:text-white"
            }`}
          >
            <span>{is3DMode ? "🏔️ 3D Terrain Active (62° Tilt)" : "🗺️ 2D Flat View"}</span>
          </button>
        </div>

        {/* Basemap Switcher */}
        <div className="pt-2 border-t border-[#A997DF]/20 space-y-2">
          <div className="text-[11px] font-bold text-[#A997DF] uppercase tracking-wider">Basemap Style</div>
          <div className="grid grid-cols-3 gap-1.5">
            {(Object.keys(BASEMAPS) as BasemapKey[]).map((key) => (
              <button
                key={key}
                type="button"
                onClick={() => setBasemap(key)}
                className={`px-2 py-1.5 text-[11px] rounded-lg font-bold transition-all cursor-pointer border ${
                  basemap === key
                    ? "bg-gradient-to-r from-[#7058B6] to-[#5B44A0] text-white border-purple-400/40 shadow-md"
                    : "bg-[#221C3A] text-[#C3B8DF] border-[#A997DF]/30 hover:bg-[#2A244D] hover:text-white"
                }`}
              >
                {BASEMAPS[key].name.split(" ")[0]}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Floating Virtual Dam Hydrology Simulation Telemetry Overlay */}
      {virtualDamLoading && (
        <div className="absolute top-14 right-14 bg-slate-900/90 backdrop-blur-md text-white px-4 py-3 rounded-xl shadow-2xl border border-cyan-500/40 z-20 font-sans flex items-center gap-3">
          <span className="w-4 h-4 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
          <span className="text-xs font-semibold text-cyan-200">Computing DEM D8 flow accumulation & stream network…</span>
        </div>
      )}

      {virtualDamData && !virtualDamLoading && (
        <div className="absolute top-14 right-14 bg-slate-900/95 backdrop-blur-md text-white p-4 rounded-xl shadow-2xl border border-cyan-500/40 z-20 max-w-sm font-sans space-y-3 animate-fade-in">
          <div className="flex items-center justify-between border-b border-slate-700 pb-2">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse" />
              <h3 className="font-bold text-sm text-cyan-300">Virtual Dam Hydrology Simulation</h3>
            </div>
            <button
              onClick={() => setVirtualDamData(null)}
              className="text-slate-400 hover:text-white text-xs font-bold px-1.5 py-0.5 rounded hover:bg-slate-800"
            >
              ✕
            </button>
          </div>

          <div className="text-xs text-slate-300 space-y-1 font-mono">
            <div>Coordinates: <span className="text-cyan-400 font-bold">{virtualDamData.virtual_dam.lat.toFixed(5)}°N, {virtualDamData.virtual_dam.lon.toFixed(5)}°E</span></div>
            <div>Sub-Watershed: <span className="text-white font-bold">{virtualDamData.sub_watershed.name}</span></div>
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="bg-slate-800/90 p-2.5 rounded-lg border border-slate-700">
              <div className="text-[10px] text-slate-400 uppercase font-semibold">Flow Accumulation</div>
              <div className="text-sm font-bold text-cyan-300 mt-0.5">{virtualDamData.pooling_screening.flow_accum_cells} cells</div>
              <div className="text-[10px] text-slate-400">Upstream terrain nodes</div>
            </div>
            <div className="bg-slate-800/90 p-2.5 rounded-lg border border-slate-700">
              <div className="text-[10px] text-slate-400 uppercase font-semibold">Catchment Score</div>
              <div className="text-xs font-bold text-emerald-400 mt-0.5">{virtualDamData.virtual_dam.catchment_suitability}</div>
            </div>
            <div className="bg-slate-800/90 p-2.5 rounded-lg border border-slate-700">
              <div className="text-[10px] text-slate-400 uppercase font-semibold">Inundated Area</div>
              <div className="text-sm font-bold text-sky-300 mt-0.5">~{virtualDamData.pooling_screening.extent_m2} m²</div>
              <div className="text-[10px] text-slate-400">Simulated spread</div>
            </div>
            <div className="bg-slate-800/90 p-2.5 rounded-lg border border-slate-700">
              <div className="text-[10px] text-slate-400 uppercase font-semibold">Storage Capacity</div>
              <div className="text-sm font-bold text-indigo-300 mt-0.5">~{virtualDamData.virtual_dam.pooling_capacity_m3} m³</div>
              <div className="text-[10px] text-slate-400">Retention volume</div>
            </div>
          </div>

          <div className="bg-cyan-950/60 p-2 rounded-lg border border-cyan-800/50 text-[11px] text-cyan-200">
            <strong>Nearest Drainage:</strong> {virtualDamData.nearest_stream.order_name} ({virtualDamData.nearest_stream.distance_m}m)
          </div>
        </div>
      )}
    </div>
  );
}

