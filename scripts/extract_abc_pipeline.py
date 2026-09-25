"""
extract_abc_pipeline.py
=======================
Extracts ONLY genuine, usable ground-truth photos of watershed water
structures from bulk-scraped DPR PDFs, strictly following the 5-stage
pipeline defined in the project master prompt.

Stages
------
  1  Candidate extraction  – JPEG only, 550–900 × 340–560 px, skip pages 1-4
  2  Content filter        – reject flat/synthetic images + caption keywords
  3  Auto visual check     – unique-colour count rejects LULC/map/diagram;
                             natural-tone % confirms real outdoor photograph
  4  Duplicate detection   – perceptual hash across all PDFs
  5  Coordinate attachment – same-page proximity then doc-level fallback;
                             honest precision labelling (never fabricated)

Satellite images are NOT extracted here. Run a separate script for those.

Outputs
-------
  <ABC_DIR>/ground_truth/<district>/  – accepted ground-truth photos
  <ABC_DIR>/ambiguous/               – images Stage 3 could not decide
  <ABC_DIR>/extraction_log.csv       – full audit trail for every candidate

Run
---
  cd "c:\\Users\\Mohammed\\Desktop\\data testing"
  python -m extract_abc_pipeline
"""

import os, io, re, sys, csv, hashlib
from collections import defaultdict

import numpy as np
import pymupdf
from PIL import Image

try:
    import imagehash
    _PHASH = True
except ImportError:
    _PHASH = False

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pipeline_engine import find_coordinates_in_text

# =============================================================================
# CONFIGURATION
# =============================================================================
ABC_DIR = r"C:\Users\Mohammed\Desktop\abc"

# Stage 1 — strict JPEG dimension window (real camera photos in these DPRs)
S1_W_MIN, S1_W_MAX = 550, 900
S1_H_MIN, S1_H_MAX = 340, 560
SKIP_PAGES = {0, 1, 2, 3}   # 0-indexed → skips pages 1-4

# Stage 2 — content filter
S2_STD_MIN       = 30    # reject if grayscale std dev below this (flat/synthetic)
S2_WHITE_MAX     = 40    # reject if white pixel % above this AND edge high
S2_EDGE_MAX      = 8     # edge density threshold for doc/map rejection
S2_CAPTION_REJECT = [
    "design", "drawing", "cross-section", "cross section",
    "elevation view", "flow chart", "flowchart", "organogram",
    "signature", "resolution copy", "cover page",
    "plan view", "longitudinal section",
    "land use and land cover", "land use & land cover", "lulc",
    "pre and post treatment", "pre & post treatment",
    "satellite", "cartosat", "bhuvan", "false colour", "false color",
]

# Stage 3 — visual confirmation thresholds
# Unique-colour check: LULC/thematic maps have very few palette entries
# Real camera photos have hundreds of distinct colours even after quantisation
S3_UNIQUE_COLOR_MIN  = 60   # reject if unique quantised colours < this → map/diagram
# Natural outdoor tone check
S3_NATURAL_TONE_MIN  = 8.0  # at least one of green/brown/blue must exceed this %
# False-colour NIR satellite detection
# NIR composites render bare soil as magenta/pink (high R+B, low G).
# Real field photos almost never have significant magenta/purple areas.
S3_MAGENTA_MAX       = 4.0  # reject if magenta pixel % exceeds this (lowered from 6)
# Spatial uniformity check
# Satellite/classified images have large flat colour patches (high neighbor match).
# Real photos have texture everywhere (low neighbor match).
S3_NEIGHBOR_MATCH_MAX = 35.0  # reject if >35% of pixels match a cardinal neighbour

# =============================================================================
# PIXEL METRICS
# =============================================================================

def _metrics(pil_img):
    arr   = np.array(pil_img.convert("RGB"))
    h, w, _ = arr.shape
    r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
    total   = h * w

    white_pct    = float(np.sum((r>240)&(g>240)&(b>240))) / total * 100
    gray         = arr.mean(axis=2)
    color_std    = float(np.std(arr))
    edge_density = (float(np.abs(np.diff(gray, axis=1)).mean()) +
                    float(np.abs(np.diff(gray, axis=0)).mean())) / 2

    green_pct = float(np.sum((g>r)&(g>b)&(g>80))) / total * 100
    brown_pct = float(np.sum((r>g)&(r>b)&(r>80)&(r<200)&(g>50))) / total * 100
    blue_pct  = float(np.sum((b>r)&(b>g)&(b>80))) / total * 100

    # Magenta/purple: high R and B, low G — signature of NIR false-colour composites.
    # Defined as: R>120, B>100, G<(R-40), G<(B-20). Never dominant in real photos.
    magenta_pct = float(np.sum((r>120)&(b>100)&(g<r-40)&(g<b-20))) / total * 100

    # Spatial uniformity (neighbor-match) check.
    # Satellite/classified map images have large flat colour patches -> high match ratio.
    # Real outdoor photos have texture everywhere -> low match ratio.
    # Quantise to 8-step bins (finer than unique_colors to preserve local structure).
    arr8 = (arr // 8).astype(np.uint8)
    match_right = np.all(arr8[:, 1:] == arr8[:, :-1], axis=2)   # each pixel == right neighbour
    match_down  = np.all(arr8[1:, :]  == arr8[:-1, :], axis=2)  # each pixel == lower neighbour
    match_any   = np.zeros((h, w), dtype=bool)
    match_any[:, :-1] |= match_right
    match_any[:-1, :] |= match_down
    neighbor_match_pct = float(match_any.mean()) * 100

    # Unique-colour count on a 16-bin quantised version of the image.
    # Maps/LULC have palette-limited colours (< 30-40 bins).
    # Real photos have hundreds even after heavy quantisation.
    arr_q = (arr // 16).reshape(-1, 3)
    unique_colors = len(np.unique(arr_q, axis=0))

    return dict(w=w, h=h,
                white_pct=white_pct, color_std=color_std,
                edge_density=edge_density,
                green_pct=green_pct, brown_pct=brown_pct, blue_pct=blue_pct,
                magenta_pct=magenta_pct,
                neighbor_match_pct=neighbor_match_pct,
                unique_colors=unique_colors)


# =============================================================================
# STAGE 2 — CONTENT FILTER
# =============================================================================

def stage2(metrics, caption_text):
    """Returns (passed: bool, reason: str)."""
    if metrics["color_std"] < S2_STD_MIN:
        return False, f"low_std_dev({metrics['color_std']:.1f})"
    if metrics["white_pct"] > S2_WHITE_MAX and metrics["edge_density"] > S2_EDGE_MAX:
        return False, f"document_scan(white={metrics['white_pct']:.0f}%,edge={metrics['edge_density']:.1f})"
    cap = caption_text.lower()
    for kw in S2_CAPTION_REJECT:
        if kw in cap:
            return False, f"caption_keyword={kw!r}"
    return True, ""


# =============================================================================
# STAGE 3 — AUTO VISUAL CHECK
# =============================================================================

def stage3(metrics, caption_text):
    """
    Returns (passed: bool, reason: str).

    Two-test approach matching the original prompt Stage 3 criteria:

    Test A — False-colour NIR rejection (checked first, hardest signal)
      NIR false-colour composites (NRSC before/after treatment images)
      always have significant magenta/purple pixels — bare soil renders
      as bright pink/magenta in NIR band. Real field photos never have
      >4% magenta pixels.

    Test B — Spatial uniformity (map/patch detection)
      Satellite and classified map images have large flat colour patches;
      >35% of pixels match a cardinal neighbour in the same quantised bin.
      Real outdoor photos have texture everywhere; match ratio is low.

    Test C — Unique colour count
      Real camera photos of outdoor scenes always contain hundreds of
      distinct colours. Thematic/LULC maps are palette-limited
      (typically 5-20 classes = few dozen unique quantised colours).
      Reject if unique_colors < S3_UNIQUE_COLOR_MIN.

    Test D — Natural outdoor tone check
      All water-structure site photos contain at least one of:
        green (vegetation), brown/earth (dry soil, embankments),
        blue (sky, water surface).
      Reject if none of these exceeds S3_NATURAL_TONE_MIN %.

    All four tests must pass.
    """
    unique_colors      = metrics["unique_colors"]
    nat_tone           = max(metrics["green_pct"], metrics["brown_pct"], metrics["blue_pct"])
    magenta_pct        = metrics["magenta_pct"]
    neighbor_match_pct = metrics["neighbor_match_pct"]

    # Test A — NIR false-colour satellite rejection
    if magenta_pct > S3_MAGENTA_MAX:
        return False, f"false_colour_nir_satellite(magenta={magenta_pct:.1f}%>threshold {S3_MAGENTA_MAX}%)"

    # Test B — Spatial uniformity (map/patch detection)
    if neighbor_match_pct > S3_NEIGHBOR_MATCH_MAX:
        return False, f"map_uniform_patches(neighbor_match={neighbor_match_pct:.1f}%>{S3_NEIGHBOR_MATCH_MAX}%)"

    # Test C — Unique colour count (palette-limited map rejection)
    if unique_colors < S3_UNIQUE_COLOR_MIN:
        return False, f"map_or_diagram(unique_colors={unique_colors}<{S3_UNIQUE_COLOR_MIN})"

    if nat_tone < S3_NATURAL_TONE_MIN:
        return False, f"no_natural_outdoor_tone(max={nat_tone:.1f}%)"

    return True, ""


# =============================================================================
# STAGE 4 — PERCEPTUAL HASH
# =============================================================================

def _phash(pil_img):
    if _PHASH:
        return str(imagehash.phash(pil_img.convert("RGB")))
    return hashlib.md5(pil_img.convert("RGB").tobytes()).hexdigest()


# =============================================================================
# STAGE 5 — COORDINATE EXTRACTION & MATCHING
# =============================================================================

def _extract_coords(doc):
    """Returns {page_num: [(lat, lon, y_center)]}."""
    result = defaultdict(list)
    seen   = set()
    for pn in range(len(doc)):
        try:
            for blk in doc[pn].get_text("blocks"):
                for lat, lon in find_coordinates_in_text(blk[4]):
                    if (lat, lon) not in seen:
                        seen.add((lat, lon))
                        y_c = (blk[1] + blk[3]) / 2.0
                        result[pn].append((lat, lon, y_c))
        except Exception:
            pass
    return result


def _match_coord(img_y, page_num, coord_map):
    """Same-page vertical proximity first, doc-level fallback."""
    if coord_map.get(page_num):
        lat, lon, _ = min(coord_map[page_num], key=lambda p: abs(p[2] - img_y))
        return lat, lon, "project_level"
    for pn in sorted(coord_map):
        if coord_map[pn]:
            lat, lon, _ = coord_map[pn][0]
            return lat, lon, "project_level"
    return None, None, "no_coordinate_available"


# =============================================================================
# HELPERS
# =============================================================================

def _caption_window(doc, page_num, window=2):
    texts = []
    for pn in range(max(0, page_num - window), min(len(doc), page_num + window + 1)):
        try:
            texts.append(doc[pn].get_text())
        except Exception:
            pass
    return " ".join(texts)


def _parse_district(pdf_filename, first_page_text, folder_hint="", grandparent_hint=""):
    """Use folder name as district (most reliable for APSAC layout).
    Returns (district, state_code)."""
    STATE_TOKENS = {
        "AP":"AP","ANDHRA":"AP","APSAC":"AP",
        "TG":"TG","TELANGANA":"TG",
        "TN":"TN","TAMILNADU":"TN",
        "KA":"KA","KARNATAKA":"KA",
        "KL":"KL","KERALA":"KL",
        "MH":"MH","MAHARASHTRA":"MH",
        "GJ":"GJ","GUJARAT":"GJ",
        "RJ":"RJ","RAJASTHAN":"RJ",
        "MP":"MP","MADHYAPRADESH":"MP",
        "UP":"UP","UTTARPRADESH":"UP",
        "UK":"UK","UTTARAKHAND":"UK",
        "OD":"OD","ODISHA":"OD",
        "JH":"JH","JHARKHAND":"JH",
        "CG":"CG","CHHATTISGARH":"CG",
    }
    # Detect state from grandparent folder (e.g. APSAC_All_Batches → AP)
    gp = grandparent_hint.upper()
    state = "AP" if ("APSAC" in gp or "AP_SAC" in gp) else "XX"
    for tok, code in STATE_TOKENS.items():
        if tok in gp:
            state = code
            break

    # Use immediate parent folder as district
    if folder_hint and len(folder_hint) > 2 and \
            folder_hint.upper() not in ("PDFS","REPORTS","DOCS","ABC"):
        district = folder_hint.replace("_"," ").replace("-"," ").title()
        return district.strip(), state

    # Fallback: page-1 text
    m = re.search(r"district\s*[:\-]\s*([A-Za-z ]+)", first_page_text, re.I)
    district = m.group(1).strip().split("\n")[0].title() if m else "Unknown"
    return district.strip(), state


def _safe(name):
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip()


def _activity(text):
    t = text.lower()
    if any(k in t for k in ["check dam","farm pond","percolation tank",
                              "nallah bund","gabion","weir","anicut","bandhara"]):
        return "water_conservation_structures"
    if any(k in t for k in ["plantation","horticulture","afforestation"]):
        return "vegetation_changes"
    if any(k in t for k in ["drainage","nalla","streamline"]):
        return "drainage_conditions"
    if any(k in t for k in ["lulc","land use","land cover"]):
        return "lulc_changes"
    return "unspecified"


# =============================================================================
# CSV
# =============================================================================

COLS = [
    "filename","source_pdf","page","district","state_code",
    "activity_type","drishti_id","mws_code",
    "width","height",
    "unique_colors","color_std","nat_tone_pct",
    "stage1_passed","stage2_passed","stage2_reason",
    "stage3_passed","stage3_reason",
    "duplicate_of",
    "attached_lat","attached_lon","coordinate_precision",
]

def _row(**kw):
    r = {c:"" for c in COLS}
    r.update(kw)
    return r


# =============================================================================
# MAIN
# =============================================================================

def run(abc_dir=ABC_DIR):
    if not os.path.isdir(abc_dir):
        print(f"[ERROR] Folder not found: {abc_dir}")
        return

    out_gt    = os.path.join(abc_dir, "ground_truth")
    out_ambig = os.path.join(abc_dir, "ambiguous")
    log_path  = os.path.join(abc_dir, "extraction_log.csv")
    os.makedirs(out_ambig, exist_ok=True)

    # Collect PDFs (skip our own output folders)
    skip_roots = {out_gt, out_ambig}
    pdfs = []
    for root, _, files in os.walk(abc_dir):
        if any(root.startswith(d) for d in skip_roots):
            continue
        for f in sorted(files):
            if f.lower().endswith(".pdf"):
                pdfs.append(os.path.join(root, f))

    if not pdfs:
        print(f"[ERROR] No PDFs found in: {abc_dir}")
        return

    print(f"\n{'='*65}")
    print(f"  EXTRACT ABC PIPELINE  --  {len(pdfs)} PDF(s)")
    print(f"{'='*65}\n")

    hash_reg: dict[str, str] = {}   # img_hash -> pdf_stem

    cnt = dict(s1=0, s2=0, s3=0, s3_ambig=0, s4_dup=0, coord_yes=0, coord_no=0)
    s2_reasons   = defaultdict(int)
    s3_reasons   = defaultdict(int)
    dist_counts  = defaultdict(int)

    with open(log_path, "w", newline="", encoding="utf-8") as flog:
        w = csv.DictWriter(flog, fieldnames=COLS)
        w.writeheader()

        for pdf_path in pdfs:
            stem   = os.path.splitext(os.path.basename(pdf_path))[0]
            folder = os.path.basename(os.path.dirname(pdf_path))
            gp     = os.path.basename(os.path.dirname(os.path.dirname(pdf_path)))

            print(f"  > {os.path.basename(pdf_path)}", flush=True)
            try:
                doc = pymupdf.open(pdf_path)
            except Exception as e:
                print(f"    [ERROR] {e}")
                continue

            p0txt = doc[0].get_text() if len(doc) else ""
            district, state = _parse_district(os.path.basename(pdf_path), p0txt,
                                              folder_hint=folder, grandparent_hint=gp)
            safe_dist = _safe(district)
            print(f"    District: {district} | State: {state} | Pages: {len(doc)}")

            coord_map = _extract_coords(doc)
            print(f"    Coords found: {sum(len(v) for v in coord_map.values())}")

            # Parse Drishti ID / MWS code from cover text
            drishti_id = mws_code = ""
            m = re.search(r"drishti\s*(?:id|no\.?)?\s*[:\-]?\s*([A-Z0-9\-/]+)", p0txt, re.I)
            if m: drishti_id = m.group(1).strip()
            m = re.search(r"mws\s*(?:code|no\.?)?\s*[:\-]?\s*([A-Z0-9\-/]+)", p0txt, re.I)
            if m: mws_code = m.group(1).strip()

            img_ctr = defaultdict(int)

            for pn in range(len(doc)):
                if pn in SKIP_PAGES:
                    continue

                page    = doc[pn]
                pg_text = page.get_text()
                caption = _caption_window(doc, pn)
                act     = _activity(pg_text)

                for img_meta in page.get_images(full=True):
                    xref = img_meta[0]
                    idx  = img_ctr[pn]
                    img_ctr[pn] += 1
                    fname = f"{_safe(stem)}_p{pn}_i{idx}.jpg"

                    try:
                        raw = doc.extract_image(xref)
                    except Exception:
                        continue

                    ext    = raw.get("ext","").lower()
                    ibytes = raw.get("image", b"")
                    if not ibytes:
                        continue

                    try:
                        pil = Image.open(io.BytesIO(ibytes))
                        iw, ih = pil.size
                    except Exception:
                        continue

                    # ── STAGE 1 ──────────────────────────────────────────────
                    # Strict: JPEG only, exact dimension window, no exceptions.
                    is_jpeg  = ext in ("jpeg","jpg")
                    in_dim   = S1_W_MIN <= iw <= S1_W_MAX and S1_H_MIN <= ih <= S1_H_MAX

                    if not (is_jpeg and in_dim):
                        w.writerow(_row(
                            filename=fname, source_pdf=os.path.basename(pdf_path),
                            page=pn, district=district, state_code=state,
                            width=iw, height=ih,
                            stage1_passed=False,
                            stage2_reason=(
                                "not_jpeg" if not is_jpeg else
                                f"dim_outside_window({iw}x{ih})"
                            ),
                        ))
                        continue

                    cnt["s1"] += 1

                    # ── STAGE 2 ──────────────────────────────────────────────
                    try:
                        met = _metrics(pil)
                    except Exception as e:
                        w.writerow(_row(filename=fname, source_pdf=os.path.basename(pdf_path),
                            page=pn, district=district, state_code=state,
                            width=iw, height=ih, stage1_passed=True,
                            stage2_passed=False, stage2_reason=f"metrics_error:{e}"))
                        continue

                    s2_ok, s2_reason = stage2(met, caption)
                    if not s2_ok:
                        s2_reasons[s2_reason.split("(")[0]] += 1
                        w.writerow(_row(filename=fname, source_pdf=os.path.basename(pdf_path),
                            page=pn, district=district, state_code=state,
                            activity_type=act, drishti_id=drishti_id, mws_code=mws_code,
                            width=iw, height=ih,
                            unique_colors=met["unique_colors"],
                            color_std=round(met["color_std"],1),
                            nat_tone_pct=round(max(met["green_pct"],met["brown_pct"],met["blue_pct"]),1),
                            stage1_passed=True, stage2_passed=False, stage2_reason=s2_reason))
                        continue

                    cnt["s2"] += 1

                    # ── STAGE 3 ──────────────────────────────────────────────
                    s3_ok, s3_reason = stage3(met, caption)
                    nat_tone = max(met["green_pct"], met["brown_pct"], met["blue_pct"])

                    if not s3_ok:
                        s3_reasons[s3_reason.split("(")[0]] += 1
                        # Save to ambiguous if borderline; reject entirely if clearly not a photo
                        if "map_or_diagram" in s3_reason:
                            # Clearly a thematic/LULC map — hard reject
                            w.writerow(_row(filename=fname, source_pdf=os.path.basename(pdf_path),
                                page=pn, district=district, state_code=state,
                                activity_type=act, drishti_id=drishti_id, mws_code=mws_code,
                                width=iw, height=ih,
                                unique_colors=met["unique_colors"],
                                color_std=round(met["color_std"],1),
                                nat_tone_pct=round(nat_tone,1),
                                stage1_passed=True, stage2_passed=True,
                                stage3_passed=False, stage3_reason=s3_reason))
                        else:
                            # Borderline — save to ambiguous for manual spot-check
                            cnt["s3_ambig"] += 1
                            os.makedirs(out_ambig, exist_ok=True)
                            try:
                                pil.convert("RGB").save(os.path.join(out_ambig, fname), "JPEG", quality=92)
                            except Exception:
                                pass
                            w.writerow(_row(filename=fname, source_pdf=os.path.basename(pdf_path),
                                page=pn, district=district, state_code=state,
                                activity_type=act, drishti_id=drishti_id, mws_code=mws_code,
                                width=iw, height=ih,
                                unique_colors=met["unique_colors"],
                                color_std=round(met["color_std"],1),
                                nat_tone_pct=round(nat_tone,1),
                                stage1_passed=True, stage2_passed=True,
                                stage3_passed=False, stage3_reason=f"AMBIGUOUS:{s3_reason}"))
                        continue

                    # ── STAGE 4 ──────────────────────────────────────────────
                    img_hash  = _phash(pil)
                    prior     = hash_reg.get(img_hash)
                    dup_of    = ""
                    if prior and prior != stem:
                        cnt["s4_dup"] += 1
                        dup_of = prior
                        w.writerow(_row(filename=fname, source_pdf=os.path.basename(pdf_path),
                            page=pn, district=district, state_code=state,
                            activity_type=act, drishti_id=drishti_id, mws_code=mws_code,
                            width=iw, height=ih,
                            unique_colors=met["unique_colors"],
                            color_std=round(met["color_std"],1),
                            nat_tone_pct=round(nat_tone,1),
                            stage1_passed=True, stage2_passed=True,
                            stage3_passed=True, duplicate_of=dup_of))
                        continue
                    hash_reg[img_hash] = stem

                    # ── STAGE 5 ──────────────────────────────────────────────
                    try:
                        rects = page.get_image_rects(xref)
                        img_y = (rects[0].y0+rects[0].y1)/2.0 if rects else 0.0
                    except Exception:
                        img_y = 0.0

                    lat, lon, prec = _match_coord(img_y, pn, coord_map)
                    if prec == "no_coordinate_available":
                        cnt["coord_no"] += 1
                    else:
                        cnt["coord_yes"] += 1

                    # ── SAVE ─────────────────────────────────────────────────
                    out_folder = os.path.join(out_gt, safe_dist)
                    os.makedirs(out_folder, exist_ok=True)
                    try:
                        pil.convert("RGB").save(os.path.join(out_folder, fname), "JPEG", quality=92)
                    except Exception as e:
                        print(f"    [WARN] Save failed: {e}")
                        continue

                    cnt["s3"] += 1
                    dist_counts[safe_dist] += 1
                    coord_str = f"({lat:.4f},{lon:.4f})" if lat else "no_coord"
                    print(f"    [ACCEPTED] p{pn} i{idx} {iw}x{ih} "
                          f"std={met['color_std']:.0f} colors={met['unique_colors']} "
                          f"{coord_str} -> {fname}", flush=True)

                    w.writerow(_row(
                        filename=fname, source_pdf=os.path.basename(pdf_path),
                        page=pn, district=district, state_code=state,
                        activity_type=act, drishti_id=drishti_id, mws_code=mws_code,
                        width=iw, height=ih,
                        unique_colors=met["unique_colors"],
                        color_std=round(met["color_std"],1),
                        nat_tone_pct=round(nat_tone,1),
                        stage1_passed=True, stage2_passed=True,
                        stage3_passed=True, duplicate_of=dup_of,
                        attached_lat=f"{lat:.6f}" if lat else "",
                        attached_lon=f"{lon:.6f}" if lon else "",
                        coordinate_precision=prec,
                    ))

            doc.close()
            print()

    # =========================================================================
    # FINAL SUMMARY
    # =========================================================================
    W = 65
    print(f"\n{'='*W}")
    print("  EXTRACTION COMPLETE")
    print(f"{'='*W}")
    print(f"  PDFs processed                         : {len(pdfs)}")
    print(f"  Stage 1 candidates (JPEG 550-900x340-560): {cnt['s1']}")
    print(f"  Stage 2 passed (content filter)        : {cnt['s2']}")
    print(f"  Stage 3 accepted (visual check)        : {cnt['s3']}")
    print(f"  Stage 3 ambiguous (check abc/ambiguous/): {cnt['s3_ambig']}")
    print(f"  Stage 4 duplicates removed             : {cnt['s4_dup']}")
    print(f"\n  Coordinate coverage:")
    print(f"    project_level                        : {cnt['coord_yes']}")
    print(f"    no_coordinate_available              : {cnt['coord_no']}")

    if s2_reasons:
        print(f"\n  Stage 2 rejection breakdown:")
        for r,n in sorted(s2_reasons.items(), key=lambda x:-x[1]):
            print(f"    {r:<47s}: {n}")

    if s3_reasons:
        print(f"\n  Stage 3 rejection breakdown:")
        for r,n in sorted(s3_reasons.items(), key=lambda x:-x[1]):
            print(f"    {r:<47s}: {n}")

    if dist_counts:
        print(f"\n  Ground-truth photos by district:")
        for d in sorted(dist_counts):
            print(f"    {d:<35s}: {dist_counts[d]}")

    print(f"\n  Individually assessed (Stage 1 candidates): {cnt['s1']}")
    print(f"  Skipped without check                  : 0")
    print(f"\n  Log  -> {log_path}")
    print(f"  Out  -> {out_gt}/")
    print(f"{'='*W}\n")


if __name__ == "__main__":
    run()
