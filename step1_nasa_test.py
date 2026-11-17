import csv
import requests

# Coordinates of a single maize field in Iowa
LAT = 42.03
LON = -93.50
YEAR = 2022

url = "https://power.larc.nasa.gov/api/temporal/daily/point"
params = {
    "parameters": "PRECTOTCORR,T2M,GWETROOT",
    "community": "AG",
    "longitude": LON,
    "latitude": LAT,
    "start": f"{YEAR}0101",
    "end": f"{YEAR}1231",
    "format": "JSON"
}

print("Fetching data from NASA POWER...")
response = requests.get(url, params=params, timeout=15)
response.raise_for_status()

data = response.json()["properties"]["parameter"]
dates = list(data["PRECTOTCORR"].keys())

output_file = "nasa_field_2022.csv"
with open(output_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["date", "precip_mm", "temp_c", "soil_moisture"])
    for d in dates:
        writer.writerow([
            d,
            data["PRECTOTCORR"][d],
            data["T2M"][d],
            data["GWETROOT"][d]
        ])

print(f"Done! Saved {len(dates)} days to {output_file}")