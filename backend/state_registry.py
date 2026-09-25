"""
All-India 28 States Watershed Registry
Maps State ISO Codes, Bhuvan WMS Thematic Layers, Regional Bounding Boxes, and Ground PDF Repositories.
"""

STATE_REGISTRY = {
    # SOUTH REGION
    "AP": {
        "name": "Andhra Pradesh",
        "region": "South",
        "wms_layer": "lulc:AP_LULC50K_1112",
        "bbox": [76.76, 12.62, 84.76, 19.91],
        "vault_type": "apsac",
        "vault_url": "https://apsac.ap.gov.in/?page_id=5285"
    },
    "TG": {
        "name": "Telangana",
        "region": "South",
        "wms_layer": "lulc:AP_LULC50K_1112",
        "bbox": [77.23, 15.83, 81.32, 19.92],
        "vault_type": "trac",
        "vault_url": "https://trac.telangana.gov.in/"
    },
    "TN": {
        "name": "Tamil Nadu",
        "region": "South",
        "wms_layer": "lulc:TN_LULC50K_1112",
        "bbox": [76.24, 8.08, 80.34, 13.56],
        "vault_type": "tawdeva",
        "vault_url": "https://tawdev.tn.gov.in/"
    },
    "KA": {
        "name": "Karnataka",
        "region": "South",
        "wms_layer": "lulc:KA_LULC50K_1112",
        "bbox": [74.05, 11.59, 78.58, 18.45],
        "vault_type": "ksrsac",
        "vault_url": "https://watershed.karnataka.gov.in/"
    },
    "KL": {
        "name": "Kerala",
        "region": "South",
        "wms_layer": "lulc:KL_LULC50K_1112",
        "bbox": [74.86, 8.29, 77.41, 12.79],
        "vault_type": "ksrec",
        "vault_url": "https://landuseboard.kerala.gov.in/"
    },

    # WEST REGION
    "MH": {
        "name": "Maharashtra",
        "region": "West",
        "wms_layer": "lulc:MH_LULC50K_1112",
        "bbox": [72.63, 15.60, 80.89, 22.02],
        "vault_type": "mrsac",
        "vault_url": "https://www.mrsac.gov.in/"
    },
    "GJ": {
        "name": "Gujarat",
        "region": "West",
        "wms_layer": "lulc:GJ_LULC50K_1112",
        "bbox": [68.10, 20.10, 74.47, 24.71],
        "vault_type": "gswma",
        "vault_url": "https://gswma.gujarat.gov.in/"
    },
    "RJ": {
        "name": "Rajasthan",
        "region": "West",
        "wms_layer": "lulc:RJ_LULC50K_1112",
        "bbox": [69.49, 23.05, 78.27, 30.19],
        "vault_type": "srsac",
        "vault_url": "https://watershed.rajasthan.gov.in/"
    },
    "GA": {
        "name": "Goa",
        "region": "West",
        "wms_layer": "lulc:GA_LULC50K_1112",
        "bbox": [73.67, 14.89, 74.34, 15.80],
        "vault_type": "central",
        "vault_url": "https://wdcpmksy.dolr.gov.in/"
    },

    # NORTH REGION
    "HR": {
        "name": "Haryana",
        "region": "North",
        "wms_layer": "lulc:HR_LULC50K_1112",
        "bbox": [74.45, 27.65, 77.60, 30.92],
        "vault_type": "harsac",
        "vault_url": "http://www.harsac.org/"
    },
    "PB": {
        "name": "Punjab",
        "region": "North",
        "wms_layer": "lulc:PB_LULC50K_1112",
        "bbox": [73.88, 29.53, 76.93, 32.50],
        "vault_type": "prsc",
        "vault_url": "https://prsc.gov.in/"
    },
    "UP": {
        "name": "Uttar Pradesh",
        "region": "North",
        "wms_layer": "lulc:UP_LULC50K_1112",
        "bbox": [77.08, 23.86, 84.64, 30.41],
        "vault_type": "rsacup",
        "vault_url": "http://rsacup.org.in/"
    },
    "HP": {
        "name": "Himachal Pradesh",
        "region": "North",
        "wms_layer": "lulc:HP_LULC50K_1112",
        "bbox": [75.58, 30.38, 79.04, 33.22],
        "vault_type": "himcoste",
        "vault_url": "https://himcoste.hp.gov.in/"
    },
    "UK": {
        "name": "Uttarakhand",
        "region": "North",
        "wms_layer": "lulc:UK_LULC50K_1112",
        "bbox": [77.57, 28.72, 81.04, 31.46],
        "vault_type": "usac",
        "vault_url": "http://wmduk.gov.in/"
    },

    # CENTRAL & EAST REGION
    "MP": {
        "name": "Madhya Pradesh",
        "region": "Central",
        "wms_layer": "lulc:MP_LULC50K_1112",
        "bbox": [74.04, 21.08, 82.80, 26.87],
        "vault_type": "mpcost",
        "vault_url": "http://mpwatershed.nic.in/"
    },
    "CG": {
        "name": "Chhattisgarh",
        "region": "Central",
        "wms_layer": "lulc:CG_LULC50K_1112",
        "bbox": [80.24, 17.78, 84.40, 24.11],
        "vault_type": "cgrsac",
        "vault_url": "https://cgrsac.cg.gov.in/"
    },
    "OD": {
        "name": "Odisha",
        "region": "East",
        "wms_layer": "lulc:OR_LULC50K_1112",
        "bbox": [81.37, 17.81, 87.50, 22.57],
        "vault_type": "orsac",
        "vault_url": "https://watershed.odisha.gov.in/"
    },
    "WB": {
        "name": "West Bengal",
        "region": "East",
        "wms_layer": "lulc:WB_LULC50K_1112",
        "bbox": [85.82, 21.53, 89.88, 27.22],
        "vault_type": "wbrsac",
        "vault_url": "https://wbwrdd.gov.in/"
    },
    "BR": {
        "name": "Bihar",
        "region": "East",
        "wms_layer": "lulc:BR_LULC50K_1112",
        "bbox": [83.32, 24.28, 88.30, 27.52],
        "vault_type": "bic",
        "vault_url": "http://bic.bih.nic.in/"
    },
    "JH": {
        "name": "Jharkhand",
        "region": "East",
        "wms_layer": "lulc:JH_LULC50K_1112",
        "bbox": [83.32, 21.97, 87.95, 25.35],
        "vault_type": "jsac",
        "vault_url": "https://jsac.jharkhand.gov.in/"
    },

    # NORTH-EAST REGION
    "AS": {
        "name": "Assam",
        "region": "North-East",
        "wms_layer": "lulc:AS_LULC50K_1112",
        "bbox": [89.70, 24.13, 96.02, 27.97],
        "vault_type": "astec",
        "vault_url": "https://astec.assam.gov.in/"
    },
    "ML": {
        "name": "Meghalaya",
        "region": "North-East",
        "wms_layer": "lulc:ML_LULC50K_1112",
        "bbox": [89.82, 25.03, 92.80, 26.11],
        "vault_type": "megsoil",
        "vault_url": "https://megsoil.gov.in/"
    },
    "SK": {
        "name": "Sikkim",
        "region": "North-East",
        "wms_layer": "lulc:SK_LULC50K_1112",
        "bbox": [88.06, 27.08, 88.92, 28.13],
        "vault_type": "central",
        "vault_url": "https://wdcpmksy.dolr.gov.in/"
    },
    "TR": {
        "name": "Tripura",
        "region": "North-East",
        "wms_layer": "lulc:TR_LULC50K_1112",
        "bbox": [91.15, 22.94, 92.34, 24.53],
        "vault_type": "central",
        "vault_url": "https://wdcpmksy.dolr.gov.in/"
    },
    "MZ": {
        "name": "Mizoram",
        "region": "North-East",
        "wms_layer": "lulc:MZ_LULC50K_1112",
        "bbox": [92.26, 21.95, 93.43, 24.52],
        "vault_type": "mirsac",
        "vault_url": "https://mirsac.mizoram.gov.in/"
    },
    "MN": {
        "name": "Manipur",
        "region": "North-East",
        "wms_layer": "lulc:MN_LULC50K_1112",
        "bbox": [93.04, 23.83, 94.76, 25.69],
        "vault_type": "marsac",
        "vault_url": "http://marsac.nic.in/"
    },
    "NL": {
        "name": "Nagaland",
        "region": "North-East",
        "wms_layer": "lulc:NL_LULC50K_1112",
        "bbox": [93.33, 25.10, 95.25, 27.04],
        "vault_type": "central",
        "vault_url": "https://landresources.nagaland.gov.in/"
    },
    "AR": {
        "name": "Arunachal Pradesh",
        "region": "North-East",
        "wms_layer": "lulc:AR_LULC50K_1112",
        "bbox": [91.51, 26.65, 97.42, 29.50],
        "vault_type": "srsac",
        "vault_url": "https://srsac.arunachal.gov.in/"
    }
}

# The 6 Core Categories (5 Problem Statement Categories + Negative Controls)
PS_CATEGORIES = [
    "water_conservation_structures",  # Check dams, farm ponds, percolation tanks, gully plugs
    "drainage_conditions",            # Drainage lines, stream order treatments, ridge-to-valley
    "vegetation_changes",             # Horticultural plantations, afforestation, social forestry
    "land_degradation",               # Continuous contour trenches (CCT), bunding, erosion control
    "lulc_changes",                   # Multi-temporal LULC changes, baseline T0 vs evaluation T5
    "negative_non_structure"          # Control class: roads, barren fields, scrubland with no intervention
]

BHUVAN_WMS_ENDPOINT = "https://bhuvan-vec2.nrsc.gov.in/bhuvan/wms"
