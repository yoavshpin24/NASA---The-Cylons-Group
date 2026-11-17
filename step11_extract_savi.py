import csv
import numpy as np
import rasterio
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

L_FACTOR = 0.5

parcels_metadata = {}
with open(INPUT_CSV, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        reg = row["region"]
        fid = int(row["field_id"])
        if reg not in parcels_metadata:
            parcels_metadata[reg] = {}
        parcels_metadata[reg][fid] = {
            "is_maize": row["is_maize"],
            "split": row["split"]
        }

for region in REGIONS:
    print(f"Extracting SAVI features for Region {region}...")
    
    field_id_path = DATA_DIR / region / f"{region}_field_id.tif"
    if not field_id_path.exists():
        continue
        
    with rasterio.open(field_id_path) as src:
        field_mask = src.read(1)
        
    time_series = {fid: {} for fid in parcels_metadata[region].keys()}
    
    for date_str in DATES:
        b4_path = DATA_DIR / region / date_str / f"{region}_B04_{date_str}.tif"
        b8_path = DATA_DIR / region / date_str / f"{region}_B08_{date_str}.tif"
        b11_path = DATA_DIR / region / date_str / f"{region}_B11_{date_str}.tif"
        
        if not (b4_path.exists() and b8_path.exists() and b11_path.exists()):
            for fid in time_series.keys():
                time_series[fid][f"savi_{date_str}"] = 0.0
                time_series[fid][f"ndwi_{date_str}"] = 0.0
            continue
            
        with rasterio.open(b4_path) as src4, rasterio.open(b8_path) as src8, rasterio.open(b11_path) as src11:
            red = src4.read(1).astype(float)
            nir = src8.read(1).astype(float)
            swir = src11.read(1).astype(float)
            
        savi_array = np.zeros_like(nir, dtype=float)
        np.divide(((nir - red) * (1 + L_FACTOR)), (nir + red + L_FACTOR), out=savi_array, where=(nir + red + L_FACTOR) > 0)
        
        ndwi_array = np.zeros_like(nir, dtype=float)
        np.divide((nir - swir), (nir + swir), out=ndwi_array, where=(nir + swir) > 0)
        
        for fid in time_series.keys():
            pixels = (field_mask == fid)
            if np.any(pixels):
                time_series[fid][f"savi_{date_str}"] = np.median(savi_array[pixels])
                time_series[fid][f"ndwi_{date_str}"] = np.median(ndwi_array[pixels])
            else:
                time_series[fid][f"savi_{date_str}"] = 0.0
                time_series[fid][f"ndwi_{date_str}"] = 0.0
                
    output_csv = f"features_savi_region_{region}.csv"
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        savi_cols = [f"savi_{d}" for d in DATES]
        ndwi_cols = [f"ndwi_{d}" for d in DATES]
        fieldnames = ["field_id", "is_maize", "split"] + savi_cols + ndwi_cols
        
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for fid, ts in time_series.items():
            row = {
                "field_id": fid,
                "is_maize": parcels_metadata[region][fid]["is_maize"],
                "split": parcels_metadata[region][fid]["split"]
            }
            row.update({k: round(float(v), 4) for k, v in ts.items()})
            writer.writerow(row)
            
    print(f"  -> Saved {output_csv}")