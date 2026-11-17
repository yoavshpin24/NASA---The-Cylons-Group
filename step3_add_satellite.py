import calendar
import csv
import numpy as np
import pystac_client
import planetary_computer
import rasterio
from rasterio.windows import Window
from rasterio.warp import transform

LAT = 42.03
LON = -93.50
YEAR = 2022

catalog = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")

# Small bounding box around our single field
bbox = [LON - 0.01, LAT - 0.01, LON + 0.01, LAT + 0.01]

satellite_by_month = {}

for month in range(1, 13):
    last_day = calendar.monthrange(YEAR, month)[1]
    date_range = f"{YEAR}-{month:02d}-01/{YEAR}-{month:02d}-{last_day:02d}"

    search = catalog.search(
        collections=["sentinel-2-l2a"],
        bbox=bbox,
        datetime=date_range,
        query={"eo:cloud_cover": {"lt": 30}}
    )
    items = list(search.items())
    if not items:
        satellite_by_month[month] = (None, None)
        print(f"Month {month:02d}: No clear image found")
        continue

    # Pick the clearest image of the month
    best_item = min(items, key=lambda x: x.properties.get("eo:cloud_cover", 100))
    signed = planetary_computer.sign(best_item)

    with (
        rasterio.open(signed.assets["B04"].href) as b04_src,
        rasterio.open(signed.assets["B08"].href) as b08_src,
        rasterio.open(signed.assets["B11"].href) as b11_src
    ):
        xs, ys = transform("EPSG:4326", b04_src.crs, [LON], [LAT])
        r10, c10 = b04_src.index(xs[0], ys[0])
        r20, c20 = b11_src.index(xs[0], ys[0])

        red = float(np.median(b04_src.read(1, window=Window(c10 - 1, r10 - 1, 3, 3))))
        nir = float(np.median(b08_src.read(1, window=Window(c10 - 1, r10 - 1, 3, 3))))
        swir = float(np.median(b11_src.read(1, window=Window(c20 - 1, r20 - 1, 2, 2))))

        ndvi = round((nir - red) / (nir + red), 3) if (nir + red) > 0 else None
        ndwi = round((nir - swir) / (nir + swir), 3) if (nir + swir) > 0 else None

        satellite_by_month[month] = (ndvi, ndwi)
        print(f"Month {month:02d}: NDVI={ndvi}, NDWI={ndwi}")

# Merge with our NASA monthly file
with open("nasa_monthly_2022.csv", "r", encoding="utf-8") as f_in:
    rows = list(csv.DictReader(f_in))

output_file = "field_2022_complete.csv"
with open(output_file, "w", newline="", encoding="utf-8") as f_out:
    writer = csv.writer(f_out)
    writer.writerow(["month", "total_precip_mm", "avg_temp_c", "avg_soil_moisture", "ndvi", "ndwi"])
    for row in rows:
        m = int(row["month"])
        ndvi, ndwi = satellite_by_month.get(m, (None, None))
        writer.writerow([
            m,
            row["total_precip_mm"],
            row["avg_temp_c"],
            row["avg_soil_moisture"],
            ndvi if ndvi is not None else "",
            ndwi if ndwi is not None else ""
        ])

print(f"\nSaved combined table to {output_file}")
print(f"Month {month:02d} -> Scene ID: {best_item.id} | Date: {best_item.datetime} | Cloud: {best_item.properties.get('eo:cloud_cover')}%")