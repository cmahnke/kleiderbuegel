/*
 * Module declaration for the Leaflet API surface used by this site's
 * TypeScript sources. Types are structural; they intentionally cover only
 * what the map code touches. Mapped to the bare `leaflet` specifier via
 * `paths` in tsconfig.json.
 */

interface Point {
  x: number;
  y: number;
}

type LatLngTuple = [number, number];

interface LatLng {
  lat: number;
  lng: number;
}

type LatLngExpression = LatLng | LatLngTuple;

interface LatLngBounds {
  getCenter(): LatLng;
}

type LatLngBoundsExpression = LatLngBounds | LatLngTuple[];

interface GeoJSONFeatureLike {
  type?: string;
  geometry?: unknown;
  properties?: FeatureProperties | null;
  id?: string | number;
}

interface IconOptions {
  iconUrl?: string;
  iconSize?: number[];
  iconAnchor?: number[];
  popupAnchor?: number[];
  svgElement?: SVGElement | null;
  [key: string]: unknown;
}

interface Icon {
  options: IconOptions;
}

type DivIcon = Icon;

interface Layer {
  addTo(target: Map): this;
  bindPopup(content: string): this;
  getBounds(): LatLngBounds;
  on(event: string, handler: (event: unknown) => void): this;
}

type Marker = Layer;

type Renderer = Layer;

type GeoJSONLayer = Layer;

interface MarkerCluster {
  getChildCount(): number;
}

interface MarkerClusterGroupOptions {
  maxClusterRadius?: number;
  pane?: string;
  iconCreateFunction?: (cluster: MarkerCluster) => DivIcon;
}

interface MarkerClusterGroup extends Layer {
  addLayer(layer: Layer): this;
}

interface MapOptions {
  maxBounds?: LatLngBoundsExpression;
  zoomControl?: boolean;
  renderer?: Renderer;
  minZoom?: number;
  maxZoom?: number;
  center?: LatLngExpression;
  zoom?: number;
  zoomSnap?: number;
  preferCanvas?: boolean;
  lang?: string;
}

interface FitBoundsOptions {
  padding?: [number, number];
}

interface Map {
  options: MapOptions;
  fitBounds(bounds: LatLngBoundsExpression, options?: FitBoundsOptions): void;
  addLayer(layer: Layer): this;
  createPane(name: string): void;
  getPane(name: string): HTMLElement | undefined;
  invalidateSize(): void;
  getBounds(): LatLngBounds;
  latLngToContainerPoint(latlng: LatLngExpression): Point;
}

interface GeoJSONOptions {
  pointToLayer?: (feature: GeoJSONFeatureLike, latlng: LatLng) => Layer;
  onEachFeature?: (feature: GeoJSONFeatureLike, layer: Layer) => void;
}

interface IconConstructor {
  new (options?: IconOptions): Icon;
}

interface IconStatic {
  extend(proto: {
    options?: IconOptions;
    createIcon?: (this: { options: IconOptions }, oldIcon?: HTMLElement) => HTMLElement;
  }): IconConstructor;
}

interface SVGNamespace {
  create(tag: string): SVGElement;
}

function geoJson(data: unknown, options?: GeoJSONOptions): GeoJSONLayer;

function marker(latlng: LatLngExpression, options?: { icon?: Icon }): Marker;

function icon(options: IconOptions): Icon;

function divIcon(options: { html?: string; className?: string; iconSize?: number[] }): DivIcon;

function map(container: HTMLElement | string | null, options?: MapOptions): Map;

function svg(): Renderer;

function markerClusterGroup(options?: MarkerClusterGroupOptions): MarkerClusterGroup;

function maplibreGL(options?: { style?: unknown }): Layer;

const Icon: IconStatic;

const SVG: SVGNamespace;

const L: {
  geoJson: typeof geoJson;
  marker: typeof marker;
  icon: typeof icon;
  divIcon: typeof divIcon;
  map: typeof map;
  svg: typeof svg;
  markerClusterGroup: typeof markerClusterGroup;
  maplibreGL: typeof maplibreGL;
  Icon: typeof Icon;
  SVG: typeof SVG;
};

export default L;
export {
  Point,
  LatLng,
  LatLngBounds,
  Icon,
  DivIcon,
  Layer,
  Marker,
  Renderer,
  GeoJSONLayer,
  MarkerCluster,
  MarkerClusterGroup,
  Map,
  IconOptions,
  GeoJSONOptions,
};
export { SVG };
