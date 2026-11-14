#!/usr/bin/env python3
"""Prepare a GeoParquet field dataset once for fast local map rendering."""

import argparse
import json
import math
from pathlib import Path
import shutil
import sqlite3
import zlib

import pyarrow.parquet as pq
from PIL import Image
from shapely import from_wkb

from farmland import DATA_DIRECTORY, OVERVIEW_ZOOM, paint_polygon, project


def prepare(source, directory=DATA_DIRECTORY):
    source, directory = Path(source).resolve(), Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    parquet = pq.ParquetFile(source)
    geo = json.loads(parquet.schema_arrow.metadata[b"geo"])
    geometry_column = geo["primary_column"]
    specification = geo["columns"][geometry_column]
    crs = specification.get("crs", {}).get("id", {})
    if crs != {"authority": "EPSG", "code": 4326} or specification["encoding"] != "WKB":
        raise ValueError("This importer requires WGS 84 (EPSG:4326) WKB polygons.")
    west, south, east, north = specification["bbox"]
    left, top = project(west, north, OVERVIEW_ZOOM)
    right, bottom = project(east, south, OVERVIEW_ZOOM)
    origin = (math.floor(left) - 2, math.floor(top) - 2)
    overview = Image.new("RGBA", (math.ceil(right) - origin[0] + 2,
                                  math.ceil(bottom) - origin[1] + 2))
    temporary_database = directory / "farmland.building.sqlite"
    temporary_database.unlink(missing_ok=True)
    connection = sqlite3.connect(temporary_database)
    connection.executescript("""
        PRAGMA journal_mode=OFF;
        PRAGMA synchronous=OFF;
        CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE fields (
            id INTEGER PRIMARY KEY, label TEXT, time TEXT, chunk_id TEXT,
            confidence_mean REAL, confidence_median REAL, confidence_min REAL,
            area_m2 REAL NOT NULL, geometry BLOB NOT NULL);
        CREATE VIRTUAL TABLE field_bounds USING rtree(id, min_x, max_x, min_y, max_y);
    """)
    index = 0
    try:
        for batch in parquet.iter_batches(batch_size=4096):
            records, bounds = [], []
            for row in batch.to_pylist():
                geometry = from_wkb(row[geometry_column])
                if geometry is None or geometry.is_empty or geometry.geom_type != "Polygon" or not geometry.is_valid:
                    raise ValueError(f"Record {index + 1} has an invalid or unsupported geometry.")
                index += 1
                # Approximate spherical area at the field's latitude, excluding holes.
                area_m2 = geometry.area * (math.pi * 6371008.8 / 180) ** 2 * math.cos(math.radians(geometry.centroid.y))
                scores = [row.get(name) for name in ("confidence_mean", "confidence_median", "confidence_min")]
                scores = [float(v) if v is not None and math.isfinite(v) else None for v in scores]
                timestamp = row.get("time")
                records.append((index, row.get("label"), timestamp.isoformat() if timestamp else None,
                                row.get("chunk_id"), *scores, area_m2,
                                zlib.compress(row[geometry_column], level=1)))
                w, s, e, n = geometry.bounds
                bounds.append((index, w, e, s, n))
                # Simplify only the overview image; exact geometry remains in the index.
                simplified = geometry.simplify(360 / (256 * 2 ** OVERVIEW_ZOOM) / 4, preserve_topology=True)
                paint_polygon(overview, simplified, OVERVIEW_ZOOM, origin)
            connection.executemany("INSERT INTO fields VALUES (?,?,?,?,?,?,?,?,?)", records)
            connection.executemany("INSERT INTO field_bounds VALUES (?,?,?,?,?)", bounds)
            connection.commit()
            print(f"Prepared {index:,} / {parquet.metadata.num_rows:,} fields", flush=True)
        metadata = {"ready": True, "count": index, "bounds": [west, south, east, north],
                    "source": source.name, "overview_zoom": OVERVIEW_ZOOM,
                    "overview_origin": list(origin), "crs": "EPSG:4326"}
        connection.execute("INSERT INTO metadata VALUES ('dataset', ?)", (json.dumps(metadata),))
        connection.commit()
    finally:
        connection.close()
    overview.save(directory / "farmland-overview.png")
    temporary_database.replace(directory / "farmland.sqlite")
    shutil.rmtree(directory / "tiles", ignore_errors=True)
    print(f"Ready: {index:,} fields indexed in {directory}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Path to the GeoParquet file")
    parser.add_argument("--output", type=Path, default=DATA_DIRECTORY)
    args = parser.parse_args()
    prepare(args.source, args.output)
