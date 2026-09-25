import os
import io
import re
import csv
import time
import json
import hashlib
import requests
import numpy as np
import pymupdf
from PIL import Image, ImageStat
from state_registry import STATE_REGISTRY, PS_CATEGORIES, BHUVAN_WMS_ENDPOINT

BASE_DATASET_DIR = "./all_india_watershed_dataset"
MASTER_CSV = "./all_india_watershed_master.csv"
CONTENT_HASH_REGISTRY = "./ground_photo_hash_registry.json"

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}


def load_hash_registry():
    """Maps content-hash -> project_id that first claimed it, persisted across
    pipeline runs so a boilerplate image (state map, org logo, cover page)
    reused in a later PDF is rejected even if it was first seen in an earlier run."""
    if os.path.exists(CONTENT_HASH_REGISTRY):
        with open(CONTENT_HASH_REGISTRY, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_hash_registry(registry):
    with open(CONTENT_HASH_REGISTRY, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)


def content_hash(pil_img):
    return hashlib.md5(pil_img.convert("RGB").tobytes()).hexdigest()


def is_ground_photo_candidate(pil_img):
    """Rejects images that are structurally not a field photograph: maps,
    drawings, scanned text, logos, charts. Low color variance and/or very
    high white-pixel coverage are the signatures of all of these; real field
    photos of watershed structures have natural, high-variance color content.
    Returns (accepted: bool, reason: str)."""
    try:
        arr = np.array(pil_img.convert("RGB"))
    except Exception:
        return False, "unreadable_image"

    h, w, _ = arr.shape
    if w < 200 or h < 200:
        return False, "too_small"

    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    total_px = h * w
    white_px = np.sum((r > 240) & (g > 240) & (b > 240)) / total_px * 100
    color_std = float(np.std(arr))
    gray = np.mean(arr, axis=2)
    edge_density = (np.abs(np.diff(gray, axis=1)).mean() + np.abs(np.diff(gray, axis=0)).mean()) / 2

    # Flat/uniform or line-art content (CAD drawings, logos, scanned text, charts)
    if color_std < 50:
        return False, f"low_color_variance(std={color_std:.1f})"
    # Document / map / text scans: mostly white background with sharp edges
    if white_px > 40 and edge_density > 8:
        return False, f"document_or_map_like(white={white_px:.0f}%,edge={edge_density:.1f})"

    return True, "ok"

def dms_to_decimal(degrees, minutes, seconds, direction):
    decimal = float(degrees) + float(minutes)/60.0 + float(seconds)/3600.0
    if direction in ['S', 'W']:
        decimal = -decimal
    return round(decimal, 6)

def classify_ps_category(text):
    """Classifies text context into one of the 5 Problem Statement categories."""
    t = text.lower()
    
    # Priority 1: Specific water structures
    if any(k in t for k in ['check dam', 'farm pond', 'percolation tank', 'rock fill', 'loose boulder', 'gully plug', 'water harvesting', 'weir', 'anicut', 'subsurface dyke', 'water conservation', 'bandhara']):
        return "water_conservation_structures"
        
    # Priority 2: Drainage & Streamline conditions
    if any(k in t for k in ['drainage line', 'drainage treatment', 'stream order', 'stream bank', 'channel deepening', 'drainage map', 'river basin', 'subbasin', 'nalla']):
        return "drainage_conditions"
        
    # Priority 3: Vegetation & Horticulture
    if any(k in t for k in ['plantation', 'horticulture', 'afforestation', 'social forestry', 'agroforestry', 'biomass', 'pasture', 'canopy']):
        return "vegetation_changes"
        
    # Priority 4: Land degradation & soil conservation
    if any(k in t for k in ['contour trench', 'cct', 'staggered trench', 'bunding', 'contour bund', 'erosion control', 'soil conservation', 'land degradation']):
        return "land_degradation"
        
    # Priority 5: LULC change detection
    if any(k in t for k in ['lulc', 'land use', 'land cover', 'change detection', 't0', 't5', 'thematic map']):
        return "lulc_changes"
        
    return "water_conservation_structures"

def is_valid_satellite_tile(filepath):
    """Evaluates gray-level standard deviation to reject blank/flat tiles.
    StdDev < 3.0 indicates blank canvas with margin anti-aliasing artifacts.
    """
    try:
        with Image.open(filepath) as img:
            gray_img = img.convert("L")
            stat = ImageStat.Stat(gray_img)
            std_dev = stat.stddev[0] if stat.stddev else 0.0
            return (std_dev >= 3.0), std_dev
    except Exception:
        return False, 0.0

def fetch_bhuvan_tile(wms_layer, lat, lon, out_path, max_retries=2):
    """Fetches a 512x512 satellite tile for a coordinate from Bhuvan WMS."""
    offset = 0.0050  # ~500m macro box
    bbox_str = f"{lon-offset},{lat-offset},{lon+offset},{lat+offset}"
    
    params = {
        "SERVICE": "WMS",
        "VERSION": "1.1.1",
        "REQUEST": "GetMap",
        "LAYERS": wms_layer,
        "STYLES": "",
        "SRS": "EPSG:4326",
        "BBOX": bbox_str,
        "WIDTH": "512",
        "HEIGHT": "512",
        "FORMAT": "image/png"
    }
    
    for attempt in range(1, max_retries + 1):
        try:
            res = requests.get(BHUVAN_WMS_ENDPOINT, params=params, headers=HEADERS, timeout=10)
            if res.status_code == 200 and 'image/png' in res.headers.get('Content-Type', ''):
                with open(out_path, "wb") as f:
                    f.write(res.content)
                valid, std_dev = is_valid_satellite_tile(out_path)
                if valid:
                    return True, std_dev
                else:
                    if os.path.exists(out_path):
                        os.remove(out_path)
                    return False, std_dev  # Received valid HTTP response, no need to retry
            time.sleep(1)
        except Exception:
            time.sleep(1)
            
    return False, 0.0

def init_master_catalog():
    if not os.path.exists(MASTER_CSV):
        with open(MASTER_CSV, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "state_code", "state_name", "district", "project_id", 
                "ps_category", "structure_condition", "page_num", "point_idx", "latitude", "longitude",
                "ground_photo_path", "space_tile_path", "pixel_variance_stddev",
                "pairing_method"
            ])

def find_coordinates_in_text(text):
    pts = []
    
    # Pattern 1: Standard DMS with optional seconds
    p1 = r"(\d{1,2})[°\s\ufffd\?\xba\xb0o]+(\d{1,2})(?:[\x27\s\u2019\u2018]+(\d{1,2}(?:\.\d+)?))?[^\dNSEW]*([NSEW])"
    m1 = re.findall(p1, text, re.I)
    cur_lat, cur_lon = None, None
    for deg, mn, sec, direct in m1:
        direct = direct.upper()
        sec_val = float(sec) if sec else 0.0
        dec = float(deg) + float(mn)/60.0 + sec_val/3600.0
        if direct in ['S', 'W']: dec = -dec
        if direct in ['N', 'S']: cur_lat = round(dec, 6)
        elif direct in ['E', 'W']: cur_lon = round(dec, 6)
        if cur_lat is not None and cur_lon is not None:
            if 8.0 <= cur_lat <= 38.0 and 68.0 <= cur_lon <= 98.0:
                pts.append((cur_lat, cur_lon))
            cur_lat, cur_lon = None, None

    # Pattern 2: Degrees only (e.g. 28o N Latitude & 71o E Longitude)
    p2 = r"(\d{1,2})[°\s\ufffd\?\xba\xb0o]+([NS])[^\dNSEW]*(\d{1,2})[°\s\ufffd\?\xba\xb0o]+([EW])"
    for m in re.finditer(p2, text, re.I):
        lat_v = float(m.group(1)) * (-1 if m.group(2).upper() == 'S' else 1)
        lon_v = float(m.group(3)) * (-1 if m.group(4).upper() == 'W' else 1)
        if 8.0 <= lat_v <= 38.0 and 68.0 <= lon_v <= 98.0:
            pts.append((round(lat_v, 6), round(lon_v, 6)))

    # Pattern 3: Decimal degrees (e.g. latitude 25.31 and longitude 92.33)
    p3 = r"lat[a-z\s]*[:=]?\s*(\d{1,2}(?:\.\d+)?)[^\dNSEW]*long[a-z\s]*[:=]?\s*(\d{1,2}(?:\.\d+)?)"
    for m in re.finditer(p3, text, re.I):
        try:
            lat_v = float(m.group(1))
            lon_v = float(m.group(2))
            if 8.0 <= lat_v <= 38.0 and 68.0 <= lon_v <= 98.0:
                pts.append((round(lat_v, 6), round(lon_v, 6)))
        except Exception:
            pass

    # Pattern 4: Decimal degrees with optional degree symbols and N/E notations (e.g. 30.70997364°N, 77.88028827° E or 30.542509° 78.176003°)
    p4 = r"(\d{1,2}\.\d{3,10})[°\s\ufffd\?\xba\xb0o]*([NS])?[,\s\n\r]+(\d{2,3}\.\d{3,10})[°\s\ufffd\?\xba\xb0o]*([EW])?"
    for m in re.finditer(p4, text, re.I):
        try:
            lat_v = float(m.group(1)) * (-1 if m.group(2) and m.group(2).upper() == 'S' else 1)
            lon_v = float(m.group(3)) * (-1 if m.group(4) and m.group(4).upper() == 'W' else 1)
            if 8.0 <= lat_v <= 38.0 and 68.0 <= lon_v <= 98.0:
                pts.append((round(lat_v, 6), round(lon_v, 6)))
        except Exception:
            pass

    return list(dict.fromkeys(pts))

def get_known_dpr_fallback_coords(project_id, state_code):
    pid = project_id.upper()
    if "SHAHJAHANPUR" in pid:
        return [(27.88, 79.91), (27.95, 79.85)]
    if "JABALPUR" in pid:
        return [(23.18, 79.98), (23.25, 80.05)]
    if state_code == "GJ" and ("GIRSOMNATH" in pid or "GIR_SOMNATH" in pid or "GIR SOMNATH" in pid):
        return [(20.90, 70.37), (20.85, 70.45)]
    if "ANGUL" in pid:
        return [(20.84, 85.10), (20.92, 85.02)]
    if "MAHARASHTRA" in pid or "STATE_PLAN" in pid:
        return [(19.99, 73.78), (19.10, 74.74), (19.85, 74.12)]
    if "JODHPUR_II" in pid or "JODHPUR-II" in pid:
        return [(27.13, 72.36)]
    if "JODHPUR" in pid:
        return [(26.28, 73.02), (26.35, 73.10)]
    if "JH_IWMP" in pid or "JAINTIA" in pid:
        return [(25.33, 92.34), (25.35, 92.33)]
    if "PALAR" in pid:
        return [(9.166667, 78.583333), (9.25, 78.666667), (9.34, 78.51)]
    if "NALLAVUR" in pid:
        return [(12.05, 79.80), (12.466667, 80.166667), (11.833333, 79.133333)]
    if "THURINJALAR" in pid:
        return [(12.15, 79.28), (12.25, 79.40), (12.22, 79.07)]
    if "ANANTAPUR" in pid:
        return [(14.68, 77.60), (14.75, 77.65)]
    if "KURNOOL" in pid:
        return [(15.82, 78.03), (15.75, 78.10)]
    if "PRAKASAM" in pid:
        return [(15.50, 80.05), (15.55, 80.10)]
    if "SRIKAKULAM" in pid:
        return [(18.29, 83.89), (18.35, 83.95)]
    if "MALLELA" in pid or "KADAPA" in pid:
        return [(14.47, 78.82), (14.52, 78.85)]
    if "GRAMYA" in pid or "UTTARAKHAND" in pid or state_code == "UK":
        return [(30.53, 77.85), (30.15, 78.78), (30.38, 78.48), (29.60, 79.67), (29.84, 79.77), (29.58, 80.22)]
    return []

def get_clean_district_name(project_id):
    pid = project_id.upper()
    if "SHAHJAHANPUR" in pid: return "Shahjahanpur"
    if "JABALPUR" in pid: return "Jabalpur"
    if "GIRSOMNATH" in pid: return "Gir Somnath"
    if "ANGUL" in pid: return "Angul"
    if "MAHARASHTRA" in pid: return "Nashik"
    if "PALAR" in pid: return "Ramanathapuram"
    if "NALLAVUR" in pid: return "Villupuram"
    if "THURINJALAR" in pid: return "Tiruvannamalai"
    if "JODHPUR" in pid: return "Jodhpur"
    if "JH_IWMP" in pid: return "West Jaintia Hills"
    if "NENMARA" in pid: return "Palakkad"
    if "BHARANIKAVU" in pid: return "Alappuzha"
    if "GRAMYA" in pid or "UTTARAKHAND" in pid: return "Dehradun / Garhwal"
    parts = project_id.split("_")
    return parts[0] if parts else "Unknown"

def process_state(state_code):
    """Processes all PDFs for a state into categorized ground + space pairs."""
    if state_code not in STATE_REGISTRY:
        print(f"[-] State {state_code} not registered.", flush=True)
        return
        
    state_info = STATE_REGISTRY[state_code]
    pdf_dir = os.path.join(BASE_DATASET_DIR, state_code, "pdfs")
    
    if not os.path.exists(pdf_dir):
        print(f"[-] No PDFs directory found for {state_code} at {pdf_dir}", flush=True)
        return
        
    pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith(".pdf")]
    if not pdf_files:
        print(f"[-] No PDF files to process in {pdf_dir}", flush=True)
        return
        
    init_master_catalog()

    existing_pairs = set()
    if os.path.exists(MASTER_CSV):
        with open(MASTER_CSV, mode="r", encoding="utf-8") as f:
            reader = csv.reader(f)
            _ = next(reader, None)
            for r in reader:
                if len(r) >= 11:
                    existing_pairs.add((r[9], r[10]))  # (ground_photo_path, space_tile_path)

    hash_registry = load_hash_registry()

    print(f"\n=======================================================", flush=True)
    print(f"[!] EXECUTING PIPELINE FOR: {state_info['name']} ({state_code})", flush=True)
    print(f"    Available PDFs: {len(pdf_files)}", flush=True)
    print(f"    Target WMS Layer: {state_info['wms_layer']}", flush=True)
    print(f"=======================================================", flush=True)

    for pdf_name in pdf_files:
        pdf_path = os.path.join(pdf_dir, pdf_name)
        project_id = os.path.splitext(pdf_name)[0]
        district = get_clean_district_name(project_id)
        
        try:
            doc = pymupdf.open(pdf_path)
        except Exception as e:
            print(f"[-] Error opening {pdf_name}: {e}", flush=True)
            continue
            
        print(f"\n -> Scanning Document: {pdf_name} ({len(doc)} pages)", flush=True)
        
        all_coords = []
        all_photos = []
        had_same_page_pair = False
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            ps_cat = classify_ps_category(text)
            
            # Extract coordinates with vertical position from text blocks
            coord_points_with_y = []
            for b in page.get_text('blocks'):
                pts = find_coordinates_in_text(b[4])
                if pts:
                    y_c = (b[1] + b[3]) / 2.0
                    for pt in pts:
                        coord_points_with_y.append((pt[0], pt[1], y_c))
            
            # Filter coordinates within state bounding box and deduplicate
            min_lon, min_lat, max_lon, max_lat = state_info['bbox']
            coord_points = []
            seen_pts = set()
            for lat, lon, yc in coord_points_with_y:
                if (lat, lon) not in seen_pts:
                    if (min_lat - 0.2) <= lat <= (max_lat + 0.2) and (min_lon - 0.2) <= lon <= (max_lon + 0.2):
                        coord_points.append((lat, lon, yc))
                        seen_pts.add((lat, lon))

            # Extract images on this page (cap at 8 per page)
            image_list = page.get_images(full=True)
            if len(image_list) > 8:
                image_list = image_list[:8]
                
            page_photos = []
            for img_idx, img_meta in enumerate(image_list):
                xref = img_meta[0]
                try:
                    rects = page.get_image_rects(xref)
                    y_center = (rects[0].y0 + rects[0].y1) / 2.0 if rects else 0.0
                    base_img = doc.extract_image(xref)
                    img_bytes = base_img["image"]
                    pil_img = Image.open(io.BytesIO(img_bytes))
                    w, h = pil_img.size
                    if w <= 150 or h <= 150:
                        continue

                    accepted, reason = is_ground_photo_candidate(pil_img)
                    if not accepted:
                        print(f"    [skip] {pdf_name} p{page_num} i{img_idx}: rejected ({reason})", flush=True)
                        continue

                    chash = content_hash(pil_img)
                    claimed_by = hash_registry.get(chash)
                    if claimed_by is not None and claimed_by != project_id:
                        print(f"    [skip] {pdf_name} p{page_num} i{img_idx}: duplicate image content "
                              f"already used by project '{claimed_by}'", flush=True)
                        continue
                    hash_registry[chash] = project_id

                    page_photos.append((pil_img, img_idx, page_num, ps_cat, y_center))
                except Exception:
                    pass
                    
            if coord_points:
                all_coords.extend([(lat, lon, page_num, ps_cat) for lat, lon, _ in coord_points])
            if page_photos:
                all_photos.extend([(p, i, pn, c) for p, i, pn, c, _ in page_photos])
                
            # Same-page 1-to-1 proximity pairing (prevents Cartesian product)
            if coord_points and page_photos:
                had_same_page_pair = True
                ground_dir = os.path.join(BASE_DATASET_DIR, state_code, ps_cat, "ground_photos")
                space_dir = os.path.join(BASE_DATASET_DIR, state_code, ps_cat, "space_tiles")
                os.makedirs(ground_dir, exist_ok=True)
                os.makedirs(space_dir, exist_ok=True)
                
                # Pair each photo to its vertically closest coordinate on the page
                for pil_img, img_idx, p_num, _, img_y in page_photos:
                    closest_pt_idx, (lat, lon, _) = min(
                        enumerate(coord_points), 
                        key=lambda item: abs(item[1][2] - img_y)
                    )
                    
                    g_name = f"ground_{project_id}_p{p_num}_i{img_idx}.png"
                    g_path = os.path.join(ground_dir, g_name)
                    pil_img.save(g_path)
                    
                    space_filename = f"space_{project_id}_p{page_num}_pt{closest_pt_idx}.png"
                    space_filepath = os.path.join(space_dir, space_filename)
                    
                    rel_g = os.path.relpath(g_path, ".")
                    rel_s = os.path.relpath(space_filepath, ".")
                    
                    if (rel_g, rel_s) in existing_pairs:
                        continue
                        
                    if os.path.exists(space_filepath) and os.path.getsize(space_filepath) > 1000:
                        success, std_dev = is_valid_satellite_tile(space_filepath)
                    else:
                        print(f"    [+] Page {page_num} (Pt {closest_pt_idx}): Fetching Bhuvan tile for {ps_cat} at ({lat}, {lon})", flush=True)
                        success, std_dev = fetch_bhuvan_tile(state_info['wms_layer'], lat, lon, space_filepath)
                        time.sleep(0.5)
                        
                    if success:
                        print(f"        -> [Space Tile Verified] StdDev: {std_dev:.2f} -> {space_filename}", flush=True)
                        # Determine condition label from text
                        txt_low = text.lower()
                        if 'proposed weir' in txt_low or 'proposed site' in txt_low:
                            s_cond = 'proposed_pre_construction'
                        elif 't1' in txt_low:
                            s_cond = 'functional_post_treatment'
                        elif 't0' in txt_low:
                            s_cond = 'baseline_pre_treatment'
                        else:
                            s_cond = 'unspecified'

                        with open(MASTER_CSV, mode="a", newline="", encoding="utf-8") as f:
                            writer = csv.writer(f)
                            writer.writerow([
                                state_code, state_info['name'], district, project_id,
                                ps_cat, s_cond, page_num, closest_pt_idx, lat, lon,
                                rel_g, rel_s, round(std_dev, 2), "same_page"
                            ])
                        existing_pairs.add((rel_g, rel_s))
                                
        # Fallback for documents with coordinate tables in text and photos in appendix
        if not had_same_page_pair and all_photos:
            target_coords = all_coords
            if not target_coords:
                fallback_pts = get_known_dpr_fallback_coords(project_id, state_code)
                target_coords = [(lat, lon, 0, "water_conservation_structures") for lat, lon in fallback_pts]
                
            if target_coords:
                min_lon, min_lat, max_lon, max_lat = state_info['bbox']
                target_coords = [
                    pt for pt in target_coords 
                    if (min_lat - 0.05) <= pt[0] <= (max_lat + 0.05) and (min_lon - 0.05) <= pt[1] <= (max_lon + 0.05)
                ]
                print(f"    [*] Document-level pairing: Found {len(target_coords)} valid coordinates and {len(all_photos)} photos", flush=True)
                for c_idx, (lat, lon, c_page, c_cat) in enumerate(target_coords[:min(len(target_coords), len(all_photos), 8)]):
                    pil_img, img_idx, p_num, _ = all_photos[c_idx % len(all_photos)]
                    ground_dir = os.path.join(BASE_DATASET_DIR, state_code, c_cat, "ground_photos")
                    space_dir = os.path.join(BASE_DATASET_DIR, state_code, c_cat, "space_tiles")
                    os.makedirs(ground_dir, exist_ok=True)
                    os.makedirs(space_dir, exist_ok=True)
                    
                    g_name = f"ground_{project_id}_p{p_num}_i{img_idx}.png"
                    g_path = os.path.join(ground_dir, g_name)
                    pil_img.save(g_path)
                    
                    space_filename = f"space_{project_id}_coord{c_idx}.png"
                    space_filepath = os.path.join(space_dir, space_filename)
                    
                    rel_g = os.path.relpath(g_path, ".")
                    rel_s = os.path.relpath(space_filepath, ".")
                    
                    if (rel_g, rel_s) in existing_pairs:
                        continue
                        
                    if os.path.exists(space_filepath) and os.path.getsize(space_filepath) > 1000:
                        success, std_dev = is_valid_satellite_tile(space_filepath)
                    else:
                        print(f"    [+] Document Pt {c_idx}: Fetching Bhuvan tile for {c_cat} at ({lat}, {lon})", flush=True)
                        success, std_dev = fetch_bhuvan_tile(state_info['wms_layer'], lat, lon, space_filepath)
                        time.sleep(0.5)
                        
                    if success:
                        print(f"        -> [Space Tile Verified] StdDev: {std_dev:.2f} -> {space_filename}", flush=True)
                        with open(MASTER_CSV, mode="a", newline="", encoding="utf-8") as f:
                            writer = csv.writer(f)
                            writer.writerow([
                                state_code, state_info['name'], district, project_id,
                                c_cat, "unspecified", p_num, c_idx, lat, lon,
                                rel_g, rel_s, round(std_dev, 2), "document_fallback"
                            ])
                        existing_pairs.add((rel_g, rel_s))

    save_hash_registry(hash_registry)
    print(f"\n[Success] Processing complete for {state_info['name']}. Master catalog updated at: {MASTER_CSV}", flush=True)

if __name__ == "__main__":
    # Ingest Central, North, West, and East states
    for st in ["MH", "MP", "UP", "GJ", "OD"]:
        process_state(st)
