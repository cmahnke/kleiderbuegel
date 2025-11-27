import L from 'leaflet';
import 'leaflet.markercluster';
import 'leaflet.vectorgrid';
import '@maplibre/maplibre-gl-leaflet';

import * as style from './kleiderbügel-style.json';

var layers = {"shortbread": style};

// TODO: This wil certainly fail with any other OpenLayers marker structure
function leafletIcon(olIconStyle) {
  const src = olIconStyle.src;
  const scale = olIconStyle.scale || 1;
  const olAnchor = olIconStyle.anchor || [0.5, 0.5];

  if (!src) {
    return Promise.resolve(null);
  }

  return new Promise((resolve) => {
    const img = new Image();
    
    img.onload = () => {
      const naturalWidth = img.naturalWidth;
      const naturalHeight = img.naturalHeight;

      const finalWidth = naturalWidth * scale;
      const finalHeight = naturalHeight * scale;

      let anchorX = olAnchor[0];
      let anchorY = olAnchor[1];

      if (olIconStyle.anchorXUnits === 'fraction' || anchorX <= 1) {
        anchorX = finalWidth * anchorX;
      }
      if (olIconStyle.anchorYUnits === 'fraction' || anchorY <= 1) {
        anchorY = finalHeight * anchorY;
      }
      
      const leafletIcon = L.icon({
        iconUrl: src,
        iconSize: [finalWidth, finalHeight],
        iconAnchor: [anchorX, anchorY],
        popupAnchor: [anchorX, anchorY] 
      });
      
      resolve(leafletIcon);
    };

    img.onerror = () => {
      resolve(null);
    };

    img.src = src;
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
    
    var map = L.map(element, {
        maxBounds: [[180, -Infinity], [-180, Infinity]],
        maxBoundsViscosity: 1,
        zoomControl: false,
        renderer: L.svg(),
        minZoom: 1,
        maxZoom: 15,
        center: center,
        zoom: 5,
        zoomSnap: .1
    });    

    if (bbox && bbox.length === 4) {
        const bounds = [[bbox[1], bbox[0]], [bbox[3], bbox[2]]];
        map.fitBounds(bounds, { padding: [30, 30] });
    }
    
    var gl = L.maplibreGL({
        style: layers[style]
    }).addTo(map);
    

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

    if (bbox && bbox.length === 4) {
        // bbox is [minLon, minLat, maxLon, maxLat]
        // Leaflet bounds are [[minLat, minLon], [maxLat, maxLon]]
        const bounds = [[bbox[1], bbox[0]], [bbox[3], bbox[2]]];
        map.fitBounds(bounds, { padding: [30, 30] });
    } else {
        map.fitBounds(geoJsonLayer.getBounds(), { padding: [30, 30] });
    }
    // TODO remove this from partial
    const popupContainer = document.getElementById(element + '-popup');
    if (popupContainer) {
        popupContainer.remove();
    }

    setTimeout(function(){
        map.invalidateSize(true);}
    ,1000)

    return map;
}
