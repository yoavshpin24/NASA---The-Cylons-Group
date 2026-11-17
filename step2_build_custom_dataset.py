import numpy as np
import rasterio
import csv
from pathlib import Path

OUTPUT_CSV = "custom_kenya_parcels.csv"
REGIONS = ["0", "1", "2", "3"]

parcels = []

for region in REGIONS:
    print(f"Processing region {region}...")
    base_dir = Path("kenya_dataset/data") / region
    field_id_path = base_dir / f"{region}_field_id.tif"
    label_path = base_dir / f"{region}_label.tif"
    
    with rasterio.open(field_id_path) as src_id, rasterio.open(label_path) as src_label:
        id_array = src_id.read(1)
        label_array = src_label.read(1)
        transform = src_id.transform
        
        # Get all unique field IDs, ignoring 0 (which is the background/empty space)
        unique_ids = np.unique(id_array)
        unique_ids = unique_ids[unique_ids != 0]
        
        for field_id in unique_ids:
            # Find the row and column indices of all pixels belonging to this field
            rows, cols = np.where(id_array == field_id)
            
            # Extract the crop label for this field
            # Taking the max ensures we get the actual crop code if there's minor edge noise
            field_label = np.max(label_array[rows, cols])
            
            # In the CV4A dataset, label 1 is Maize
            is_maize = 1 if field_label == 1 else 0
            
            # Calculate the physical center of the field
            row_mean = rows.mean()
            col_mean = cols.mean()
            
            # Convert the pixel location (row, col) to geographic coordinates (lon, lat)
            lon, lat = rasterio.transform.xy(transform, int(row_mean), int(col_mean))
            
            # Apply our spatial cross-validation strategy: Region 3 is held out for testing
            split = "test" if region == "3" else "train"
            
            parcels.append({
                "region": region,
                "field_id": field_id,
                "lat": round(lat, 5),
                "lon": round(lon, 5),
                "is_maize": is_maize,
                "split": split
            })

with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
    fieldnames = ["region", "field_id", "lat", "lon", "is_maize", "split"]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(parcels)
    
print(f"\n[DONE] Built custom spatial dataset with {len(parcels)} parcels.")
print(f"Saved to {OUTPUT_CSV}")