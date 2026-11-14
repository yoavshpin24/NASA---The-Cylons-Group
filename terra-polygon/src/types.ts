import type { Feature, Polygon } from 'geojson';

export interface Point {
  lat: number;
  lng: number;
}

export type CoordinateFormat = 'table' | 'geojson';
export type ExportFormat = 'geojson' | 'csv';

export interface FieldProperties {
  id: number;
  label: string | null;
  time: string | null;
  chunk_id: string | null;
  confidence_mean: number | null;
  confidence_median: number | null;
  confidence_min: number | null;
  area_m2: number;
}

export type FieldFeature = Feature<Polygon, FieldProperties>;

export interface FarmlandMetadata {
  ready: true;
  count: number;
  bounds: [west: number, south: number, east: number, north: number];
  source: string;
  overview_zoom: number;
  overview_origin: [number, number];
  crs: 'EPSG:4326';
}

export interface HoverResponse {
  feature: FieldFeature | null;
}

export interface PlaceResult {
  lat: string;
  lon: string;
  display_name: string;
  boundingbox?: [south: string, north: string, west: string, east: string];
}
