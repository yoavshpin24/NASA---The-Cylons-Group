"""Spatially indexed field data and transparent map tiles for the local explorer."""

from functools import lru_cache
from contextlib import closing
from io import BytesIO
import json
import math
from pathlib import Path
import sqlite3
import zlib

from PIL import Image, ImageDraw
from shapely import from_wkb
from shapely.geometry import Point, mapping


ROOT = Path(__file__).resolve().parent
DATA_DIRECTORY = ROOT / "data"
OVERVIEW_ZOOM = 12
FILL = (244, 191, 79, 38)
OUTLINE = (246, 205, 103, 225)


def project(lng, lat, zoom):
    size = 256 * 2 ** zoom
    lat = max(-85.05112878, min(85.05112878, lat))
    return ((lng + 180) / 360 * size,
            (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * size)


def unproject(x, y, zoom):
    size = 256 * 2 ** zoom
    return (x / size * 360 - 180,
            math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / size)))))


def paint_polygon(image, geometry, zoom, origin, scale=1):
    """Render rings in Web Mercator, preserving holes in field boundaries."""
    draw = ImageDraw.Draw(image)

    def pixels(ring):
        return [((x - origin[0]) * scale, (y - origin[1]) * scale)
                for x, y in (project(lng, lat, zoom) for lng, lat, *_ in ring.coords)]

    exterior = pixels(geometry.exterior)
    draw.polygon(exterior, fill=FILL)
    draw.line(exterior, fill=OUTLINE, width=max(1, round(scale)), joint="curve")
    for ring in geometry.interiors:
        interior = pixels(ring)
        draw.polygon(interior, fill=(0, 0, 0, 0))
        draw.line(interior, fill=OUTLINE, width=max(1, round(scale)), joint="curve")


class FarmlandStore:
    def __init__(self, directory=DATA_DIRECTORY):
        self.directory = Path(directory).resolve()
        self.database = self.directory / "farmland.sqlite"
        self.cache_directory = self.directory / "tiles"
        with closing(self.connect()) as connection:
            row = connection.execute("SELECT value FROM metadata WHERE key = 'dataset'").fetchone()
        self.metadata = json.loads(row[0])
        with Image.open(self.directory / "farmland-overview.png") as image:
            self.overview = image.convert("RGBA")
        self.overview.load()

    def connect(self):
        connection = sqlite3.connect(self.database.as_uri() + "?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        return connection

    def fields_in_bounds(self, bounds):
        west, south, east, north = bounds
        with closing(self.connect()) as connection:
            return connection.execute(
                "SELECT f.* FROM field_bounds b JOIN fields f ON f.id=b.id "
                "WHERE b.min_x<=? AND b.max_x>=? AND b.min_y<=? AND b.max_y>=? "
                "ORDER BY f.id", (east, west, north, south)).fetchall()

    def hover(self, lng, lat):
        if not math.isfinite(lng) or not math.isfinite(lat) or not -180 <= lng <= 180 or not -85.051129 <= lat <= 85.051129:
            raise ValueError("Coordinates are outside the map.")
        point = Point(lng, lat)
        candidates = self.fields_in_bounds((lng, lat, lng, lat))
        # Prefer the smallest containing field when dataset boundaries overlap.
        for row in sorted(candidates, key=lambda r: r["area_m2"]):
            geometry = from_wkb(zlib.decompress(row["geometry"]))
            if geometry.covers(point):
                return {"type": "Feature", "id": row["id"],
                        "properties": {key: row[key] for key in (
                            "id", "label", "time", "chunk_id", "confidence_mean",
                            "confidence_median", "confidence_min", "area_m2")},
                        "geometry": mapping(geometry)}
        return None

    @lru_cache(maxsize=128)
    def tile(self, zoom, x, y):
        if not 2 <= zoom <= 19 or not 0 <= x < 2 ** zoom or not 0 <= y < 2 ** zoom:
            raise ValueError("Invalid tile coordinates.")
        cache = self.cache_directory / str(zoom) / str(x) / f"{y}.png"
        if cache.is_file():
            return cache.read_bytes()
        if zoom <= OVERVIEW_ZOOM:
            factor = 2 ** (OVERVIEW_ZOOM - zoom)
            left, top = self.metadata["overview_origin"]
            box = (x * 256 * factor - left, y * 256 * factor - top,
                   (x + 1) * 256 * factor - left, (y + 1) * 256 * factor - top)
            # Affine sampling avoids allocating a huge padded crop at country zoom.
            image = self.overview.transform(
                (256, 256), Image.Transform.AFFINE,
                (factor, 0, box[0], 0, factor, box[1]), Image.Resampling.BILINEAR)
        else:
            west, north = unproject(x * 256 - 2, y * 256 - 2, zoom)
            east, south = unproject((x + 1) * 256 + 2, (y + 1) * 256 + 2, zoom)
            image = Image.new("RGBA", (512, 512))
            for row in self.fields_in_bounds((west, south, east, north)):
                geometry = from_wkb(zlib.decompress(row["geometry"]))
                paint_polygon(image, geometry, zoom, (x * 256, y * 256), scale=2)
            image = image.resize((256, 256), Image.Resampling.LANCZOS)
        output = BytesIO()
        image.save(output, format="PNG")
        content = output.getvalue()
        cache.parent.mkdir(parents=True, exist_ok=True)
        # Concurrent requests may calculate the same tile; replace atomically.
        import tempfile
        with tempfile.NamedTemporaryFile(dir=cache.parent, delete=False) as temporary:
            temporary.write(content)
            temporary_path = Path(temporary.name)
        temporary_path.replace(cache)
        return content
