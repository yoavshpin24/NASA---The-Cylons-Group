# Terra — local polygon explorer

Run from this folder with Python 3; no packages, account, API key, Node.js, or hosting service required:

```sh
python3 map.py
```

Open **http://127.0.0.1:8000**. To open your browser automatically, use `python3 map.py --open`. Stop the server with **Ctrl+C**. If the port is occupied, use `python3 map.py --port 8001`.

Click **Draw a polygon**, place at least three points, and click the first point or press Enter to finish. The visible border connects your vertices. Drag points to edit, copy the coordinates, or download GeoJSON/CSV. Your last selection is saved in your browser.

The app is served only on your computer's loopback address. Drawing, coordinate calculations, and exports run in your browser. Map imagery and place-name search still require internet access to Esri and OpenStreetMap services.

App files are in `terra-polygon/dist/`. See [the app README](terra-polygon/README.md) for coordinate formats and keyboard shortcuts.
