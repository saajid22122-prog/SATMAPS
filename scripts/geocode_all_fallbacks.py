import sqlite3
import urllib.request
import urllib.parse
import json
import time
import re

conn = sqlite3.connect("backend/watershed.db")
c = conn.cursor()

rows = c.execute("SELECT id, district, project_id FROM assets WHERE pairing_method = 'district_fallback'").fetchall()
print(f"Total fallback assets to geocode: {len(rows)}")

def clean_location_name(project_id):
    # E.g. ANANTAPURAMU_IWMP-01_BANDLAPALLI -> BANDLAPALLI
    # E.g. CHITTOOR_IWMP_02_T.PASALAVANDLA-PALLE -> T. PASALAVANDLA PALLE
    parts = re.split(r'_|-', project_id)
    # The last meaningful part is the village/mandal name
    loc_parts = []
    found_marker = False
    for p in parts:
        p_clean = p.strip()
        if not p_clean:
            continue
        if "IWMP" in p_clean.upper() or p_clean.isdigit():
            found_marker = True
            continue
        if found_marker:
            loc_parts.append(p_clean)
            
    if not loc_parts:
        loc_parts = [parts[-1]]
        
    loc = " ".join(loc_parts).strip()
    # Normalize common naming variations
    loc = loc.replace("MUDDANAPALLE", "Madanapalle")
    loc = loc.replace("MC PALLE", "Madhavaram")
    loc = loc.replace("T.PASALAVANDLA PALLE", "Pasalavandlapalli")
    loc = loc.replace("M.N.PALLI", "MN Palli")
    loc = loc.replace("J.L.KOTA", "JL Kota")
    loc = re.sub(r'[^a-zA-Z0-9\s]', ' ', loc)
    return re.sub(r'\s+', ' ', loc).strip()

resolved = 0
failed = 0

for asset_id, district, project_id in rows:
    loc_name = clean_location_name(project_id)
    queries = [
        f"{loc_name}, {district}, Andhra Pradesh",
        f"{loc_name}, Andhra Pradesh",
    ]
    
    success = False
    for q in queries:
        url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(q)}&format=json&limit=1"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "IWMPWatershedResolver/2.0 (contact@watershed.gov)"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
                if data:
                    lat = float(data[0]["lat"])
                    lon = float(data[0]["lon"])
                    display = data[0].get("display_name", "")
                    # Sanity check: inside Andhra Pradesh / Rayalaseema bbox [12.5-19.5 N, 76.5-84.5 E]
                    if 12.0 <= lat <= 20.0 and 76.0 <= lon <= 85.0:
                        c.execute("""
                            UPDATE assets 
                            SET latitude = ?, longitude = ?, pairing_method = 'village_geocoded'
                            WHERE id = ?
                        """, (lat, lon, asset_id))
                        conn.commit()
                        print(f"[{asset_id}] {project_id} -> ({lat:.5f}, {lon:.5f}) [{loc_name}]")
                        success = True
                        resolved += 1
                        break
        except Exception as e:
            print(f"Query error for {q}: {e}")
        time.sleep(1.0)
        
    if not success:
        print(f"FAILED to resolve: [{asset_id}] {project_id} ({loc_name})")
        failed += 1

print(f"\nGeocoding complete: {resolved} resolved, {failed} remaining.")
