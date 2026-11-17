import csv
import numpy as np
import rasterio
from pathlib import Path

INPUT_CSV = "custom_kenya_parcels.csv"
DATA_DIR = Path("kenya_dataset/data")
REGIONS = ["0", "1", "2", "3"]
DATES = [
    "20190606", "20190701", "20190706", "20190711", "20190721",
    "20190805", "20190815", "20190825", "20190909", "20190919",
    "20190924", "20191004", "20191103"
]

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
    print(f"Extracting features for Region {region}...")
    
    field_id_path = DATA_DIR / region / f"{region}_field_id.tif"
    if not field_id_path.exists():
        print(f"  -> Skipping region {region}, ID mask not found.")
        continue
        
    with rasterio.open(field_id_path) as src:
        field_mask = src.read(1)
        
    time_series = {fid: {"ndvi": [], "ndwi": []} for fid in parcels_metadata[region].keys()}
    
    for date_str in DATES:
        b4_path = DATA_DIR / region / date_str / f"{region}_B04_{date_str}.tif"
        b8_path = DATA_DIR / region / date_str / f"{region}_B08_{date_str}.tif"
        b11_path = DATA_DIR / region / date_str / f"{region}_B11_{date_str}.tif"
        
        if not (b4_path.exists() and b8_path.exists() and b11_path.exists()):
            continue
            
        with rasterio.open(b4_path) as src4, rasterio.open(b8_path) as src8, rasterio.open(b11_path) as src11:
            red = src4.read(1).astype(float)
            nir = src8.read(1).astype(float)
            swir = src11.read(1).astype(float)
            
        ndvi_array = np.zeros_like(nir, dtype=float)
        np.divide((nir - red), (nir + red), out=ndvi_array, where=(nir + red) > 0)
        
        ndwi_array = np.zeros_like(nir, dtype=float)
        np.divide((nir - swir), (nir + swir), out=ndwi_array, where=(nir + swir) > 0)
        
        for fid in time_series.keys():
            pixels = (field_mask == fid)
            if np.any(pixels):
                field_ndvi = np.median(ndvi_array[pixels])
                field_ndwi = np.median(ndwi_array[pixels])
                time_series[fid]["ndvi"].append(field_ndvi)
                time_series[fid]["ndwi"].append(field_ndwi)
                
    output_csv = f"features_region_{region}.csv"
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "field_id", "max_ndvi", "min_ndvi", "ndvi_amplitude", 
            "mean_ndvi", "mean_ndwi", "is_maize", "split"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for fid, ts in time_series.items():
            if len(ts["ndvi"]) == 0:
                continue
            
            max_ndvi = np.max(ts["ndvi"])
            min_ndvi = np.min(ts["ndvi"])
            mean_ndvi = np.mean(ts["ndvi"])
            mean_ndwi = np.mean(ts["ndwi"])
            
            writer.writerow({
                "field_id": fid,
                "max_ndvi": round(float(max_ndvi), 4),
                "min_ndvi": round(float(min_ndvi), 4),
                "ndvi_amplitude": round(float(max_ndvi - min_ndvi), 4),
                "mean_ndvi": round(float(mean_ndvi), 4),
                "mean_ndwi": round(float(mean_ndwi), 4),
                "is_maize": parcels_metadata[region][fid]["is_maize"],
                "split": parcels_metadata[region][fid]["split"]
            })
            
    print(f"  -> Saved {output_csv}")