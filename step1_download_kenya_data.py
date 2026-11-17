import requests
from pathlib import Path

BASE_URL = "https://data.source.coop/radiantearth/african-crops-kenya-02/"
OUTPUT_DIR = Path("kenya_dataset")

# We only need the main ID file and the labels/field_ids for the 4 regions
FILES_TO_DOWNLOAD = [
    "FieldIds.csv",
    "data/0/0_field_id.tif",
    "data/0/0_label.tif",
    "data/1/1_field_id.tif",
    "data/1/1_label.tif",
    "data/2/2_field_id.tif",
    "data/2/2_label.tif",
    "data/3/3_field_id.tif",
    "data/3/3_label.tif"
]

def download_file(url: str, dest_path: Path):
    if dest_path.exists():
        print(f"[SKIP] {dest_path.name} already exists.")
        return

    print(f"[DOWNLOAD] Fetching {dest_path.name}...")
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    response = requests.get(url, stream=True)
    response.raise_for_status()

    with open(dest_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"  -> Saved to {dest_path}")

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    for file_path in FILES_TO_DOWNLOAD:
        url = BASE_URL + file_path
        local_path = OUTPUT_DIR / file_path
        download_file(url, local_path)
        
    print("\n[DONE] All metadata and label files downloaded successfully.")

if __name__ == "__main__":
    main()