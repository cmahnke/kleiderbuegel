import L from 'leaflet';
import 'leaflet.markercluster';
import vectorTileLayer from 'leaflet-vector-tile-layer';
import '@maplibre/maplibre-gl-leaflet';
import { leafletIcon, mapboxToLeafletVectorGrid } from './leaflet-util';
import LanguageDetector from 'i18next-browser-languagedetector';

import * as mapStyle from './kleiderbügel-style.json';

const fontPath = undefined;
const defaultFonts = "Space Grotesk Variable";

const languageDetector = new LanguageDetector(null, {order: ['querystring',  'navigator', 'htmlTag', 'path'],
    lookupQuerystring: 'lang',
    htmlTag: document.documentElement,
});
languageDetector.detect();
const lang = languageDetector.detect();

var layers = {"shortbread": mapStyle};

if (fontPath !== undefined) {
    layers["shortbread"]["ol:webfonts"] = fontPath;
    layers["shortbread"].metadata["ol:webfonts"] = fontPath;
} else {
    layers["shortbread"]["ol:webfonts"] = defaultFonts;
    layers["shortbread"].metadata["ol:webfonts"] = defaultFonts;
}

const padding = [30, 30];

const vectorLayerImpl = "vectorgrid";

// See https://stackoverflow.com/a/61511955
function waitForElm(selector) {
    return new Promise(resolve => {
        if (document.querySelector(selector)) {
            return resolve(document.querySelector(selector));
        }

        const observer = new MutationObserver(mutations => {
            if (document.querySelector(selector)) {
                observer.disconnect();
                resolve(document.querySelector(selector));
            }
        });

        // If you get "parameter 1 is not of type 'Node'" error, see https://stackoverflow.com/a/77855838/492336
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    });
}

export async function initMap(element, geojson, source, cluster, marker, style, bbox) {
    console.log(bbox);
    if (!style in layers) {
        throw new Error(`'${style}' is not a valid style.`);
    }

    let markerOptions = {};

    if (marker) {
        //TODO: Check if we need to be sync her to be not outrunned by the layout process.
        let leafletMarker = await leafletIcon(marker)

        markerOptions.icon = leafletMarker
    }

    let geoJsonLayer, center;
    if (geojson !== undefined) {
        geojson = JSON.parse(geojson);
        geoJsonLayer = L.geoJson(geojson, {
            pointToLayer: function (feature, latlng) {
                return L.marker(latlng, markerOptions);
            },
            onEachFeature: function (feature, layer) {
                if (feature.properties && (feature.properties.name || feature.properties.popupContent)) {
                    let popupContent = '';
                    if (feature.properties.name) {
                        popupContent += '<h1>' + feature.properties.name + '</h1>';
                    }
                    if (feature.properties.popupContent) {
                        popupContent += feature.properties.popupContent;
                    }
                    layer.bindPopup(popupContent);
                }
            }
        });
        center = geoJsonLayer.getBounds().getCenter();
    }

    let map, mapElem;
    mapElem = document.querySelector(element);
    //waitForElm(element).then((elm) => {
    //    console.log(`Found element ${elm}`);
    //    mapElem = elm;
        map = L.map(mapElem, {
            maxBounds: [[180, -Infinity], [-180, Infinity]],
            maxBoundsViscosity: 1,
            zoomControl: false,
            renderer: L.svg(),
            minZoom: 1,
            maxZoom: 15,
            center: center,
            zoom: 3,
            zoomSnap: .1,
            preferCanvas: false
        });
    //});


    let bounds;
    if (bbox && bbox.length === 4) {
        //bounds = [[bbox[1], bbox[0]], [bbox[3], bbox[2]]];
        bounds = [[bbox[3], bbox[2]], [bbox[1], bbox[0]]];
        map.fitBounds(bounds, { padding: padding });
    }

    var vectorLayer;

    if (vectorLayerImpl === "maplibre") {
      vectorLayer = L.maplibreGL({
          style: layers[style]
      }).addTo(map);
    } else if (vectorLayerImpl === "vectorgrid") {
      const vectorTileUrl = layers[style].sources["versatiles-" + style].tiles[0];
      const vectorTileAttribution = layers[style].sources["versatiles-" + style].attribution;

      // Handle background layer
      const backgroundLayer = mapStyle.layers.find(l => l.type === 'background');
      if (backgroundLayer && backgroundLayer.paint?.['background-color']) {
          mapElem.style.backgroundColor = backgroundLayer.paint['background-color'];
      }

      // Example of how to use the new disabledFeatures parameter.
      const disabledRules = {
        'water_lines': [
            {kind: 'basin'},
            {tunnel: true},
            {tunnel: 'culvert'}
        ],
        'water_polygons': [
            {tunnel: true},
            {tunnel: 'culvert'}
        ],
        'addresses': [],
        'pois': [],
        'public_transport': [],
        'streets':[
            { kind: 'narrow_gauge'},
            { kind: 'cycleway' },
            { bicycle: 'designated' }
        ],
        'street_polygons': [],
        'street_labels': []
      };

      // Create a dedicated pane for labels to ensure they appear on top.
      map.createPane('labels');
      map.getPane('labels').style.zIndex = 650; // Higher than the default overlay pane (400)
      map.getPane('labels').style.pointerEvents = 'none'; // Allow clicks to pass through to layers below


      // First, create the styling for polygons and lines, but disable label drawing.
      const vectorTileStyling = mapboxToLeafletVectorGrid(mapStyle, map, disabledRules, false);
      console.log(vectorTileStyling, vectorTileStyling);
      
      vectorTileStyling['*'] = function(properties, zoom) {
        console.warn("Unhandled", properties, zoom);
      }

      const vectorTileOptions = {
        attribution: vectorTileAttribution,
        vectorTileLayerStyles: vectorTileStyling,
        maxDetailZoom: 14,
        maxZoom: 20,
      };

      vectorLayer = vectorTileLayer(vectorTileUrl, vectorTileOptions).addTo(map);

      // Label layer - just a hack for GridTile
    //   const labelTileStyling = mapboxToLeafletVectorGrid(mapStyle, map, disabledRules, true);
    //   const labelVectorTileOptions = {
    //     attribution: vectorTileAttribution,
    //     vectorTileLayerStyles: labelTileStyling,
    //     maxZoom: 20,
    //     maxDetailZoom: 14,
    //     pane: 'labels'
    //   };

    //   let labelCache = [];
    //   labelVectorTileOptions.getFeatureId = (f) => f.properties.name;
    //   const labelVectorLayer = vectorTileLayer(vectorTileUrl, labelVectorTileOptions).addTo(map);
    //   labelVectorLayer.on('loading', () => { labelCache = []; });
    //   labelTileStyling['*'] = { cache: labelCache };
    

    }

    if (cluster !== undefined && cluster) {
        let markers = L.markerClusterGroup({
            //showCoverageOnHover: false,
            maxClusterRadius: 40,
            iconCreateFunction: function(cluster) {
                const count = cluster.getChildCount();
                const icon = markerOptions.icon;

                if (!icon) {
                    return L.divIcon({ html: '<b>' + count + '</b>', className: 'marker-cluster' });
                }

                const iconUrl = icon.options.iconUrl;
                const iconSize = icon.options.iconSize;

                return L.divIcon({
                    html: `<img src="${iconUrl}" style="width:${iconSize[0]}px;height:${iconSize[1]}px;"><span class="cluster-count">${count}</span>`,
                    className: 'custom-marker-cluster',
                    iconSize: iconSize
                });
            }
        });
        markers.addLayer(geoJsonLayer);
        map.addLayer(markers);
    } else {
        map.addLayer(geoJsonLayer);
    }

    if (bounds !== undefined) {
        map.fitBounds(bounds, { padding: padding });
    } else {
        map.fitBounds(geoJsonLayer.getBounds(), { padding: padding });
    }

    /*
   const resizeObserver = new ResizeObserver(() => {
        map.invalidateSize();
        if (bounds !== undefined) {
            map.fitBounds(bounds, { padding: padding });
        }
    });
    if (mapElem !== null) {
        resizeObserver.observe(mapElem);
    } else {
        console.error(`Couldn't set up resize observer for ${element}`)
    }
    */

    return map;
}
