# Terra — Polygon Explorer

An interactive Earth map for drawing a polygon, editing its vertices, and exporting coordinates. No API key or build step required.

Run locally from the parent workspace folder:

```sh
python3 map.py
```

Open http://127.0.0.1:8000. No hosting service or account is required. Alternatively, from this `terra-polygon` folder, run `python3 -m http.server 8000 --bind 127.0.0.1 --directory dist`.

Select **Draw a polygon**, place at least three vertices, then click the first vertex or press Enter. Drag vertices to adjust the shape. The coordinate table uses latitude, longitude; GeoJSON uses longitude, latitude and closes the polygon ring automatically. Export GeoJSON or CSV, or copy the visible coordinate format. The last completed selection is saved locally in your browser.

Shortcuts: `/` search, `Enter` finish, `Backspace` undo point, `Escape` cancel. Search accepts place names or `latitude, longitude`.

Leaflet 1.9.4 is included in `dist/vendor`. Satellite imagery is provided by Esri; street maps and place search use OpenStreetMap and Nominatim. Internet access is required for tiles, place search, and optional web fonts. The map uses Web Mercator (latitude ±85.05°); output coordinates use WGS 84. Area is an approximate spherical calculation. GeoJSON coordinates near the antimeridian are unwrapped to preserve the selected shape; longitudes may extend beyond ±180°.

Run geometry checks with Node 22 or later:

```sh
node --test tests/geometry.test.js
```
