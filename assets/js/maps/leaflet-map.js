import L from 'leaflet';
import 'leaflet.markercluster';
import 'leaflet.vectorgrid';
import 'mapbox-gl-leaflet';

import * as style from './kleiderbügel-style.json';

var layers = {};

layers['wiki'] = L.tileLayer('https://maps.wikimedia.org/osm-intl/{z}/{x}/{y}.png?lang=en', {
    attribution: '&copy; <a href="http://openstreetmap.org/copyright">OpenStreetMap contributors</a>'
});

layers['osm'] = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'
});

var vectorStyles = {};

vectorStyles['shortbread'] = L.mapboxGL({
    // The style can be a URL to a JSON file or a style object
    style: style
})

export function initMap(element, url, source, cluster, marker, style, bbox) {

  // Languages
  var lang = 'en';
  if (document.documentElement.lang !== undefined) {
      /* TODO: Check for lang locale combinations here: "de-de" instead of "de" will currently break this. */
      lang = document.documentElement.lang;
  }
  var toolTips = { 'de': {'zoomIn': 'Vergrößern', 'zoomOut': 'Verkleinern', 'fullscreen': 'Vollbildansicht', 'rotate': 'Rotation zurücksetzen', 'rotateLeft': '90° nach links drehen', 'rotateRight': '90° nach rechst drehen'},
                   'en': {'zoomIn': 'Zoom in', 'zoomOut': 'Zoom out', 'fullscreen': 'Toggle full-screen'}};

    // Base layer
    var baseLayer;
    if (style !== undefined && style in vectorStyles) {
        baseLayer = vectorStyles[style];
    } else if (source !== undefined && source !== '') {
        if (source in layers) {
            baseLayer = layers[source];
        } else {
            baseLayer = L.tileLayer(source);
        }
    } else {
      baseLayer = layers['osm'];
    }

    var map = L.map(element, {
        layers: [baseLayer],
        zoomControl: false, // We add it with custom tooltips later
        renderer: L.svg() // Use SVG renderer as requested
    });

    L.control.zoom({
        zoomInTitle: toolTips[lang]['zoomIn'],
        zoomOutTitle: toolTips[lang]['zoomOut']
    }).addTo(map);

    fetch(url)
        .then(function(response) {
            response
                .json()
                .then(function(geojson) {
                    let geoJsonLayer;
                    let markerOptions = {};

                    if (marker) {
                        if (typeof marker !== 'object') {
                            try {
                                marker = JSON.parse(marker);
                            } catch (e) {
                                console.warn(`Can't parse marker ${marker}`);
                            }
                        }
                        markerOptions.icon = L.icon(marker);
                    }

                    if (cluster !== undefined && cluster) {
                        geoJsonLayer = L.markerClusterGroup({
                            // Other cluster options can go here
                        });
                        const markers = L.geoJSON(geojson, {
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
                        geoJsonLayer.addLayer(markers);
                    } else {
                        geoJsonLayer = L.geoJSON(geojson, {
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
                    }

                    map.addLayer(geoJsonLayer);

                    if (bbox && bbox.length === 4) {
                        // bbox is [minLon, minLat, maxLon, maxLat]
                        // Leaflet bounds are [[minLat, minLon], [maxLat, maxLon]]
                        const bounds = [[bbox[1], bbox[0]], [bbox[3], bbox[2]]];
                        map.fitBounds(bounds, { padding: [30, 30] });
                    } else {
                        map.fitBounds(geoJsonLayer.getBounds(), { padding: [30, 30] });
                    }
                })
                .catch(function(body) {
                    console.log('Could not read GeoJSON. ' + body);
                });
        })
        .catch(function() {
            console.log('Could not read data from URL.');
        });

    // Remove popup elements if they exist, as Leaflet handles its own popups
    const popupContainer = document.getElementById(element + '-popup');
    if (popupContainer) {
        popupContainer.remove();
    }

    return map;
}
