# SRISHTI-DRISHTI Integrated Geospatial Visualization & Verification Framework (PS 26015)

## 🌊 System Framing & Core Methodology
> **Core Opening Framing:**
> *"This system takes a geo-coded field photograph and places it in its actual watershed context — spatially, hydrologically, and temporally — to support evidence-based interpretation, not to declare fraud."*

The platform provides **evidence-based anomaly detection and verification support** for Mahatma Gandhi NREGS and Integrated Watershed Management Programme (IWMP) field assets across India. It connects field ground truth photographs from SRISHTI-DRISHTI to authoritative satellite imagery, hydrological flow networks, sub-watershed boundaries, and thematic land-surface products.

---

## 🗺️ Integrated Geospatial Methodology (GIS-First Approach)

1. **Copernicus DEM & Hydrological Modeling (`DEM → Flow Direction → Flow Accumulation`)**
   - Ingests Copernicus 30m Global DEM (GLO-30) terrain matrices.
   - Computes D8 steepest-descent flow direction vectors and upstream cell flow accumulation.
2. **Drainage Stream Network Layer**
   - Extracts 1st-Order (Headwater), 2nd-Order (Tributary), and 3rd-Order (Main Channel) Strahler stream lines.
   - Computes exact spatial proximity (distance in meters and stream order) between field intervention assets and nearest drainage channels.
3. **Sub-Watershed Boundary Delineation**
   - Automatically delineates micro-watershed sub-basin boundaries (e.g. `MWS-NW-01 Upper Catchment`).
   - Establishes the spatial backbone hierarchy: `Regional Basin → Micro-Watershed → Drainage Stream → Asset Geolocation → Vegetation/LULC Layer`.
4. **Standalone Land-Use Mapping (LULC)**
   - Integrates Bhuvan ISRO baseline LULC classifications with Sentinel-2 / Dynamic World current land cover (Agriculture, Forest, Built-up, Barren, Water).
5. **Standalone Vegetation Map Layer**
   - Renders continuous spatial NDVI vegetation density gradients across project areas with dynamically computed legend ranges (`NDVI min–max`).
6. **Spatial Change-Zone Detection & Asset Status Mapping**
   - Maps baseline vs. current land-surface transitions and pairs target ROI bounding boxes (~90m x 65m) around structures.
7. **Advanced Impact Analysis (RESTREND Module)**
   - Perform OLS residual trend regression against IMD / Open-Meteo precipitation series to separate climate-driven greening from human intervention impact.
8. **Supporting Decision Tools**
   - Integrates CLIP visual zero-shot verification, Random Forest DPR site-feasibility scoring, and role-routed specialist verification workflows.

---

## 🚀 Key System Features & Interface Structure
- **Integrated Shared Map Canvas:** All 5 thematic map layers (Land Use, Drainage Network, Vegetation Map, Asset Status, Spatial Change Detection) are toggleable together on one interactive MapLibre canvas with 3D elevation controls.
- **Geospatial Asset Detail Inspection:** Inspect before/after satellite sliders, ground truth photo pairings, exact hydrological hierarchy, and advanced RESTREND analytics.
- **Simulated SRISHTI-DRISHTI Ingestion Layer:** Interactive ingestion prototype for field data feeds with clear integration status labeling.
- **Multi-Specialist Verification Workflow:** Cross-validation engine routing flagged sites to designated domain specialists (Water Management, Agriculture, Soil Science, Social Mobilization, Committee).
