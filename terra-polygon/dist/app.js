import { area, wrapLongitude, unwrap, validPolygon, geoJSON, csv } from './geometry.js';
import { attachFarmland } from './farmland-layer.js';
import { element as $ } from './dom.js';
import { L } from './leaflet.js';
let points = [], backup = [], drawing = false;
let format = 'table', exportFormat = 'geojson';
let markers = [], toastTimer;
let searchController;
const storageKey = 'terra-polygon-v1';
const notify = (message) => { $('toast').textContent = message; $('toast').hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => $('toast').hidden = true, 4500); };
const moroccoBounds = L.latLngBounds([[27.4, -13.3], [36.2, -0.9]]);
const map = L.map('map', { zoomControl: false, doubleClickZoom: false, minZoom: 6, maxZoom: 19, maxBounds: moroccoBounds, maxBoundsViscosity: 1 }).setView([33.49, -6.5], 10);
function constrainView() {
    map.setMinZoom(Math.max(6, map.getBoundsZoom(moroccoBounds, true)));
    map.panInsideBounds(moroccoBounds, { animate: false });
}
constrainView();
map.attributionControl.setPrefix('<a href="https://leafletjs.com" target="_blank" rel="noopener">Leaflet</a>');
L.control.scale({ position: 'bottomleft', imperial: false, maxWidth: 90 }).addTo(map);
const satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', { maxNativeZoom: 18, maxZoom: 19, attribution: 'Imagery © Esri, Maxar, Earthstar Geographics, GIS User Community' });
const streets = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors' });
satellite.addTo(map);
const farmland = attachFarmland(map, () => drawing);
const polygon = L.polygon([], { color: '#d3f3a2', weight: 3, fillColor: '#c1e88a', fillOpacity: .2, interactive: false }).addTo(map);
const line = L.polyline([], { color: '#e0f7ba', weight: 3, interactive: false }).addTo(map);
const ghost = L.polyline([], { color: '#e0f7ba', weight: 1.5, dashArray: '4 6', opacity: .8, interactive: false }).addTo(map);
let loadedTiles = 0, failedTiles = 0;
for (const layer of [satellite, streets]) {
    layer.on('tileload', () => { loadedTiles++; $('map-error').hidden = true; });
    layer.on('tileerror', () => { failedTiles++; if (failedTiles > 3 && loadedTiles === 0)
        $('map-error').hidden = false; });
}
function save() {
    try {
        if (points.length)
            localStorage.setItem(storageKey, JSON.stringify(points.map(p => ({ lat: p.lat, lng: wrapLongitude(p.lng) }))));
        else
            localStorage.removeItem(storageKey);
    }
    catch { /* Map and exports remain usable when browser storage is unavailable. */ }
}
function renderMarkers() {
    markers.forEach(m => m.remove());
    markers = unwrap(points).map((p, i) => {
        const marker = L.marker([p.lat, p.lng], { draggable: true, keyboard: true, title: `Vertex ${i + 1}. Drag to adjust.`, icon: L.divIcon({ className: `vertex-icon ${i === 0 ? 'first-vertex' : ''}`, html: String(i + 1), iconSize: [21, 21], iconAnchor: [10.5, 10.5] }) }).addTo(map);
        marker.on('click', (e) => { L.DomEvent.stopPropagation(e.originalEvent); if (drawing && i === 0)
            finish(); });
        let before = { ...points[i] };
        marker.on('dragstart', () => { before = { ...points[i] }; });
        marker.on('drag', () => { const p = marker.getLatLng(); points[i] = { lat: p.lat, lng: p.lng }; renderShape(); renderData(); });
        marker.on('dragend', () => {
            if (!drawing && !validPolygon(points)) {
                points[i] = before;
                notify('That move creates an invalid boundary. Try another position.');
            }
            renderShape();
            renderMarkers();
            renderData();
            if (!drawing)
                save();
        });
        return marker;
    });
}
function renderShape() {
    const display = unwrap(points).map((p) => [p.lat, p.lng]);
    polygon.setLatLngs(points.length >= 3 ? display : []);
    polygon.setStyle({ fillOpacity: drawing ? .12 : .23 });
    line.setLatLngs(drawing && points.length < 3 ? display : []);
    if (!drawing || !points.length)
        ghost.setLatLngs([]);
}
function renderData() {
    $('vertices').innerHTML = `${points.length} <small>points</small>`;
    const km = area(points) / 1e6;
    $('area').innerHTML = points.length >= 3 ? `${km < .01 ? (km * 1e6).toLocaleString(undefined, { maximumFractionDigits: 1 }) : km.toLocaleString(undefined, { maximumFractionDigits: 2 })} <small>${km < .01 ? 'm²' : 'km²'}</small>` : '— <small>km²</small>';
    $('finish').disabled = points.length < 3;
    $('undo').disabled = !points.length;
    $('clear').disabled = drawing || !points.length;
    $('copy').disabled = $('download').disabled = drawing || points.length < 3;
    $('selection-state').textContent = drawing ? 'DRAWING' : points.length ? 'AREA SELECTED' : 'NO AREA YET';
    $('selection-state').classList.toggle('ready', !drawing && points.length > 0);
    $('coordinate-note').textContent = format === 'table' ? 'Latitude, longitude · 6 decimal places' : 'Longitude, latitude · closed polygon ring';
    if (!points.length) {
        $('coordinate-content').innerHTML = '<div class="empty-state">No polygon selected.<br>Draw an area to see its coordinates.</div>';
    }
    else if (format === 'table') {
        $('coordinate-content').innerHTML = `<table class="coordinate-table"><thead><tr><th>POINT</th><th>LATITUDE</th><th>LONGITUDE</th></tr></thead><tbody>${points.map((p, i) => `<tr data-index="${i}"><td>${String(i + 1).padStart(2, '0')}</td><td>${p.lat.toFixed(6)}</td><td>${wrapLongitude(p.lng).toFixed(6)}</td></tr>`).join('')}</tbody></table>`;
    }
    else {
        const pre = document.createElement('pre');
        pre.className = 'json-output';
        pre.textContent = points.length >= 3 ? JSON.stringify(geoJSON(points), null, 2) : 'Add at least 3 points to create a GeoJSON polygon.';
        $('coordinate-content').replaceChildren(pre);
    }
    if (drawing)
        $('draw-tip').textContent = points.length < 3 ? `${points.length} point${points.length === 1 ? '' : 's'} placed · at least 3 needed.` : 'Click the first point or press Enter to finish.';
}
function render() { renderShape(); renderMarkers(); renderData(); }
function setDrawing(value) {
    drawing = value;
    farmland.onDrawingChange();
    $('draw').hidden = value;
    $('drawing-actions').hidden = !value;
    $('map').classList.toggle('map-drawing', value);
    $('draw-description').textContent = value ? 'Click on the map to add points. Drag a point to adjust it.' : 'Draw an area to measure it and export its coordinates.';
    $('draw-tip').textContent = points.length ? 'Drag any vertex to refine your selection.' : 'Click to place points. Click the first to finish.';
    $('draw').querySelector('span').textContent = points.length ? 'Draw a new polygon' : 'Draw a polygon';
    render();
}
function start() {
    backup = points.map(p => ({ ...p }));
    points = [];
    setDrawing(true);
}
function finish() {
    if (points.length < 3) {
        notify('Add at least three points to finish your polygon.');
        return;
    }
    if (!validPolygon(points)) {
        notify('Your boundary crosses itself or has no area. Undo a point and try again.');
        return;
    }
    setDrawing(false);
    save();
    notify('Polygon ready. Drag a point to refine it, or export your coordinates.');
}
$('draw').addEventListener('click', start);
$('finish').addEventListener('click', finish);
$('undo').addEventListener('click', () => { points.pop(); ghost.setLatLngs([]); render(); });
$('cancel').addEventListener('click', () => { points = backup; setDrawing(false); });
$('clear').addEventListener('click', () => { points = []; backup = []; setDrawing(false); save(); notify('Selection cleared.'); });
function setToolsOpen(open) {
    if (!open && drawing) {
        points = backup;
        setDrawing(false);
    }
    $('tools-panel').hidden = !open;
    $('tools-toggle').setAttribute('aria-expanded', String(open));
}
$('tools-toggle').addEventListener('click', () => setToolsOpen($('tools-panel').hidden !== false));
$('close-tools').addEventListener('click', () => { setToolsOpen(false); $('tools-toggle').focus(); });
map.on('click', (e) => {
    $('search-results').hidden = true;
    if (!drawing || !moroccoBounds.contains(e.latlng))
        return;
    let p = { lat: e.latlng.lat, lng: e.latlng.lng };
    const last = points.at(-1);
    if (last) {
        p.lng = last.lng + wrapLongitude(p.lng - last.lng);
        if (map.distance(last, p) < .05)
            return;
    }
    points.push(p);
    render();
});
map.on('mousemove', (e) => {
    const { lat, lng } = e.latlng, l = wrapLongitude(lng);
    $('cursor-coordinates').textContent = `${Math.abs(lat).toFixed(4)}° ${lat >= 0 ? 'N' : 'S'}   ${Math.abs(l).toFixed(4)}° ${l >= 0 ? 'E' : 'W'}`;
    const last = points.at(-1);
    if (drawing && last)
        ghost.setLatLngs([last, { lat, lng: last.lng + wrapLongitude(lng - last.lng) }]);
});
map.on('mouseout', () => ghost.setLatLngs([]));
document.querySelectorAll('[data-format]').forEach(button => button.addEventListener('click', () => {
    const value = button.dataset.format;
    if (value !== 'table' && value !== 'geojson')
        return;
    format = value;
    document.querySelectorAll('[data-format]').forEach(b => { b.classList.toggle('active', b === button); b.setAttribute('aria-selected', String(b === button)); });
    $('coordinate-content').setAttribute('aria-labelledby', button.id);
    renderData();
}));
document.querySelectorAll('[data-export]').forEach(button => button.addEventListener('click', () => {
    const value = button.dataset.export;
    if (value !== 'csv' && value !== 'geojson')
        return;
    exportFormat = value;
    document.querySelectorAll('[data-export]').forEach(b => b.classList.toggle('active', b === button));
    $('download').setAttribute('aria-label', `Download ${exportFormat === 'csv' ? 'CSV' : 'GeoJSON'}`);
}));
$('copy').addEventListener('click', async () => {
    const text = format === 'geojson' ? JSON.stringify(geoJSON(points), null, 2) : points.map(p => `${p.lat.toFixed(6)}, ${wrapLongitude(p.lng).toFixed(6)}`).join('\n');
    try {
        await navigator.clipboard.writeText(text);
        notify('Coordinates copied to clipboard.');
    }
    catch {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.cssText = 'position:fixed;left:-9999px';
        document.body.append(textarea);
        textarea.select();
        const copied = document.execCommand('copy');
        textarea.remove();
        notify(copied ? 'Coordinates copied to clipboard.' : 'Clipboard unavailable. Download your coordinates instead.');
    }
});
$('download').addEventListener('click', () => {
    const text = exportFormat === 'csv' ? csv(points) : JSON.stringify(geoJSON(points), null, 2) + '\n';
    const blob = new Blob([text], { type: exportFormat === 'csv' ? 'text/csv;charset=utf-8' : 'application/geo+json' });
    const url = URL.createObjectURL(blob), a = document.createElement('a');
    a.href = url;
    a.download = `polygon.${exportFormat}`;
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    notify(`${exportFormat === 'csv' ? 'CSV' : 'GeoJSON'} downloaded.`);
});
$('zoom-in').addEventListener('click', () => map.zoomIn());
$('zoom-out').addEventListener('click', () => map.zoomOut());
function fit() { if (points.length)
    map.fitBounds(L.latLngBounds(unwrap(points)), { padding: [65, 85], maxZoom: 16 });
else
    farmland.focus(); }
$('fit').addEventListener('click', fit);
$('morocco').addEventListener('click', () => map.fitBounds(moroccoBounds));
for (const [id, layer, other] of [['satellite', satellite, streets], ['streets', streets, satellite]])
    $(id).addEventListener('click', () => {
        if (map.hasLayer(layer))
            return;
        loadedTiles = failedTiles = 0;
        $('map-error').hidden = true;
        map.removeLayer(other);
        layer.addTo(map);
        for (const key of ['satellite', 'streets']) {
            $(key).classList.toggle('active', key === id);
            $(key).setAttribute('aria-pressed', String(key === id));
        }
    });
function searchMessage(text) { const div = document.createElement('div'); div.className = 'search-message'; div.textContent = text; $('search-results').replaceChildren(div); $('search-results').hidden = false; }
$('search-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = $('search').value.trim();
    if (!query)
        return;
    searchController?.abort();
    searchController = new AbortController();
    const controller = searchController;
    const pair = query.match(/^\s*(-?\d+(?:\.\d+)?)\s*[,;]\s*(-?\d+(?:\.\d+)?)\s*$/);
    if (pair) {
        const lat = Number(pair[1]), lng = Number(pair[2]);
        if (!moroccoBounds.contains([lat, lng])) {
            searchMessage('Choose coordinates within the Morocco area.');
            return;
        }
        map.setView([lat, lng], 12);
        $('search-results').hidden = true;
        return;
    }
    searchMessage('Looking for your place…');
    const timeout = setTimeout(() => controller.abort(), 12000);
    try {
        const response = await fetch(`https://nominatim.openstreetmap.org/search?format=jsonv2&limit=5&countrycodes=ma&bounded=1&viewbox=-13.3,36.2,-0.9,27.4&q=${encodeURIComponent(query)}`, { signal: controller.signal, headers: { Accept: 'application/json' } });
        if (!response.ok)
            throw new Error('Search unavailable');
        const places = await response.json();
        const results = places.filter(result => moroccoBounds.contains([Number(result.lat), Number(result.lon)]));
        if (!results.length) {
            searchMessage('No places found in Morocco. Try a city or coordinates.');
            return;
        }
        $('search-results').replaceChildren();
        results.forEach(result => {
            const button = document.createElement('button');
            button.type = 'button';
            button.textContent = result.display_name;
            button.addEventListener('click', () => {
                const box = result.boundingbox?.map(Number);
                if (box?.length === 4)
                    map.fitBounds([[box[0], box[2]], [box[1], box[3]]], { padding: [60, 65], maxZoom: 14 });
                else
                    map.setView([Number(result.lat), Number(result.lon)], 12);
                $('search').value = result.display_name.split(',').slice(0, 2).join(',');
                $('search-results').hidden = true;
            });
            $('search-results').append(button);
        });
        $('search-results').hidden = false;
    }
    catch {
        searchMessage('Place search is unavailable. Try coordinates, such as 33.49, -6.50.');
    }
    finally {
        clearTimeout(timeout);
    }
});
document.addEventListener('click', e => { if (e.target instanceof Element && !e.target.closest('.search-wrap'))
    $('search-results').hidden = true; });
$('help').addEventListener('click', () => $('help-dialog').showModal());
for (const id of ['close-help', 'got-it'])
    $(id).addEventListener('click', () => $('help-dialog').close());
$('help-dialog').addEventListener('click', e => { const dialog = $('help-dialog'); if (e.target === dialog) {
    const b = dialog.getBoundingClientRect();
    if (e.clientX < b.left || e.clientX > b.right || e.clientY < b.top || e.clientY > b.bottom)
        dialog.close();
} });
document.addEventListener('keydown', e => {
    if ((e.target instanceof HTMLElement && ['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) || $('help-dialog').open)
        return;
    if (e.key === '/') {
        e.preventDefault();
        $('search').focus();
    }
    if (!drawing) {
        if (e.key === 'Escape' && !$('tools-panel').hidden) {
            setToolsOpen(false);
            $('tools-toggle').focus();
        }
        return;
    }
    if (e.key === 'Enter') {
        e.preventDefault();
        finish();
    }
    if (e.key === 'Escape')
        $('cancel').click();
    if (e.key === 'Backspace' || ((e.ctrlKey || e.metaKey) && e.key === 'z')) {
        e.preventDefault();
        $('undo').click();
    }
});
new ResizeObserver(() => { map.invalidateSize(); constrainView(); }).observe($('map'));
try {
    const stored = JSON.parse(localStorage.getItem(storageKey) ?? 'null');
    const isPoint = (value) => typeof value === 'object' && value !== null && 'lat' in value && 'lng' in value && typeof value.lat === 'number' && typeof value.lng === 'number';
    if (Array.isArray(stored) && stored.length <= 10000 && stored.every(isPoint) && validPolygon(stored) && stored.every(point => moroccoBounds.contains(point))) {
        points = stored;
        setDrawing(false);
    }
}
catch { /* Start with an empty map when stored data is invalid or unavailable. */ }
render();
//# sourceMappingURL=app.js.map