import numpy as np
import rasterio
import csv
from pathlib import Path
import warnings
from rasterio.errors import NotGeoreferencedWarning

warnings.filterwarnings("ignore", category=NotGeoreferencedWarning)

INPUT_CSV = "custom_kenya_parcels.csv"
DATA_DIR = Path("kenya_dataset/data")
REGIONS = ["0", "1", "2", "3"]
DATES = [
    "20190606", "20190701", "20190706", "20190711", "20190721",
    "20190805", "20190815", "20190825", "20190909", "20190919",
    "20190924", "20191004", "20191103"
]

PATCH_SIZE = 5
HALF_PATCH = PATCH_SIZE // 2

parcels_metadata = {}
with open(INPUT_CSV, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        reg = row["region"]
        fid = int(row["field_id"])
        if reg not in parcels_metadata:
            parcels_metadata[reg] = {}
        parcels_metadata[reg][fid] = {
            "is_maize": int(row["is_maize"]),
            "split": row["split"]
        }

for region in REGIONS:
    print(f"Extracting image patches for Region {region}...")
    
    field_id_path = DATA_DIR / region / f"{region}_field_id.tif"
    if not field_id_path.exists():
        continue
        
    with rasterio.open(field_id_path) as src:
        field_mask = src.read(1)
        
    field_centroids = {}
    for fid in parcels_metadata[region].keys():
        pixels = (field_mask == fid)
        if np.any(pixels):
            y_coords, x_coords = np.where(pixels)
            cy = int(np.mean(y_coords))
            cx = int(np.mean(x_coords))
            field_centroids[fid] = (cy, cx)
            
    num_fields = len(field_centroids)
    if num_fields == 0:
        continue
        
    # הקצאת זיכרון מראש לכל הגזירים כדי להימנע מהגדלת רשימות דינמית
    field_patches = {fid: np.zeros((len(DATES), 3, PATCH_SIZE, PATCH_SIZE), dtype=np.float32) for fid in field_centroids.keys()}
    
    # לולאת התאריכים נמצאת כעת בחוץ - פותחים כל מפה רק פעם אחת!
    for d_idx, date_str in enumerate(DATES):
        b4_path = DATA_DIR / region / date_str / f"{region}_B04_{date_str}.tif"
        b8_path = DATA_DIR / region / date_str / f"{region}_B08_{date_str}.tif"
        b11_path = DATA_DIR / region / date_str / f"{region}_B11_{date_str}.tif"
        
        if not (b4_path.exists() and b8_path.exists() and b11_path.exists()):
            continue
            
        print(f"  Loading date {date_str} into RAM...")
        with rasterio.open(b4_path) as src4, rasterio.open(b8_path) as src8, rasterio.open(b11_path) as src11:
            red = src4.read(1)
            nir = src8.read(1)
            swir = src11.read(1)
            
        # גזירת כל השדות מתוך המפה שכבר נמצאת בזיכרון המהיר
        for fid, (cy, cx) in field_centroids.items():
            for c_idx, band in enumerate([red, nir, swir]):
                y_min = max(0, cy - HALF_PATCH)
                y_max = min(band.shape[0], cy + HALF_PATCH + 1)
                x_min = max(0, cx - HALF_PATCH)
                x_max = min(band.shape[1], cx + HALF_PATCH + 1)
                
                patch = band[y_min:y_max, x_min:x_max]
                
                pad_y_before = max(0, -(cy - HALF_PATCH))
                pad_y_after = max(0, (cy + HALF_PATCH + 1) - band.shape[0])
                pad_x_before = max(0, -(cx - HALF_PATCH))
                pad_x_after = max(0, (cx + HALF_PATCH + 1) - band.shape[1])
                
                if pad_y_before > 0 or pad_y_after > 0 or pad_x_before > 0 or pad_x_after > 0:
                    patch = np.pad(patch, ((pad_y_before, pad_y_after), (pad_x_before, pad_x_after)), mode='reflect')
                    
                field_patches[fid][d_idx, c_idx, :, :] = patch
                
    X_data = []
    y_data = []
    field_ids = []
    
    for fid in field_centroids.keys():
        X_data.append(field_patches[fid])
        y_data.append(parcels_metadata[region][fid]["is_maize"])
        field_ids.append(fid)
        
    out_file = f"patches_region_{region}.npz"
    np.savez_compressed(
        out_file, 
        X=np.array(X_data), 
        y=np.array(y_data), 
        field_ids=np.array(field_ids)
    )
    print(f"  -> Saved {len(X_data)} fields to {out_file}")