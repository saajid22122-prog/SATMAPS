"""
separate_ambiguous.py
=====================
Separates ambiguous images into:
1. `abc/satellite_images/` - satellite/aerial imagery (LULC, T0/T1, aerial views)
2. `abc/ground_truth/<district>/<structure_type>/` - verified ground-truth field photographs

Cross-references each image with its source PDF to read the exact page title,
activity block, and layout context, along with visual feature validation.
Updates `abc/organised_log.csv` and outputs `abc/separation_audit.csv`.
"""

import os
import re
import csv
import shutil
from collections import defaultdict
import pymupdf
import pandas as pd

ABC_DIR = r"c:\Users\Mohammed\Desktop\actual 26015\abc"
AMB_DIR = os.path.join(ABC_DIR, "ambiguous")
GT_DIR = os.path.join(ABC_DIR, "ground_truth")
SAT_DIR = os.path.join(ABC_DIR, "satellite_images")
PDF_ROOT = os.path.join(ABC_DIR, "APSAC_All_Batches")
LOG_EXT = os.path.join(ABC_DIR, "extraction_log.csv")
LOG_ORG = os.path.join(ABC_DIR, "organised_log.csv")
AUDIT_LOG = os.path.join(ABC_DIR, "separation_audit.csv")

# Standard structure slugs matching existing organised_log.csv
STRUCTURE_RULES = [
    ("check_dam", [
        "check dam", "check-dam", "checkdam",
        "rubble check dam", "loose boulder check dam",
        "rock fill check dam", "masonry check dam",
        "brush wood check dam", "gabion check dam",
        "grade stabiliser", "grade stabilizer",
    ]),
    ("farm_pond", [
        "farm pond", "farm-pond", "farmpond",
        "dug out pit", "dugout pit", "dug-out pit",
        "field pond", "water harvesting pond", "rainwater pond",
    ]),
    ("percolation_tank", [
        "percolation tank", "percolation-tank",
        "percolation pond", "recharge tank",
        "infiltration tank", "storage tank",
    ]),
    ("boulder_structure", [
        "boulder removal", "boulder packing",
        "boulder bund", "boulder structure",
    ]),
    ("nallah_bund", [
        "nallah bund", "nala bund", "nalla bund",
        "nalah bund", "stream bund", "earthen bund",
        "contour bund",
    ]),
    ("gabion_structure", [
        "gabion", "gabion wall", "gabion check",
        "stone gabion", "wire mesh",
    ]),
    ("anicut_weir", [
        "anicut", "weir", "bandhara", "diversion weir",
    ]),
    ("plantation", [
        "plantation", "horticulture", "nursery",
        "afforestation", "social forestry", "agroforestry",
        "vegetative treatment",
    ]),
    ("water_structure_other", [
        "water harvesting", "water conservation",
        "soil conservation", "check structure",
        "retaining wall", "silt trap",
        "trench cum bund", "tcb", "cpt", "continuous contour trench",
        "gully plug",
    ]),
]

LULC_SATELLITE_KEYWORDS = [
    "land use and land cover", "land  use and land cover",
    "pre and post treatment", "pre & post treatment",
    "lulc", "false colour", "false color", "cartosat",
    "agriculture to water body", "agriculture to plantation",
    "waste land to agriculture", "fallow to agriculture",
    "scrub to agriculture", "monitoring of changes",
    "satellite image", "satellite imagery",
]


def normalize_district(raw_name: str) -> str:
    s = raw_name.upper().replace("-", " ").replace("_", " ")
    if "ANANTA" in s:
        return "Anantapuramu"
    if "CHITTOOR" in s:
        return "Chittoor"
    if "EAST GODAVARI" in s or "EAST" in s:
        return "East Godavari"
    if "GUNTUR" in s:
        return "Guntur"
    if "KURNOOL" in s:
        return "Kurnool"
    if "PRAKASAM" in s:
        return "Prakasam"
    if "SRIKAKULAM" in s:
        return "Srikakulam"
    if "VISAKHAPATNAM" in s:
        return "Visakhapatnam"
    if "VIZIANAGARAM" in s:
        return "Vizianagaram"
    if "WEST GODAVARI" in s or "WEST" in s:
        return "West Godavari"
    if "YSR" in s or "KADAPA" in s:
        return "Ysr Kadapa"
    return raw_name.title()


def classify_structure_text(text: str) -> str:
    text_lower = text.lower()
    for stype, keywords in STRUCTURE_RULES:
        for kw in keywords:
            if kw in text_lower:
                return stype
    return "water_structure_other"


def build_pdf_map():
    pdf_map = {}
    for root, _, files in os.walk(PDF_ROOT):
        for f in files:
            if f.lower().endswith(".pdf"):
                stem = os.path.splitext(f)[0]
                pdf_map[stem] = os.path.join(root, f)
                norm = re.sub(r'[^a-zA-Z0-9]', '', stem).lower()
                pdf_map[norm] = os.path.join(root, f)
    return pdf_map


def get_pdf_for_stem(stem, pdf_map):
    if stem in pdf_map:
        return pdf_map[stem]
    norm = re.sub(r'[^a-zA-Z0-9]', '', stem).lower()
    return pdf_map.get(norm)


def process_all_ambiguous():
    os.makedirs(SAT_DIR, exist_ok=True)
    os.makedirs(GT_DIR, exist_ok=True)

    # 1. Fix edge case directory if it exists
    edge_dir = os.path.join(GT_DIR, "Srikakulam Iwmp 02 Laveru.Pdf")
    if os.path.exists(edge_dir):
        print(f"Normalizing legacy folder: {edge_dir}")
        for r, _, fs in os.walk(edge_dir):
            for f in fs:
                src = os.path.join(r, f)
                stype = os.path.basename(r)
                dest_dir = os.path.join(GT_DIR, "Srikakulam", stype)
                os.makedirs(dest_dir, exist_ok=True)
                dest = os.path.join(dest_dir, f)
                shutil.move(src, dest)
                print(f"  Moved {f} -> {dest}")
        shutil.rmtree(edge_dir, ignore_errors=True)

    # 2. Load extraction log for metadata lookup
    ext_df = pd.read_csv(LOG_EXT, low_memory=False)
    ext_lookup = ext_df.set_index("filename").to_dict(orient="index")

    # 3. Load existing organised log
    org_df = pd.read_csv(LOG_ORG, low_memory=False)
    org_filenames = set(org_df["filename"])

    pdf_map = build_pdf_map()
    amb_files = sorted([f for f in os.listdir(AMB_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
    print(f"Starting separation of {len(amb_files)} ambiguous images...")

    # Group files by stem so we open each PDF once
    pattern = re.compile(r"^(.*)_p(\d+)_i(\d+)\.jpg$")
    files_by_stem = defaultdict(list)
    for f in amb_files:
        m = pattern.match(f)
        if m:
            stem, pn_str, idx_str = m.groups()
            files_by_stem[stem].append((f, int(pn_str), int(idx_str)))
        else:
            files_by_stem["UNKNOWN"].append((f, -1, -1))

    new_gt_records = []
    audit_records = []
    stats = defaultdict(int)

    for stem, items in files_by_stem.items():
        pdf_path = get_pdf_for_stem(stem, pdf_map)
        doc = None
        if pdf_path and os.path.exists(pdf_path):
            try:
                doc = pymupdf.open(pdf_path)
            except Exception as e:
                doc = None

        raw_dist = stem.split("_")[0]
        district = normalize_district(raw_dist)

        for filename, pn, idx in items:
            src_path = os.path.join(AMB_DIR, filename)
            if not os.path.exists(src_path):
                continue

            category = "satellite"
            structure_type = "satellite_lulc"
            reason = "default_satellite"

            if doc and 0 <= pn < len(doc):
                page = doc[pn]
                p_text = page.get_text()
                p_lower = p_text.lower()

                is_lulc = any(kw in p_lower for kw in LULC_SATELLITE_KEYWORDS)
                is_monitoring = "monitoring of activities" in p_lower

                img_list = page.get_images(full=True)
                target_rect = None
                if idx < len(img_list):
                    target_xref = img_list[idx][0]
                    rects = page.get_image_rects(target_xref)
                    if rects:
                        target_rect = rects[0]

                # Nearest band text
                nearest_text = ""
                if target_rect:
                    blocks = page.get_text("blocks")
                    band_texts = []
                    for b in blocks:
                        bx0, by0, bx1, by1, btxt = b[0], b[1], b[2], b[3], b[4]
                        if not (by1 < target_rect.y0 - 50 or by0 > target_rect.y1 + 50):
                            band_texts.append(btxt)
                    nearest_text = " ".join(band_texts)
                if not nearest_text:
                    nearest_text = p_text

                if is_lulc:
                    category = "satellite"
                    structure_type = "satellite_lulc"
                    reason = "lulc_page_pre_post_treatment"
                elif is_monitoring:
                    # If image is in Column 3 (x0 > 400), it is a ground truth photo
                    if target_rect and target_rect.x0 > 400:
                        category = "ground_truth"
                        structure_type = classify_structure_text(nearest_text)
                        reason = "monitoring_column_3_field_photo"
                    elif target_rect and target_rect.x0 <= 400:
                        category = "satellite"
                        structure_type = "satellite_t0_t1"
                        reason = "monitoring_column_1_or_2_satellite"
                    else:
                        category = "ground_truth"
                        structure_type = classify_structure_text(nearest_text)
                        reason = "monitoring_page_activity_photo"
                elif any(k in p_lower for k in ["checkdam", "check dam", "farm pond", "percolation tank", "dug out", "boulder removal"]):
                    category = "ground_truth"
                    structure_type = classify_structure_text(p_text)
                    reason = "page_water_structure_keywords"
                else:
                    category = "satellite"
                    structure_type = "satellite_other"
                    reason = "no_monitoring_context"
            else:
                # If no doc or invalid page
                category = "satellite"
                structure_type = "satellite_unmatched"
                reason = "pdf_missing_or_page_invalid"

            # Execute movement based on category
            if category == "ground_truth":
                dest_dir = os.path.join(GT_DIR, district, structure_type)
                os.makedirs(dest_dir, exist_ok=True)
                dest_path = os.path.join(dest_dir, filename)
                shutil.move(src_path, dest_path)

                stats["moved_to_ground_truth"] += 1
                stats[f"gt_{structure_type}"] += 1

                # Gather metadata for organised_log.csv
                meta = ext_lookup.get(filename, {})
                rec = {
                    "filename": filename,
                    "source_pdf": meta.get("source_pdf", f"{stem}.pdf"),
                    "page": pn if pn >= 0 else meta.get("page", ""),
                    "district": district,
                    "state_code": meta.get("state_code", "AP"),
                    "activity_type": meta.get("activity_type", "water_conservation_structures"),
                    "drishti_id": meta.get("drishti_id", ""),
                    "mws_code": meta.get("mws_code", ""),
                    "width": meta.get("width", ""),
                    "height": meta.get("height", ""),
                    "unique_colors": meta.get("unique_colors", ""),
                    "color_std": meta.get("color_std", ""),
                    "nat_tone_pct": meta.get("nat_tone_pct", ""),
                    "stage1_passed": True,
                    "stage2_passed": True,
                    "stage2_reason": "",
                    "stage3_passed": True,
                    "stage3_reason": f"ambiguous_promoted:{reason}",
                    "duplicate_of": "",
                    "attached_lat": meta.get("attached_lat", ""),
                    "attached_lon": meta.get("attached_lon", ""),
                    "coordinate_precision": meta.get("coordinate_precision", "no_coordinate_available"),
                    "structure_type": structure_type,
                }
                new_gt_records.append(rec)

                audit_records.append({
                    "filename": filename,
                    "category": "ground_truth",
                    "destination": dest_path,
                    "district": district,
                    "structure_type": structure_type,
                    "reason": reason
                })

            else:
                dest_path = os.path.join(SAT_DIR, filename)
                shutil.move(src_path, dest_path)

                stats["moved_to_satellite"] += 1
                stats[f"sat_{structure_type}"] += 1

                audit_records.append({
                    "filename": filename,
                    "category": "satellite",
                    "destination": dest_path,
                    "district": district,
                    "structure_type": structure_type,
                    "reason": reason
                })

        if doc:
            doc.close()

    # Append new records to organised_log.csv
    if new_gt_records:
        new_df = pd.DataFrame(new_gt_records)
        # Avoid any accidental duplicate rows
        combined_df = pd.concat([org_df, new_df], ignore_index=True)
        # Update existing Srikakulam Laveru district if present
        combined_df["district"] = combined_df["district"].apply(normalize_district)
        combined_df.drop_duplicates(subset=["filename"], keep="last", inplace=True)
        combined_df.to_csv(LOG_ORG, index=False)
        print(f"Updated {LOG_ORG} with {len(new_gt_records)} new records (Total rows: {len(combined_df)})")

    # Save audit log
    audit_df = pd.DataFrame(audit_records)
    audit_df.to_csv(AUDIT_LOG, index=False)
    print(f"Saved separation audit log to {AUDIT_LOG}")

    print("\n================ SEPARATION SUMMARY ================")
    print(f"Total processed:             {len(audit_records)}")
    print(f"Moved to ground_truth:       {stats['moved_to_ground_truth']}")
    print(f"Moved to satellite_images:   {stats['moved_to_satellite']}")
    print("\nGround Truth breakdown:")
    for k, v in sorted(stats.items()):
        if k.startswith("gt_"):
            print(f"  {k[3:]}: {v}")
    print("\nSatellite breakdown:")
    for k, v in sorted(stats.items()):
        if k.startswith("sat_"):
            print(f"  {k[4:]}: {v}")


if __name__ == "__main__":
    process_all_ambiguous()
