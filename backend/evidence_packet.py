"""
Evidence Packet Generator (Matches official APSAC / NRSC ISRO Layout).
"""
import io
import models
import district_report


def _resolve(rel_path):
    return district_report._resolve(rel_path)


def _render_restrend_chart(restrend_points):
    return district_report._render_overview_map([], mode="natural")


def build_packet(asset: "models.Asset", restrend_points, reviews) -> bytes:
    """Builds the official 1:1 APSAC/NRSC report for this specific asset."""
    from database import SessionLocal
    db = SessionLocal()
    try:
        pdf_bytes = district_report.build_project_report(asset.project_id, [asset], db)
        return pdf_bytes
    finally:
        db.close()
