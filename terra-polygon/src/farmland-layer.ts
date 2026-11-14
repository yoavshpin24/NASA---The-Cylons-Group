import { element } from './dom.js';
import { L } from './leaflet.js';
import type { LatLng, LeafletMouseEvent, Map, TileLayer } from 'leaflet';
import type { FarmlandMetadata, FieldProperties, HoverResponse } from './types.js';

// Field outlines are tiled; only the field under the pointer becomes a vector.
export function attachFarmland(map: Map, isDrawing: () => boolean) {
  const status = element('farmland-status');
  const toggle = element('farmland-toggle');
  const focus = element('farmland-focus');
  let metadata: FarmlandMetadata | undefined, layer: TileLayer | undefined;
  let timer: ReturnType<typeof setTimeout> | undefined, controller: AbortController | undefined;
  let generation = 0, moving = false;
  map.createPane('farmland').style.zIndex = '350';
  map.getPane('farmland')!.style.pointerEvents = 'none';
  map.createPane('field-highlight').style.zIndex = '390';
  map.getPane('field-highlight')!.style.pointerEvents = 'none';
  const highlight = L.geoJSON<FieldProperties>(undefined, {
    pane: 'field-highlight', interactive: false,
    style: {color: '#72f2ef', weight: 3, fillColor: '#72f2ef', fillOpacity: .25}
  }).addTo(map);
  const tooltip = L.tooltip({className: 'field-tooltip', direction: 'top', offset: [0, -14], opacity: 1});

  function clearHover() {
    generation++;
    clearTimeout(timer);
    controller?.abort();
    highlight.clearLayers();
    tooltip.remove();
  }

  function readyMessage() {
    if (metadata) status.textContent = toggle.checked
      ? `${metadata.count.toLocaleString()} fields · hover to inspect`
      : 'Field boundaries hidden';
  }

  function tooltipContent(properties: FieldProperties): HTMLDivElement {
    const content = document.createElement('div');
    const title = document.createElement('strong');
    title.textContent = `Field #${properties.id.toLocaleString()}`;
    content.append(title);
    const rows = document.createElement('dl');
    const score = (value: number | null): string => typeof value==='number'&&Number.isFinite(value) ? value.toFixed(3) : 'Not available';
    const hectares = properties.area_m2 / 10000;
    const date = properties.time?.slice(0, 10) || 'Not available';
    for (const [label, value] of [
      ['Label', properties.label || 'field'],
      ['Area ≈', `${hectares.toLocaleString(undefined, {maximumFractionDigits: 2})} ha`],
      ['Mean confidence', score(properties.confidence_mean)],
      ['Median confidence', score(properties.confidence_median)],
      ['Minimum confidence', score(properties.confidence_min)],
      ['Dataset date', date],
      ['Tile', properties.chunk_id || 'Not available']
    ]) {
      const key = document.createElement('dt'), text = document.createElement('dd');
      key.textContent = label; text.textContent = value;
      rows.append(key, text);
    }
    content.append(rows);
    return content;
  }

  async function inspect(latlng: LatLng, requestGeneration: number): Promise<void> {
    controller = new AbortController();
    try {
      const query = new URLSearchParams({lat: String(latlng.lat), lng: String(latlng.lng)});
      const response = await fetch(`/api/farmland/hover?${query}`, {signal: controller.signal});
      if (!response.ok) throw new Error('Field details unavailable');
      const {feature}: HoverResponse = await response.json();
      if (generation !== requestGeneration || isDrawing() || moving || !toggle.checked) return;
      readyMessage();
      highlight.clearLayers(); tooltip.remove();
      if (!feature) return;
      highlight.addData(feature);
      tooltip.setLatLng(latlng).setContent(tooltipContent(feature.properties)).addTo(map);
    } catch (error) {
      if (!(error instanceof DOMException&&error.name==='AbortError') && generation === requestGeneration) {
        highlight.clearLayers(); tooltip.remove();
        status.textContent = 'Field details unavailable · try hovering again';
      }
    }
  }

  map.on('mousemove', (event: LeafletMouseEvent) => {
    if (!metadata || !toggle.checked || isDrawing() || moving) return;
    clearHover();
    const requestGeneration = generation;
    timer = setTimeout(() => inspect(event.latlng, requestGeneration), 100);
  });
  map.on('click', (event: LeafletMouseEvent) => {
    if (!metadata || !toggle.checked || isDrawing() || moving) return;
    clearHover();
    inspect(event.latlng, generation); // Also inspect fields on touch devices.
  });
  map.on('mouseout', clearHover);
  map.on('movestart', () => { moving = true; clearHover(); });
  map.on('moveend', () => { moving = false; });

  function focusFields() {
    if (!metadata) { map.setView([33.49, -6.5], 10); return; }
    const [west, south, east, north] = metadata.bounds;
    map.fitBounds([[south, west], [north, east]], {padding: [50, 65], maxZoom: 11});
  }
  focus.addEventListener('click', focusFields);
  toggle.addEventListener('change', () => {
    clearHover();
    if (layer) toggle.checked ? layer.addTo(map) : layer.remove();
    readyMessage();
  });

  fetch('/api/farmland/meta').then(async response => {
    if (!response.ok) throw new Error('Field layer unavailable');
    metadata = await response.json() as FarmlandMetadata;
    const [west, south, east, north] = metadata.bounds;
    layer = L.tileLayer('/api/farmland/tiles/{z}/{x}/{y}.png', {
      pane: 'farmland', bounds: [[south, west], [north, east]],
      minZoom: 2, maxZoom: 19, noWrap: true, updateWhenIdle: true,
      attribution: 'Field boundaries · N33W007 · 2025'
    });
    layer.on('tileerror', () => { status.textContent = 'Some boundaries could not load · pan or zoom to retry'; });
    layer.on('load', readyMessage);
    if (toggle.checked) layer.addTo(map);
    toggle.disabled = false; focus.disabled = false;
    readyMessage();
  }).catch(() => {
    status.textContent = 'Field boundaries unavailable · drawing is still available';
    toggle.disabled = true; focus.disabled = true;
  });

  return {focus: focusFields, onDrawingChange: clearHover};
}
