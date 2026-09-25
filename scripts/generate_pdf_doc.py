import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#4A5568"))
        
        # Suppress headers/footers on title page
        if self._pageNumber > 1:
            # Header
            self.drawString(54, 750, "PS 26015: SRISHTI-DRISHTI — Technical Master Documentation")
            self.setStrokeColor(colors.HexColor("#CBD5E0"))
            self.setLineWidth(0.5)
            self.line(54, 742, 558, 742)
            
            # Footer
            page_text = f"Page {self._pageNumber} of {page_count}"
            self.drawRightString(558, 36, page_text)
            self.drawString(54, 36, "CONFIDENTIAL — FOR SIH EVALUATION & TECHNICAL AUDIT")
            self.line(54, 48, 558, 48)
            
        self.restoreState()

def build_pdf(filename="PS_26015_SRISHTI_DRISHTI_Technical_Documentation.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    
    # Custom Palette
    PRIMARY = colors.HexColor("#1A365D")   # Deep Navy
    SECONDARY = colors.HexColor("#2B6CB0") # Slate Blue
    ACCENT = colors.HexColor("#2C7A7B")    # Teal Accent
    DARK_TEXT = colors.HexColor("#2D3748") # Charcoal
    LIGHT_BG = colors.HexColor("#F7FAFC")  # Cool Grey
    BORDER_COLOR = colors.HexColor("#E2E8F0")

    # Typography Styles
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=30,
        textColor=PRIMARY,
        alignment=TA_LEFT,
        spaceAfter=10
    )

    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=13,
        leading=17,
        textColor=SECONDARY,
        alignment=TA_LEFT,
        spaceAfter=20
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=PRIMARY,
        spaceBefore=16,
        spaceAfter=8,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=SECONDARY,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=DARK_TEXT,
        alignment=TA_JUSTIFY,
        spaceAfter=8
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-10,
        alignment=TA_LEFT,
        spaceAfter=4
    )

    code_style = ParagraphStyle(
        'Code_Custom',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#1A202C"),
        backColor=colors.HexColor("#EDF2F7"),
        borderColor=BORDER_COLOR,
        borderWidth=0.5,
        borderPadding=6,
        spaceBefore=6,
        spaceAfter=8,
        borderRadius=4
    )

    callout_style = ParagraphStyle(
        'Callout_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#2C5282"),
        backColor=colors.HexColor("#EBF8FF"),
        borderColor=colors.HexColor("#BEE3F8"),
        borderWidth=1,
        borderPadding=8,
        spaceBefore=8,
        spaceAfter=10
    )

    story = []

    # ==================== COVER / TITLE SECTION ====================
    story.append(Spacer(1, 10))
    story.append(Paragraph("SRISHTI-DRISHTI TECHNICAL MASTER SPECIFICATION", title_style))
    story.append(Paragraph("Systematic, Scalable Geospatial Framework for Watershed Monitoring, Remote Sensing Analysis & Geo-Coded Evidence Interpretation", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=PRIMARY, spaceAfter=15))

    # Metadata Block Table
    meta_data = [
        [Paragraph("<b>Problem Statement:</b>", body_style), Paragraph("SIH PS 26015 (Ministry of Rural Development / Land Resources)", body_style)],
        [Paragraph("<b>Core Objective:</b>", body_style), Paragraph("Integration of GIS, Remote Sensing, Geo-tagged Photo Interpretation & Hydrology", body_style)],
        [Paragraph("<b>Target Regions:</b>", body_style), Paragraph("Andhra Pradesh Watershed Districts (WDC-PMKSY 2.0 Schema)", body_style)],
        [Paragraph("<b>Architecture:</b>", body_style), Paragraph("Decoupled Edge Frontend (Vercel) + Async Microservice Backend (Railway)", body_style)],
        [Paragraph("<b>Document Version:</b>", body_style), Paragraph("v2.4 Production Engineering Architecture Specification", body_style)],
        [Paragraph("<b>Date & Build State:</b>", body_style), Paragraph("September 2026 | Verified Scientific Integrity & Provenance Pipeline", body_style)],
    ]
    meta_table = Table(meta_data, colWidths=[130, 374])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), LIGHT_BG),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 15))

    # Executive Callout
    story.append(Paragraph(
        "<b>Executive Directive:</b> This document provides an exhaustive, end-to-end technical specification of the SRISHTI-DRISHTI watershed evidence system. It details the underlying mathematical engines, remote sensing satellites, ML models, data provenance standards, API schemas, and production deployment architecture for Vercel and Railway.",
        callout_style
    ))

    story.append(Spacer(1, 10))

    # ==================== SECTION 1: EXECUTIVE OVERVIEW & PS ALIGNMENT ====================
    story.append(Paragraph("1. System Overview & Problem Statement Alignment", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=SECONDARY, spaceAfter=8))

    story.append(Paragraph(
        "Conventional watershed development programs (such as WDC-PMKSY 2.0) rely on manual field inspections and standalone geo-tagged photos stored primarily as static administrative documentation. This creates a critical operational bottleneck: field photos lack spatial integration with satellite remote sensing, hydrological flow analysis, and historical precipitation baseline data.",
        body_style
    ))
    story.append(Paragraph(
        "The <b>SRISHTI-DRISHTI Framework</b> directly solves PS 26015 by converting isolated geo-coded field evidence into an integrated, multi-layered spatial decision-support system. It combines ground-truth EXIF coordinates, Sentinel-2 10m multispectral satellite imagery, Landsat 8 30m decade-long NDVI time series, IMD grid rainfall baseline, Copernicus 30m DEM hydrological stream extraction, and OpenAI CLIP zero-shot neural visual interpretation.",
        body_style
    ))

    # Feature Alignment Matrix Table
    align_headers = [Paragraph("<b>PS 26015 Requirement</b>", body_style), Paragraph("<b>Implemented Technical Solution</b>", body_style), Paragraph("<b>Scientific / Data Source</b>", body_style)]
    align_rows = [
        align_headers,
        [
            Paragraph("Geo-coded Image Interpretation", body_style),
            Paragraph("EXIF parser + OpenAI CLIP (ViT-B/32) feature similarity + spatial context extraction", body_style),
            Paragraph("Field Photo EXIF + PyTorch CLIP Embeddings", body_style)
        ],
        [
            Paragraph("Land Use & Vegetation Status", body_style),
            Paragraph("Dynamic World 10m LULC classification + Sentinel-2 NDVI surface reflectance", body_style),
            Paragraph("Google Earth Engine (GEE) + Sentinel-2 L2A", body_style)
        ],
        [
            Paragraph("Hydrology & Stream Network", body_style),
            Paragraph("Copernicus DEM D8 flow direction, accumulation, Strahler ordering & sub-watershed delineation", body_style),
            Paragraph("Copernicus DEM GLO-30 (30m)", body_style)
        ],
        [
            Paragraph("Rainfall & Vegetation Trend", body_style),
            Paragraph("RESTREND OLS regression isolating intervention impact from precipitation variability", body_style),
            Paragraph("Landsat 8 NDVI (2014–2024) + IMD 0.25° Grid", body_style)
        ],
        [
            Paragraph("Soil Moisture & Degradation", body_style),
            Paragraph("Sentinel-2 Moisture Index Proxy (SMI/TVDI) + persistent multi-year NDVI slope decay", body_style),
            Paragraph("Sentinel-2 B8A/B11 + Long-term Trend", body_style)
        ],
        [
            Paragraph("Thematic Maps & PDF Evidence", body_style),
            Paragraph("Exportable multi-layer thematic maps & automated PDF Evidence Packets with digital audit trail", body_style),
            Paragraph("ReportLab PDF Engine + Matplotlib", body_style)
        ]
    ]
    align_table = Table(align_rows, colWidths=[125, 225, 154])
    align_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, LIGHT_BG]),
    ]))
    story.append(align_table)
    story.append(Spacer(1, 10))

    # ==================== SECTION 2: END-TO-END SYSTEM ARCHITECTURE ====================
    story.append(Paragraph("2. End-to-End System Architecture & Technology Stack", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=SECONDARY, spaceAfter=8))

    story.append(Paragraph(
        "The platform utilizes a modern, fully decoupled microservice architecture optimized for high performance, interactive 3D map rendering, and robust cloud deployment.",
        body_style
    ))

    # Tech Stack Summary List
    story.append(Paragraph("<b>Frontend Microservice Stack (Target: Vercel):</b>", h2_style))
    story.append(Paragraph("• <b>Framework:</b> Next.js 15+ (App Router) with React 19 and TypeScript for strict type safety.", bullet_style))
    story.append(Paragraph("• <b>Styling & UX:</b> Vanilla CSS & TailwindCSS featuring custom glassmorphism, dark/light themes, and responsive design systems.", bullet_style))
    story.append(Paragraph("• <b>Geospatial Visualization:</b> Mapbox GL JS & Deck.gl for 3D terrain representation (1.8x elevation scale), flow vectors, and satellite tile raster overlays.", bullet_style))
    story.append(Paragraph("• <b>Analytics & UI:</b> Recharts for RESTREND NDVI vs rainfall scatter plots, Lucide Icons, and custom evidence modals.", bullet_style))

    story.append(Paragraph("<b>Backend Microservice Stack (Target: Railway):</b>", h2_style))
    story.append(Paragraph("• <b>Application Server:</b> FastAPI (Python 3.11) with Uvicorn ASGI server for asynchronous request handling.", bullet_style))
    story.append(Paragraph("• <b>Database & ORM:</b> SQLite (development) / PostgreSQL (production) with Async SQLAlchemy and Alembic schema migrations.", bullet_style))
    story.append(Paragraph("• <b>AI & Remote Sensing Pipelines:</b> PyTorch, OpenAI CLIP (ViT-B/32), Earth Engine Python API, Rich Hydrology Engine (Rasterio, RichDEM, SciPy, Shapely).", bullet_style))
    story.append(Paragraph("• <b>Document Generation Engine:</b> ReportLab PDF Engine for dynamic, client-ready evidence packets.", bullet_style))

    story.append(Spacer(1, 8))

    # Architecture Diagram (Code Format)
    arch_diagram = """+-----------------------------------------------------------------------------------+
|                           USER INTERFACE (Next.js / Vercel)                        |
|   Interactive 3D Mapbox  |  Temporal Comparison Slider  |  Evidence Packet Generator |
+-----------------------------------------------------------------------------------+
                                         |  HTTPS REST API / JSON
                                         v
+-----------------------------------------------------------------------------------+
|                           BACKEND CORE (FastAPI / Railway)                        |
|  +-----------------------+  +------------------------+  +----------------------+  |
|  | Geo-Coded Ingestion   |  | Hydrology Engine (D8)  |  | CLIP ML Classifier   |  |
|  | EXIF + Ground Photo   |  | Stream Order + Catchment|  | Zero-Shot Embeddings |  |
|  +-----------------------+  +------------------------+  +----------------------+  |
|  +-----------------------+  +------------------------+  +----------------------+  |
|  | RESTREND Engine       |  | Differential Delta Map |  | ReportLab PDF Builder|  |
|  | OLS NDVI vs Precip    |  | ΔNDVI / ΔNDWI / SMI    |  | Evidence Export      |  |
|  +-----------------------+  +------------------------+  +----------------------+  |
+-----------------------------------------------------------------------------------+
                                         |
     +-----------------------------------+-----------------------------------+
     |                                   |                                   |
     v                                   v                                   v
+-----------------------+     +-----------------------+     +-----------------------+
| SATELLITE & DEM DATA  |     | PRECIPITATION DATA    |     | PERSISTENT DATABASE   |
| Sentinel-2 L2A (10m)  |     | IMD 0.25° Grid        |     | PostgreSQL / SQLite   |
| Landsat 8 L2 (30m)    |     | Open-Meteo Archive    |     | Assets, Photos,       |
| Copernicus DEM (30m)  |     | Historical Records    |     | RESTREND Points       |
+-----------------------+     +-----------------------+     +-----------------------+"""
    story.append(Paragraph(f"<font name='Courier' size=7>{arch_diagram.replace(' ', '&nbsp;').replace('\n', '<br/>')}</font>", code_style))

    story.append(Spacer(1, 10))

    # ==================== SECTION 3: SCIENTIFIC ENGINES & ALGORITHMS ====================
    story.append(Paragraph("3. Detailed Scientific Engines & Mathematical Formulations", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=SECONDARY, spaceAfter=8))

    story.append(Paragraph("3.1 RESTREND (Residual Trend Analysis) Engine", h2_style))
    story.append(Paragraph(
        "To distinguish between vegetation growth caused by natural rainfall fluctuations versus growth induced by human watershed interventions (e.g., check dams, farm ponds), the platform executes <b>RESTREND Analysis</b> over a 10-year period (2014–2024).",
        body_style
    ))
    story.append(Paragraph(
        "<b>Mathematical Formulation:</b><br/>"
        "1. Linear OLS Regression is established between annual peak Landsat-8 NDVI and annual precipitation (P) from IMD gridded data:<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<b>NDVI_predicted = a * P + b</b><br/>"
        "2. The NDVI Residual for each year i is computed as:<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<b>Residual_i = NDVI_actual,i - NDVI_predicted,i</b><br/>"
        "3. Non-parametric Mann-Kendall test or linear trend analysis is performed on the residual time series. A statistically significant <i>positive residual trend</i> (p < 0.05) indicates vegetation improvement exceeding rainfall expectations, validating successful intervention impact.",
        body_style
    ))

    story.append(Paragraph("3.2 D8 Hydrological Drainage & Sub-Watershed Engine", h2_style))
    story.append(Paragraph(
        "Using 30m Copernicus DEM data, the hydrology engine computes accurate stream networks and sub-watershed catchment boundaries:",
        body_style
    ))
    story.append(Paragraph("1. <b>Sink Filling:</b> Depressions in DEM are filled using Planchon-Darboux algorithm to ensure continuous flow direction.", bullet_style))
    story.append(Paragraph("2. <b>D8 Flow Direction:</b> Direction of steepest descent is calculated for each grid cell across 8 neighboring directions.", bullet_style))
    story.append(Paragraph("3. <b>Flow Accumulation:</b> Cumulative number of upstream cells contributing drainage to each cell is accumulated.", bullet_style))
    story.append(Paragraph("4. <b>Strahler Stream Ordering:</b> Streams are extracted above threshold accumulation (e.g., 500 cells) and hierarchically categorized from 1st to 5th order tributaries.", bullet_style))

    story.append(Paragraph("3.3 Quantitative Change Detection & Differential Layers", h2_style))
    story.append(Paragraph(
        "Rather than relying strictly on visual comparison sliders, the backend generates explicit raster differential layers ($\Delta$-layers) between T0 (Pre-intervention) and T1 (Post-intervention) satellite acquisitions:",
        body_style
    ))
    story.append(Paragraph("• <b>Vegetation Index (NDVI):</b> (B8 - B4) / (B8 + B4)", bullet_style))
    story.append(Paragraph("• <b>Water Index (NDWI):</b> (B3 - B8) / (B3 + B8)", bullet_style))
    story.append(Paragraph("• <b>Soil Moisture Index Proxy (SMI / TVDI):</b> Derived from Sentinel-2 B8A and SWIR B11 bands to quantify surface dryness.", bullet_style))
    story.append(Paragraph("• <b>Vegetation Gain/Loss Delta:</b> ΔNDVI = NDVI_post - NDVI_pre (Categorized into Gain > +0.15, Loss < -0.15, Stable).", bullet_style))

    story.append(Spacer(1, 10))

    # ==================== SECTION 4: SCIENTIFIC INTEGRITY & PROVENANCE ====================
    story.append(Paragraph("4. Scientific Guardrails, Data Lineage & Provenance Panel", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=SECONDARY, spaceAfter=8))

    story.append(Paragraph(
        "To withstand rigorous technical evaluation by SIH judges, the platform enforces strict <b>anti-fabrication guardrails</b> and full <b>data provenance transparency</b>.",
        body_style
    ))

    story.append(Paragraph(
        "<b>Core Anti-Fabrication Principles:</b><br/>"
        "• <b>No Synthetic Overwrites:</b> Raw CSV ground facts (coordinates, Drishti ID, project code) are ingested verbatim. Unrecorded attributes are kept as explicit <i>'not_recorded'</i> or <i>NULL</i> rather than inventing artificial values.<br/>"
        "• <b>Calibrated Terminology:</b> CLIP raw output is styled as <i>'Visual Feature Similarity'</i> rather than raw 'probability'. Confidence scores are defined as transparent composite indices: <b>Composite Score = w1 * Visual + w2 * Satellite + w3 * Temporal</b>.<br/>"
        "• <b>Data Provenance Panel (ⓘ Data Sources Modal):</b> Every map layer and chart displays sensor origin, acquisition date, cloud cover %, and EXIF precision.",
        body_style
    ))

    # Provenance Schema Table
    prov_headers = [Paragraph("<b>Data Layer</b>", body_style), Paragraph("<b>Provider / Source</b>", body_style), Paragraph("<b>Spatial Res.</b>", body_style), Paragraph("<b>Acquisition / Quality</b>", body_style)]
    prov_rows = [
        prov_headers,
        [Paragraph("Field Photo", body_style), Paragraph("DRISHTI Mobile App EXIF", body_style), Paragraph("Point", body_style), Paragraph("GPS Precision ±4.2m", body_style)],
        [Paragraph("Satellite Scene", body_style), Paragraph("ESA Sentinel-2 L2A", body_style), Paragraph("10 meters", body_style), Paragraph("Cloud Cover 2.4%", body_style)],
        [Paragraph("Terrain DEM", body_style), Paragraph("Copernicus GLO-30", body_style), Paragraph("30 meters", body_style), Paragraph("Vertical Acc. <4m", body_style)],
        [Paragraph("Rainfall Grid", body_style), Paragraph("IMD / Open-Meteo API", body_style), Paragraph("0.25° Grid", body_style), Paragraph("2014–2024 Daily Archive", body_style)],
        [Paragraph("Land Cover", body_style), Paragraph("Dynamic World LULC", body_style), Paragraph("10 meters", body_style), Paragraph("Composite 2024", body_style)]
    ]
    prov_table = Table(prov_rows, colWidths=[110, 150, 90, 154])
    prov_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), SECONDARY),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, LIGHT_BG]),
    ]))
    story.append(prov_table)

    story.append(Spacer(1, 10))

    # ==================== SECTION 5: DEPLOYMENT ARCHITECTURE ====================
    story.append(Paragraph("5. Production Deployment Architecture (Vercel & Railway)", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=SECONDARY, spaceAfter=8))

    story.append(Paragraph(
        "The project structure is designed for seamless, one-click continuous deployment across <b>Vercel</b> (Frontend) and <b>Railway</b> (Backend).",
        body_style
    ))

    story.append(Paragraph("5.1 Frontend Deployment on Vercel", h2_style))
    story.append(Paragraph(
        "• <b>Build Root Directory:</b> <code>frontend/</code><br/>"
        "• <b>Build Command:</b> <code>npm run build</code><br/>"
        "• <b>Output Directory:</b> <code>.next</code><br/>"
        "• <b>Environment Variables Required:</b><br/>"
        "&nbsp;&nbsp;- <code>NEXT_PUBLIC_API_URL</code> = <i>https://backend-production-xyz.up.railway.app</i><br/>"
        "&nbsp;&nbsp;- <code>NEXT_PUBLIC_MAPBOX_TOKEN</code> = <i>pk.eyJ1...</i>",
        body_style
    ))

    story.append(Paragraph("5.2 Backend Deployment on Railway", h2_style))
    story.append(Paragraph(
        "• <b>Build Root Directory:</b> <code>backend/</code><br/>"
        "• <b>Start Command:</b> <code>uvicorn main:app --host 0.0.0.0 --port $PORT</code><br/>"
        "• <b>Python Version:</b> 3.11 (via Railway Nixpacks / Dockerfile)<br/>"
        "• <b>Environment Variables Required:</b><br/>"
        "&nbsp;&nbsp;- <code>DATABASE_URL</code> = <i>postgresql://...</i> (or SQLite volume)<br/>"
        "&nbsp;&nbsp;- <code>CORS_ORIGINS</code> = <i>https://srishti-drishti.vercel.app</i>",
        body_style
    ))

    story.append(Spacer(1, 10))

    # ==================== SECTION 6: SUMMARY & CONCLUSION ====================
    story.append(Paragraph("6. Conclusion & Verification Summary", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=SECONDARY, spaceAfter=8))

    story.append(Paragraph(
        "The SRISHTI-DRISHTI framework delivers a mathematically sound, scientifically defensible, and fully integrated geospatial monitoring platform for watershed development. By establishing rigorous data provenance, quantitative change detection, RESTREND trend analysis, and zero-shot neural visual interpretation, the platform directly fulfills all requirements of SIH PS 26015 with complete technical transparency.",
        body_style
    ))

    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>End of Engineering Technical Specification Document.</b>", ParagraphStyle('EndDoc', parent=body_style, alignment=TA_CENTER, fontName='Helvetica-Bold', textColor=PRIMARY)))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully built PDF documentation: {filename}")

if __name__ == "__main__":
    build_pdf()
