import csv

input_file = "field_2022_complete.csv"
output_file = "parcel_features_2022.csv"

all_ndvi = []
peak_ndvi = []
off_ndvi = []
peak_ndwi = []
annual_precip = 0.0

with open(input_file, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        month = int(row["month"])
        annual_precip += float(row["total_precip_mm"])

        if row["ndvi"] != "":
            ndvi_val = float(row["ndvi"])
            all_ndvi.append(ndvi_val)
            if month in (6, 7, 8):
                peak_ndvi.append(ndvi_val)
            elif month in (1, 2, 3, 4, 10, 11, 12):
                off_ndvi.append(ndvi_val)

        if row["ndwi"] != "" and month in (6, 7, 8):
            peak_ndwi.append(float(row["ndwi"]))

features = {
    "parcel_id": "IA_2022_001",
    "max_ndvi": round(max(all_ndvi), 3),
    "ndvi_amplitude": round(max(all_ndvi) - min(all_ndvi), 3),
    "peak_season_ndvi": round(sum(peak_ndvi) / len(peak_ndvi), 3),
    "off_season_ndvi": round(sum(off_ndvi) / len(off_ndvi), 3),
    "peak_season_ndwi": round(sum(peak_ndwi) / len(peak_ndwi), 3),
    "annual_precip_mm": round(annual_precip, 1),
    "is_maize": 1
}

with open(output_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(features.keys()))
    writer.writeheader()
    writer.writerow(features)

print("Extracted 6 features for our maize field:")
for k, v in features.items():
    print(f"  {k}: {v}")