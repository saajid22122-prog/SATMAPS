"""
organise_by_structure.py
========================
Post-processing step: reads extraction_log.csv produced by extract_abc_pipeline.py,
opens each source PDF, scans the page where each ground-truth photo was found,
and re-organises (copies) images into structure-type subfolders:

  abc/ground_truth/<district>/check_dam/
  abc/ground_truth/<district>/farm_pond/
  abc/ground_truth/<district>/percolation_tank/
  abc/ground_truth/<district>/nallah_bund/
  abc/ground_truth/<district>/gabion_structure/
  abc/ground_truth/<district>/water_structure_other/
  abc/ground_truth/<district>/non_water_structure/   <- plantation, horticulture, etc.

Also writes abc/organised_log.csv with a new `structure_type` column.

Run AFTER extract_abc_pipeline.py has finished:
  cd "c:\\Users\\Mohammed\\Desktop\\data testing"
  python -m organise_by_structure
"""

import os, csv, re, shutil
from collections import defaultdict

import pymupdf

# ──────────────────────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────────────────────
ABC_DIR     = r"C:\Users\Mohammed\Desktop\abc"
PDF_ROOT    = os.path.join(ABC_DIR, "APSAC_All_Batches")   # root that contains district folders
LOG_IN      = os.path.join(ABC_DIR, "extraction_log.csv")
LOG_OUT     = os.path.join(ABC_DIR, "organised_log.csv")
GT_DIR      = os.path.join(ABC_DIR, "ground_truth")

# ──────────────────────────────────────────────────────────────────────────────
# STRUCTURE-TYPE KEYWORD RULES
# Priority order matters: more specific matches are checked first.
# Each rule: (structure_type_slug, [keyword_list])
# ──────────────────────────────────────────────────────────────────────────────
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
        "field pond", "percolation pond",
        "rain water harvesting pond", "rainwater pond",
    ]),
    ("percolation_tank", [
        "percolation tank", "percolation-tank",
        "percolation pond", "recharge tank",
        "infiltration tank", "storage tank",
    ]),
    ("nallah_bund", [
        "nallah bund", "nala bund", "nalla bund",
        "nalah bund", "nallah check",
        "stream bund", "earthen bund", "earthen check",
        "loose rock fill bund", "staggered trench",
        "contour bund",
    ]),
    ("gabion_structure", [
        "gabion", "gabion wall", "gabion check",
        "wire mesh", "stone gabion",
        "gabion weir", "gabion dam",
    ]),
    ("anicut_weir", [
        "anicut", "weir", "bandhara",
        "diversion weir", "drop weir",
        "subsurface dyke", "subsurface dam",
        "underground dyke",
    ]),
    # Catch-all for other water-retaining / soil-conservation structures
    ("water_structure_other", [
        "water harvesting", "water conservation",
        "soil conservation", "check structure",
        "retaining wall", "silt trap",
        "trench cum bund", "tcb",
        "cpt", "continuous contour trench",
        "gully plug", "boulder packing",
    ]),
    # Non-water-structure categories that slipped past Stage 3
    ("plantation", [
        "plantation", "horticulture", "nursery",
        "afforestation", "social forestry", "agroforestry",
        "vegetative treatment",
    ]),
    ("livelihood", [
        "livelihood", "self help group", "shg",
        "income generation", "training",
    ]),
]


def classify_structure(page_text: str, window_text: str = "") -> str:
    """
    Classify structure type from page text (and ±1-page window for context).
    Returns the structure_type slug.
    """
    combined = (page_text + " " + window_text).lower()
    for slug, keywords in STRUCTURE_RULES:
        for kw in keywords:
            if kw in combined:
                return slug
    return "water_structure_other"   # conservative default for water-structure PDFs


def _safe(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip()


def find_pdf(source_pdf_basename: str, district: str) -> str | None:
    """
    Locate the source PDF on disk.
    Searches: PDF_ROOT/<district>/<file>, PDF_ROOT/<any folder>/<file>
    """
    # Try district folder first
    candidate = os.path.join(PDF_ROOT, district, source_pdf_basename)
    if os.path.exists(candidate):
        return candidate
    # Walk all subdirs of PDF_ROOT
    for root, _, files in os.walk(PDF_ROOT):
        if source_pdf_basename in files:
            return os.path.join(root, source_pdf_basename)
    return None


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

def run():
    if not os.path.exists(LOG_IN):
        print(f"[ERROR] extraction_log.csv not found at: {LOG_IN}")
        print("        Run extract_abc_pipeline.py first.")
        return

    with open(LOG_IN, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Only process rows that were fully accepted (stage3_passed=True, no duplicate)
    accepted = [
        r for r in rows
        if str(r.get("stage3_passed", "")).strip().lower() in ("true", "1")
        and not r.get("duplicate_of", "").strip()
    ]

    print(f"\n{'='*65}")
    print(f"  ORGANISE BY STRUCTURE TYPE")
    print(f"{'='*65}")
    print(f"  Total rows in log          : {len(rows)}")
    print(f"  Accepted ground-truth rows : {len(accepted)}")
    print()

    # Cache open PDFs to avoid re-opening for every image on the same PDF
    pdf_cache: dict[str, pymupdf.Document] = {}
    out_rows = []
    type_counts: dict[str, int] = defaultdict(int)
    missing_pdf = 0
    errors = 0

    for row in accepted:
        src_pdf   = row.get("source_pdf", "")
        district  = row.get("district", "Unknown")
        filename  = row.get("filename", "")
        page_num  = int(row.get("page", 0))

        if not filename or not src_pdf:
            continue

        # Find and open the source PDF
        pdf_path = find_pdf(src_pdf, _safe(district))
        if pdf_path is None:
            # Try the district folder name variants
            for variant in [district, district.upper(), district.replace(" ", "_")]:
                pdf_path = find_pdf(src_pdf, variant)
                if pdf_path:
                    break

        if pdf_path is None:
            print(f"  [WARN] PDF not found: {src_pdf}")
            missing_pdf += 1
            struct_type = "water_structure_other"
        else:
            if pdf_path not in pdf_cache:
                try:
                    pdf_cache[pdf_path] = pymupdf.open(pdf_path)
                except Exception as e:
                    print(f"  [WARN] Cannot open {src_pdf}: {e}")
                    pdf_cache[pdf_path] = None

            doc = pdf_cache[pdf_path]
            if doc is None:
                struct_type = "water_structure_other"
            else:
                try:
                    # Get text from the image page + ±1 page for context
                    pages_to_read = list(range(max(0, page_num-1), min(len(doc), page_num+2)))
                    page_text     = doc[page_num].get_text() if page_num < len(doc) else ""
                    window_texts  = []
                    for pn in pages_to_read:
                        if pn != page_num and pn < len(doc):
                            window_texts.append(doc[pn].get_text())
                    struct_type = classify_structure(page_text, " ".join(window_texts))
                except Exception as e:
                    errors += 1
                    struct_type = "water_structure_other"

        # Source image path
        safe_dist   = _safe(district)
        src_img     = os.path.join(GT_DIR, safe_dist, filename)

        if not os.path.exists(src_img):
            # Maybe image is directly under ground_truth/<district>/ — already handled
            # Try searching
            found = False
            for root, _, files in os.walk(GT_DIR):
                if filename in files:
                    src_img = os.path.join(root, filename)
                    found = True
                    break
            if not found:
                print(f"  [WARN] Image not found on disk: {filename}")
                continue

        # Copy to structure-type subfolder
        dst_folder = os.path.join(GT_DIR, safe_dist, struct_type)
        os.makedirs(dst_folder, exist_ok=True)
        dst_img = os.path.join(dst_folder, filename)

        if os.path.abspath(src_img) != os.path.abspath(dst_img):
            try:
                shutil.move(src_img, dst_img)
            except Exception as e:
                print(f"  [WARN] Move failed for {filename}: {e}")
                errors += 1
                continue

        type_counts[struct_type] += 1
        out_row = dict(row)
        out_row["structure_type"] = struct_type
        out_rows.append(out_row)

        print(f"  [{struct_type:<25s}] {district:<20s} {filename}", flush=True)

    # Close cached PDFs
    for doc in pdf_cache.values():
        if doc:
            try:
                doc.close()
            except Exception:
                pass

    # Write organised log
    if out_rows:
        fieldnames = list(rows[0].keys()) + ["structure_type"]
        with open(LOG_OUT, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            w.writeheader()
            w.writerows(out_rows)

    # ──────────────────────────────────────────────────────────────────────────
    # SUMMARY
    # ──────────────────────────────────────────────────────────────────────────
    print(f"\n{'='*65}")
    print("  ORGANISATION COMPLETE")
    print(f"{'='*65}")
    print(f"  Images organised           : {sum(type_counts.values())}")
    print(f"  PDFs not found             : {missing_pdf}")
    print(f"  Errors                     : {errors}")
    print(f"\n  By structure type:")
    for stype in [
        "check_dam","farm_pond","percolation_tank","nallah_bund",
        "gabion_structure","anicut_weir","water_structure_other",
        "plantation","livelihood"
    ]:
        n = type_counts.get(stype, 0)
        if n:
            print(f"    {stype:<30s}: {n}")
    print(f"\n  Organised log -> {LOG_OUT}")
    print(f"  Images in    -> {GT_DIR}/<district>/<structure_type>/")
    print(f"{'='*65}\n")
    print("  NOTE: Original flat copies in abc/ground_truth/<district>/ are kept.")
    print("        The structure-type subfolders contain additional sorted copies.")


if __name__ == "__main__":
    run()
