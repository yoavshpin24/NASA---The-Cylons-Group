# Terra — Morocco farmland explorer

Explore the 2025 `N33W007` farmland tile in Morocco, inspect individual fields, and draw and export your own polygon boundaries.

## Run

The dataset and environment are already prepared in this checkout. From this folder:

```sh
python3 map.py --open
```

Open **http://127.0.0.1:8000**. Stop with **Ctrl+C**. If the port is occupied, use `python3 map.py --port 8001 --open`. After updating the server code, stop and restart any previously running instance. The launcher uses this folder's `.venv` automatically when the required packages are unavailable in your system Python.

## First-time setup on another machine

Use Python 3.10 or later and your own copy of the GeoParquet file:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python prepare_farmland.py /path/to/2025_N33W007.parquet
python3 map.py --open
```

Preparation builds a spatial index and overview image in `data/`. The source Parquet stays in its original location. Generated data, cached tiles, and the virtual environment are ignored by Git. Preparation requires WGS 84 / EPSG:4326 WKB polygons; rerun it to replace the dataset. Without prepared data, the app still supports drawing and exports.

## Use the map

- The map starts over the Morocco dataset. Gold outlines show all 276,353 fields using a tiled layer; detailed tiles load as you zoom in.
- Hover over a field, or tap on a touch screen, to highlight its exact boundary in turquoise. Its tooltip shows a local field number, label, approximate area in hectares, three confidence scores, dataset date, and tile ID. Fields with missing scores display “Not available.” Confidence values are dataset scores, not calibrated accuracy percentages. Local field numbers come from source row order.
- **Go to farmland** returns to the dataset; **Show field boundaries** toggles the overlay.
- **Draw a polygon** retains the original selection workflow. Place at least three points and click the first point or press Enter to finish. Drag vertices to edit, copy coordinates, or download GeoJSON/CSV. Field inspection pauses while drawing, and the last completed selection is saved in your browser.

The server binds only to your computer's loopback address. Field data is read locally. Basemap imagery, place-name search, and optional fonts require internet access.

## Checks

```sh
.venv/bin/python -m unittest discover -s tests -v
node --test terra-polygon/tests/geometry.test.js
```

The JavaScript geometry checks require Node 22 or later. See [the app README](terra-polygon/README.md) for coordinate formats and shortcuts.
