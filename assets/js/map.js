import Map from 'ol/Map';
import MVT from 'ol/format/MVT.js';
import VectorTileLayer from 'ol/layer/VectorTile.js';
import VectorTileSource from 'ol/source/VectorTile.js';
import View from 'ol/View.js';
import {apply} from 'ol-mapbox-style';
import {boundingExtent} from 'ol/extent';
import {style} from "./style.js"
import * as bbox from './bbox.json';

const layer = new VectorTileLayer({
  source: new VectorTileSource({
    attributions: '&copy; OpenStreetMap contributors and Natural Earth',
    maxZoom: 13,
    url: 'tiles/{z}/{x}/{y}.pbf',
    format: new MVT()
  }),
});

const map = new Map({
  layers: [
    layer,
  ],
  target: 'map',
  view: new View({
    center: [9.93,51.55],
    zoom: 3,
  }),
  extent: boundingExtent(bbox)
});

apply(map, style);

export default map;
