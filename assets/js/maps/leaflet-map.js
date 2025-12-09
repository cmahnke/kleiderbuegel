import L from 'leaflet';
import 'leaflet.markercluster';
import vectorTileLayer from './Leaflet.VectorTileLayer/VectorTileLayer';
import '@maplibre/maplibre-gl-leaflet';
import { leafletIcon, mapboxToLeafletVectorGrid, getFeatureLayer } from './leaflet-util';
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

    let bounds, maxBounds= [[180, -Infinity], [-180, Infinity]];
    if (bbox && bbox.length === 4) {
        //bounds = [[bbox[1], bbox[0]], [bbox[3], bbox[2]]];
        bounds = [[bbox[3], bbox[2]], [bbox[1], bbox[0]]];
        
        maxBounds = bounds;
    }


    let map, mapElem;
    mapElem = document.querySelector(element);
    //waitForElm(element).then((elm) => {
    //    console.log(`Found element ${elm}`);
    //    mapElem = elm;
        map = L.map(mapElem, {
            maxBounds: maxBounds,
            //maxBoundsViscosity: 1,
            zoomControl: false,
            renderer: L.svg(),
            minZoom: 1,
            maxZoom: 15,
            center: center,
            zoom: 3,
            zoomSnap: .1,
            preferCanvas: false,
            lang: lang
        });
    //});

    if (bbox && bbox.length === 4) {
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

      map.createPane('labels');
      map.getPane('labels').style.zIndex = 500;
      map.getPane('labels').style.pointerEvents = 'none';

      map.createPane('clusters');
      map.getPane('clusters').style.zIndex = 650;

      // First, create the styling for polygons and lines, but disable label drawing.
      const vectorTileStyling = mapboxToLeafletVectorGrid(mapStyle, map, false);
      //console.log(vectorTileStyling, `${Object.keys(vectorTileStyling)}`);

      const vectorTileOptions = {
        attribution: vectorTileAttribution,
        vectorTileLayerStyles: vectorTileStyling,
        minDetailZoom: 4,
        maxDetailZoom: 14,
        maxZoom: 20,
        bounds: bounds,
        reuseTiles : true,
        layers: ["ocean", "water_polygons", "land", "water_lines", "dam_polygons", "dam_lines", "pier_polygons", "pier_lines", "sites", "street_polygons", "streets", "buildings", "bridges", "boundaries"]
      };

      vectorLayer = vectorTileLayer(vectorTileUrl, vectorTileOptions).addTo(map);

      // Label layer - just a hack for GridTile
      const labelTileStyling = getFeatureLayer(mapStyle, map)
      const labelCache = {};
      const labelVectorTileOptions = {
        style: labelTileStyling,
        //featureToLayer: labelsLayer,
        minDetailZoom: 7,
        maxDetailZoom: 14,
        maxZoom: 20,
        pane: 'labels',
        bounds: bounds,
        reuseTiles : true,
        layers: ["place_labels", "boundary_labels", "street_labels"],
        // Pass a cache object to the styling function via the '*' property.
        '*': { cache: labelCache }
      };

       const labelVectorLayer = vectorTileLayer(vectorTileUrl, labelVectorTileOptions)
       
       /*
       console.log(labelVectorLayer);
      labelVectorLayer.prototype.applyImageStyle = function(layer, style) {
        if (style.divIcon) {
          // If our style function returns a divIcon, use it.
          layer.setIcon(style.divIcon);
        } else if (style.icon) {
          // Fallback to the original behavior if a regular icon is provided.
          layer.setIcon(style.icon);
        }
      };
      */

       labelVectorLayer.addTo(map);

       // Clear the label cache for a tile when it's loaded to start fresh.
       labelVectorLayer.on('tileload', (e) => {
         const tileKey = e.tile.x + ':' + e.tile.y + ':' + e.tile.z;
         labelCache[tileKey] = [];
       });


      
    }

    if (cluster !== undefined && cluster) {
        let markers = L.markerClusterGroup({
            //showCoverageOnHover: false,
            maxClusterRadius: 40,
            pane: 'clusters', // Assign clusters to the dedicated top pane.
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

   const resizeObserver = new ResizeObserver(() => {
        map.invalidateSize();
        if (bounds !== undefined) {
            map.fitBounds(bounds, { padding: padding });
            console.log("Resized map and fit to bounds: ", map.getBounds(), " expected: ", bounds, mapElem.clientWidth, mapElem.clientHeight);
        }
    });
    if (mapElem !== null) {
        resizeObserver.observe(mapElem);
    } else {
        console.error(`Couldn't set up resize observer for`, mapElem)
    }


    return map;
}
