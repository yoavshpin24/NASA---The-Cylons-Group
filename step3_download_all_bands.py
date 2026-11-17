import requests
from pathlib import Path

BASE_URL = "https://data.source.coop/radiantearth/african-crops-kenya-02/data/"
OUTPUT_BASE_DIR = Path("kenya_dataset/data")

REGIONS = ["0", "1", "2", "3"]
BANDS = ["B04", "B08", "B11"]

DATES = [
    "20190606", "20190701", "20190706", "20190711", "20190721", 
    "20190805", "20190815", "20190825", "20190909", "20190919", 
    "20190924", "20191004", "20191103"
]

def download_band(region, date_str, band):
    filename = f"{region}_{band}_{date_str}.tif"
    url = f"{BASE_URL}{region}/{date_str}/{filename}"
    dest_path = OUTPUT_BASE_DIR / region / date_str / filename
    
    if dest_path.exists():
        return
        
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {filename}...")
    
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    else:
        print(f"  -> Skipping (Not found): {filename}")

for r in REGIONS:
    print(f"\n--- Starting Region {r} ---")
    for d in DATES:
        for b in BANDS:
            download_band(r, d, b)
            
print("\nFinished downloading required satellite bands for all regions.")