import datetime
from functools import partial
from http.server import ThreadingHTTPServer
from io import BytesIO
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen

import pyarrow as pa
import pyarrow.parquet as pq
from PIL import Image
from shapely.geometry import Polygon, box

from farmland import FarmlandStore, project
from map import APP_DIRECTORY, AppHandler
from prepare_farmland import prepare


class FarmlandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.directory = Path(cls.temporary.name)
        outer = box(-7, 33, -6.9, 33.1)
        hole = box(-6.96, 33.04, -6.94, 33.06)
        geometries = [Polygon(outer.exterior.coords, [hole.exterior.coords]),
                      box(-6.99, 33.01, -6.98, 33.02), box(-6.8, 33.2, -6.79, 33.21)]
        rows = [{"time": datetime.datetime(2025, 1, 1), "label": "field", "chunk_id": "N33W007",
                 "confidence_mean": .5 if i != 2 else None,
                 "confidence_median": .51 if i != 2 else None,
                 "confidence_min": .4 if i != 2 else None,
                 "geometry": geometry.wkb} for i, geometry in enumerate(geometries)]
        table = pa.Table.from_pylist(rows)
        table = table.replace_schema_metadata({"geo": json.dumps({
            "primary_column": "geometry", "columns": {"geometry": {
                "encoding": "WKB", "bbox": [-7, 33, -6.79, 33.21],
                "crs": {"id": {"authority": "EPSG", "code": 4326}}}}}).encode()})
        source = cls.directory / "fixture.parquet"
        pq.write_table(table, source)
        prepare(source, cls.directory / "data")
        cls.store = FarmlandStore(cls.directory / "data")
        cls.previous_store = AppHandler.farmland
        AppHandler.farmland = cls.store
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), partial(AppHandler, directory=str(APP_DIRECTORY)))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        AppHandler.farmland = cls.previous_store
        cls.temporary.cleanup()

    def test_import_preserves_all_fields_and_metadata(self):
        self.assertEqual(self.store.metadata["count"], 3)
        self.assertEqual(self.store.metadata["bounds"], [-7, 33, -6.79, 33.21])
        feature = self.store.hover(-6.97, 33.03)
        self.assertEqual(feature["id"], 1)
        self.assertEqual(len(feature["geometry"]["coordinates"]), 2)
        self.assertEqual(feature["properties"]["confidence_mean"], .5)
        self.assertGreater(feature["properties"]["area_m2"], 0)

    def test_holes_and_outside_points_do_not_match(self):
        self.assertIsNone(self.store.hover(-6.95, 33.05))
        self.assertIsNone(self.store.hover(0, 0))

    def test_smallest_overlapping_field_is_inspected(self):
        self.assertEqual(self.store.hover(-6.985, 33.015)["id"], 2)

    def test_missing_confidence_is_json_null(self):
        feature = self.store.hover(-6.795, 33.205)
        self.assertIsNone(feature["properties"]["confidence_mean"])
        json.dumps(feature, allow_nan=False)

    def test_tiles_show_fields_at_overview_and_detail_zooms(self):
        for zoom in (10, 14):
            x, y = project(-6.97, 33.03, zoom)
            content = self.store.tile(zoom, int(x // 256), int(y // 256))
            image = Image.open(BytesIO(content))
            self.assertEqual(image.size, (256, 256))
            self.assertIsNotNone(image.getchannel("A").getbbox())
            self.assertEqual(content, self.store.tile(zoom, int(x // 256), int(y // 256)))

    def test_invalid_coordinates_are_rejected(self):
        with self.assertRaises(ValueError):
            self.store.hover(float("nan"), 33)
        with self.assertRaises(ValueError):
            self.store.tile(30, 1, 1)

    def test_http_metadata_hover_and_static_app(self):
        with urlopen(self.base_url + "/api/farmland/meta") as response:
            self.assertEqual(json.load(response)["count"], 3)
        with urlopen(self.base_url + "/api/farmland/hover?lng=-6.95&lat=33.05") as response:
            self.assertIsNone(json.load(response)["feature"])
        with urlopen(self.base_url + "/") as response:
            self.assertIn(b'id="draw"', response.read())
        with self.assertRaises(HTTPError) as result:
            urlopen(self.base_url + "/api/farmland/hover?lng=nan&lat=33")
        self.assertEqual(result.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
