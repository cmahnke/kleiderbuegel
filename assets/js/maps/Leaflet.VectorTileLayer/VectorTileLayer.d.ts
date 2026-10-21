/*
 * Type declaration for the vendored Leaflet.VectorTileLayer fork
 * (VectorTileLayer.js stays plain JavaScript and is bundled by esbuild).
 */

import type { Map as LeafletMap } from 'leaflet';

export interface VectorTileFeatureLike {
  type: number;
  properties?: FeatureProperties | null;
  id?: number | string;
  loadGeometry(): Array<Array<{ x: number; y: number }>>;
}

export interface VectorTileStyleResult {
  stroke?: boolean;
  fill?: boolean;
  color?: string;
  weight?: number;
  opacity?: number;
  fillColor?: string;
  fillOpacity?: number;
  radius?: number;
  dashArray?: string;
  lineCap?: string;
  lineJoin?: string;
}

export type VectorTileStyleFn = (
  properties: FeatureProperties,
  zoom: number,
  geometry?: number[]
) => VectorTileStyleResult | VectorTileStyleResult[] | null;

export interface VectorTileFeatureLayerResult {
  icon: {
    options: {
      svg?: SVGElement;
      iconSize?: number[];
      iconAnchor?: number[];
    };
  };
}

export type VectorTileFeatureStyleFn = (
  this: VectorTileLayerOptions,
  feature: VectorTileFeatureLike,
  layerName: string,
  zoom: number,
  tile: { x: number; y: number; z: number }
) => VectorTileFeatureLayerResult | null;

export interface VectorTileLayerOptions {
  attribution?: string;
  vectorTileLayerStyles?: Record<string, VectorTileStyleFn>;
  renderer?: string;
  minZoom?: number;
  maxZoom?: number;
  minDetailZoom?: number;
  maxDetailZoom?: number;
  pane?: string;
  reuseTiles?: boolean;
  layers?: string[];
  featureToLayer?: (
    feature: VectorTileFeatureLike,
    layerName: string,
    pxPerExtent: { x: number; y: number },
    options?: unknown
  ) => unknown;
  filter?: (feature: VectorTileFeatureLike, layerName: string) => boolean;
  getFeatureId?: (feature: VectorTileFeatureLike) => string | number | undefined;
  subdomains?: string | string[];
  zoomOffset?: number;
  zoomReverse?: boolean;
  style?: VectorTileFeatureStyleFn;
  '*'?: { cache?: LabelCache };
}

export interface VectorTileLayerInstance {
  addTo(map: LeafletMap): this;
  on(event: 'tileload', handler: (event: { tile: { x: number; y: number; z: number } }) => void): this;
}

declare function vectorTileLayer(url: string, options: VectorTileLayerOptions): VectorTileLayerInstance;

export default vectorTileLayer;
