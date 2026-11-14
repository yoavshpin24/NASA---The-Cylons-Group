# Farmland map

A full-window map of Morocco's farmland with field inspection and optional polygon drawing, vertex editing, and coordinate exports. Navigation is constrained to the Morocco area and uses an arrow cursor. No API key or build step required.

Run locally from the parent workspace folder:

```sh
python3 map.py
```

Open http://127.0.0.1:8000. See the [project README](../README.md) for environment setup and the one-time GeoParquet import. Use `map.py` to serve the farmland API as well as the app.

Gold outlines show the farmland dataset. Hover on a field, or tap it, to highlight its exact boundary and see field information. Toggle the layer using **Field boundaries** or return using **Go to farmland**. Field inspection pauses while you draw. Tile rendering keeps the full dataset out of browser memory; overview tiles are simplified, while close-up tiles and hover geometry retain original boundaries and holes. Field areas are approximate spherical measurements excluding holes. Confidence scores are displayed as supplied, with missing values marked unavailable.

Open **Tools**, select **Draw a polygon**, place at least three vertices, then click the first vertex or press Enter. The tools start collapsed; on mobile they open in a bottom sheet so the map stays usable. Closing the panel cancels an unfinished draft and restores the previous selection. Drag vertices to adjust a completed shape. The coordinate table uses latitude, longitude; GeoJSON uses longitude, latitude and closes the polygon ring automatically. Export GeoJSON or CSV, or copy the visible coordinate format. The last completed selection within the Morocco area is saved locally in your browser.

Shortcuts: `/` search, `Enter` finish, `Backspace` undo point, `Escape` cancel drawing or close the idle tools panel. Search accepts Morocco place names or `latitude, longitude` within the viewing extent.

Leaflet 1.9.4 is included in `dist/vendor`. Satellite imagery is provided by Esri; street maps and place search use OpenStreetMap and Nominatim. Internet access is required for tiles, place search, and optional web fonts. The map uses Web Mercator (latitude ±85.05°); output coordinates use WGS 84. Area is an approximate spherical calculation. GeoJSON coordinates near the antimeridian are unwrapped to preserve the selected shape; longitudes may extend beyond ±180°.

Run geometry checks with Node 22 or later:

```sh
node --test tests/geometry.test.js
```
