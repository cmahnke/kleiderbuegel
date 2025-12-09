import L from 'leaflet';
import {SVG} from "leaflet";
//from './Leaflet.VectorTileLayer/VectorTileLayer';

//import {VectorTileFeature} from "@mapbox/vector-tile";

// A custom L.Icon class that renders a provided SVG element.
const SvgIcon = L.Icon.extend({
  options: {
    // svgElement is the <g> element containing our label.
    svgElement: null,
  },

  createIcon: function (oldIcon) {
    const div = (oldIcon && oldIcon.tagName === 'DIV') ? oldIcon : document.createElement('div');
    const options = this.options;

    // The main container for the SVG.
    const svg = SVG.create('svg');
    svg.setAttribute('width', options.iconSize[0]);
    svg.setAttribute('height', options.iconSize[1]);
    svg.appendChild(options.svgElement);

    div.appendChild(svg);
    return div;
  }
});

// TODO: This wil certainly fail with any other OpenLayers marker structure
export function leafletIcon(olIconStyle) {
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

/**
 * A very basic Mapbox filter to function converter.
 * This is not a complete implementation of the Mapbox filter spec.
 * See https://docs.mapbox.com/mapbox-gl-js/style-spec/layers/#filter
 * @param {Array} filter - The Mapbox filter array.
 * @returns {function(object): boolean} A function that takes feature properties and returns true if the feature matches the filter.
 */
function createFilter(filter) {
  if (!filter) {
    return () => true;
  }

  return (properties, zoom) => {
    const operator = filter[0];

    switch (operator) {
      case '==':
      case '!=':
      case '>':
      case '>=':
      case '<':
      case '<=': {
        const key = filter[1];
        const value = filter[2];
        const propValue = Array.isArray(key) ? resolveValue(key, zoom, properties) : properties[key];
        if (operator === '==') return propValue == value;
        if (operator === '!=') return propValue != value;
        if (operator === '>') return propValue > value;
        if (operator === '>=') return propValue >= value;
        if (operator === '<') return propValue < value;
        if (operator === '<=') return propValue <= value;
        return false;
      }
      case 'in':
      case '!in': {
        const key = filter[1];
        const propValue = Array.isArray(key) ? resolveValue(key, zoom, properties) : properties[key];
        const values = filter.slice(2);
        const hasMatch = values.includes(propValue);
        return operator === 'in' ? hasMatch : !hasMatch;
      }
      case 'has':
        return properties.hasOwnProperty(filter[1]);
      case '!has':
        return !properties.hasOwnProperty(filter[1]);
      case 'all':
        return filter.slice(1).every(subFilter => createFilter(subFilter)(properties, zoom));
      default:
        console.warn(`Unsupported filter operator: ${operator}`);
        return true;
    }
  };
}

/**
 * A very basic Mapbox match expression evaluator.
 * @param {*} value The value to match.
 * @param {Array} args The arguments for the match expression.
 * @returns {*} The matched result or the default value.
 */
function match(value, args) {
  for (let i = 0; i < args.length - 1; i += 2) {
    const caseValue = args[i];
    const result = args[i + 1];
    if (Array.isArray(caseValue)) { // e.g. ["val1", "val2"]
      if (caseValue.includes(value)) return result;
    } else if (value === caseValue) {
      return result;
    }
  }
  // Return the default value
  return args[args.length - 1];
}

/**
 * Resolves a Mapbox GL style expression or literal value.
 * @param {*} value The value to resolve.
 * @param {number} zoom The current map zoom level.
 * @param {object} properties The properties of the feature.
 * @returns {*} The resolved value.
 */
function resolveValue(value, zoom, properties) {
  // Handle rgba/hsla color strings to extract opacity
  if (typeof value === 'string' && (value.startsWith('rgba') || value.startsWith('hsla'))) {
    const parts = value.split(',');
    if (parts.length === 4) {
      const alpha = parseFloat(parts[3]);
      const color = parts.slice(0, 3).join(',') + ')';
      // Return an object that the style handler can use
      return { color: color.replace('rgba', 'rgb').replace('hsla', 'hsl'), opacity: alpha };
    }
  }

  if (typeof value !== 'object' || value === null) {
    return value; // It's a literal
  }

  if (Array.isArray(value)) {
    // It's an expression
    const knownOperators = ['get', 'match'];
    if (typeof value[0] !== 'string' || !knownOperators.includes(value[0])) {
      // This is likely a literal array (e.g., for line-dasharray), not an expression.
      return value;
    }

    const [op, ...args] = value;
    switch (op) {
      case 'get':
        return properties[args[0]];
      case 'match': {
        const inputValue = resolveValue(args[0], zoom, properties);
        const branches = args.slice(1);
        for (let i = 0; i < branches.length - 1; i += 2) {
          const caseValue = branches[i];
          const result = branches[i + 1];
          if (Array.isArray(caseValue)) {
            if (caseValue.includes(inputValue)) return resolveValue(result, zoom, properties);
          } else if (inputValue === caseValue) {
            return resolveValue(result, zoom, properties);
          }
        }
        // Return the default value
        return resolveValue(branches[branches.length - 1], zoom, properties);
      }
      default:
        console.warn(`Unsupported expression operator: ${op}`);
        return value;
    }
  }

  if (value.stops) {
    // It's a zoom-based 'stops' expression
    const stops = value.stops;

    // Find the two stops the current zoom is between
    let lowerStop = stops[0];
    let upperStop = stops[stops.length - 1];

    if (zoom <= lowerStop[0]) {
      return resolveValue(lowerStop[1], zoom, properties);
    }
    if (zoom >= upperStop[0]) {
      return resolveValue(upperStop[1], zoom, properties);
    }

    for (let i = 0; i < stops.length - 1; i++) {
      if (zoom >= stops[i][0] && zoom < stops[i+1][0]) {
        lowerStop = stops[i];
        upperStop = stops[i+1];
        break;
      }
    }

    const lowerZoom = lowerStop[0];
    const upperZoom = upperStop[0];
    const lowerValue = lowerStop[1];
    const upperValue = upperStop[1];

    // If values are not numbers (e.g., colors), we can't interpolate. Use step logic.
    if (typeof lowerValue !== 'number' || typeof upperValue !== 'number') {
      return resolveValue(lowerValue, zoom, properties);
    }

    // Perform linear interpolation
    const zoomDiff = upperZoom - lowerZoom;
    const valueDiff = upperValue - lowerValue;
    const progress = (zoom - lowerZoom) / zoomDiff;

    const interpolatedValue = lowerValue + (progress * valueDiff);
    return interpolatedValue;
  }

  console.warn('Unsupported expression type:', value);
  return value;
}

export function mapboxToLeafletVectorGrid(mapboxStyle, map, drawLabels = true) {
  const lang = map.options.lang;
  const leafletStyle = {};

  if (!mapboxStyle || !mapboxStyle.layers) {
    return leafletStyle;
  }
  
  const layersBySourceLayer = {};

  // Group layers by source-layer
  mapboxStyle.layers.forEach((layer) => {
    // Background layer is handled separately
    if (layer.type === 'background') {
      return;
    }

    const sourceLayer = layer['source-layer'];
    if (!sourceLayer) {
      return;
    }
    if (!layersBySourceLayer[sourceLayer]) {
      layersBySourceLayer[sourceLayer] = [];
    }
    layersBySourceLayer[sourceLayer].push(layer);
  });

  for (const sourceLayer in layersBySourceLayer) {
    const layers = layersBySourceLayer[sourceLayer];

    // For each source-layer, create a single function that iterates through all corresponding Mapbox layers.
    leafletStyle[sourceLayer] = function(properties, zoom, geometry) {
      // The cache is passed via the '*' property in the style options for collision detection.
      const labelCache = leafletStyle['*']?.cache;

      const styles = [];

      // Iterate backwards to find the topmost layer that matches.
      // This correctly handles cases like 'road:outline' and 'road' where the top one should be rendered.
      // We now iterate forwards to collect styles from bottom to top.
      for (let i = 0; i < mapboxStyle.layers.length; i++) {
        const layer = mapboxStyle.layers[i];
        if (layer['source-layer'] !== sourceLayer) continue;
        const filter = createFilter(layer.filter);

        // Check if the layer is within the zoom range.
        if (layer.minzoom && zoom < layer.minzoom) {
          continue;
        }
        if (layer.maxzoom && zoom >= layer.maxzoom) {
          continue;
        }

        // If the filter for this layer matches the feature...
        if (filter(properties, zoom)) {
          const style = {};
          const paint = layer.paint || {}; 
          const layout = layer.layout || {};

          const visibility = resolveValue(layout.visibility, zoom, properties);
          if (visibility === 'none') {
            // This layer is not visible, so we skip it and see if another layer matches.
            continue;
          }

          switch (layer.type) {
            case 'fill':
              style.fill = true;
              const fillColor = resolveValue(paint['fill-color'], zoom, properties);
              if (typeof fillColor === 'object' && fillColor.color) {
                style.fillColor = fillColor.color;
                style.fillOpacity = fillColor.opacity;
              } else {
                style.fillColor = fillColor;
                // Only resolve fill-opacity if it wasn't part of an rgba color
                style.fillOpacity = resolveValue(paint['fill-opacity'], zoom, properties) ?? 1;
              }
              if (paint['fill-outline-color']) {
                style.color = resolveValue(paint['fill-outline-color'], zoom, properties);
                style.weight = 1; // Default weight
              } else {
                style.stroke = false;
              }
              break;
            case 'line':
              const lineColor = resolveValue(paint['line-color'], zoom, properties);
              if (typeof lineColor === 'object' && lineColor.color) {
                style.color = lineColor.color;
                style.opacity = lineColor.opacity;
              } else {
                style.color = lineColor;
                // Only resolve line-opacity if it wasn't part of an rgba color
                style.opacity = resolveValue(paint['line-opacity'], zoom, properties);
              }
              style.weight = resolveValue(paint['line-width'], zoom, properties);
              if (style.weight <= 0) {
                continue;
              }
              const dashArray = resolveValue(paint['line-dasharray'], zoom, properties);
              if (Array.isArray(dashArray)) style.dashArray = dashArray.join(' ');
              style.lineCap = resolveValue(layout['line-cap'], zoom, properties);
              style.lineJoin = resolveValue(layout['line-join'], zoom, properties);
              break;
            case 'circle':
              style.radius = resolveValue(paint['circle-radius'], zoom, properties);
              style.color = resolveValue(paint['circle-stroke-color'], zoom, properties);
              style.weight = resolveValue(paint['circle-stroke-width'], zoom, properties);
              style.opacity = resolveValue(paint['circle-stroke-opacity'], zoom, properties);
              style.fillColor = resolveValue(paint['circle-color'], zoom, properties);
              style.fillOpacity = resolveValue(paint['circle-opacity'], zoom, properties);
              style.fill = true;
              break;
            case 'symbol':
              const iconImage = resolveValue(layout['icon-image'], zoom, properties);
              if (!iconImage || iconImage === '') {
                // This is a text-only layer (a label).
                if (drawLabels) {
                  return { stroke: false, fill: false };
                }
                
                // See https://github.com/Leaflet/Leaflet.VectorGrid/issues/67
                  let text = properties['name' + lang];
                  if (text === undefined) {
                    text = properties['name'];
                  }
                  const textFont = mapboxStyle["ol:webfonts"];
                  const fontFamily = Array.isArray(textFont) ? textFont.join(', ') : 'sans-serif';
                  const fs = resolveValue(layout['text-size'], zoom, properties) || 0;

                  const fill = resolveValue(paint['text-color'], zoom, properties);
                  const stroke = resolveValue(paint['text-halo-color'], zoom, properties);
                  const strokeWidth = resolveValue(paint['text-halo-width'], zoom, properties);

                  if (fs <= 0) {
                    return { stroke: false, fill: false }; 
                  }

                  // --- Label Collision Detection ---
                  if (labelCache && geometry) {
                    const l = properties.name.length;
                    const w = fs * l * 0.7; // Approximate width
                    const h = fs + 10;      // Approximate height

                    // Get the screen coordinates of the point
                    const point = map.latLngToContainerPoint([geometry[1], geometry[0]]);

                    // Calculate the bounding box of the label
                    const halfWidth = w / 2;
                    const originalBox = {
                      minX: point.x - halfWidth,
                      maxX: point.x + halfWidth,
                      minY: point.y - h, // Anchor is at the bottom
                      maxY: point.y
                    };

                    // Create a slightly larger box for checking to enforce a margin.
                    const margin = 10; // 5-pixel margin on each side
                    const checkBox = {
                      minX: originalBox.minX - margin,
                      maxX: originalBox.maxX + margin,
                      minY: originalBox.minY - margin,
                      maxY: originalBox.maxY + margin
                    };

                    // Check for overlap with existing labels in the cache
                    const overlaps = labelCache.some(b => checkBox.maxX > b.minX && checkBox.minX < b.maxX && checkBox.maxY > b.minY && checkBox.minY < b.maxY);
                    if (overlaps) return { stroke: false, fill: false }; // Hide if it overlaps
                    labelCache.push(originalBox); // Add the original box to the cache
                  }

                  // Calculate icon dimensions
                  const w = fs * (text ? text.length : 0) * 0.8;
                  const h = fs + 10;
                  const anchorY = fs;

                  // Programmatically create the SVG elements instead of building a string.
                  const group = SVG.create('g');

                  const textElement = SVG.create('text');
                  const attributes = {
                    'paint-order': 'stroke fill', 'fill': fill, 'stroke': stroke,
                    'stroke-width': strokeWidth, 'x': w / 2, 'y': fs,
                    'font-size': `${fs}px`, 'font-family': fontFamily, 'text-anchor': 'middle'
                  };
                  for (const key in attributes) {
                    textElement.setAttribute(key, attributes[key]);
                  }
                  textElement.textContent = text;
                  group.appendChild(textElement);

                  const icon = new SvgIcon({
                      svgElement: group,
                      iconSize: [w, h],
                      iconAnchor: [w / 2, anchorY]
                  });
                  //return {graphics: group};
                  // Use zIndexOffset to ensure labels appear on top. Higher 'level' properties get a higher z-index.
                  //return { icon, zIndexOffset: 1000 + (properties.level || 0) };
              } else {
                // This is an icon symbol, not a text label. Skip if we are in the label-drawing pass.
                if (drawLabels) {
                  return { stroke: false, fill: false };
                }
                // If we are in the geometry pass, we would handle the icon here.
              }
            default:
              console.warn(`Unsupported layer type: ${layer.type}`);
              continue;
          }
          // Add the generated style to our array for this feature.
          styles.push(style);
        }
      }

      if (styles.length > 0) {
        return styles.reverse();
      }

      // For debugging, make unstyled features visible.
      //console.warn(`Unstyled feature in source-layer '${sourceLayer}':`, properties, 'at zoom:', zoom);
      return { stroke: false, fill: false };
      //return { color: 'magenta', weight: 2, fill: true, fillColor: 'magenta', fillOpacity: 0.4 };
    }
  }

  return leafletStyle;
}

// Use OffscreenCanvas for text measurement if available, otherwise fall back to a standard canvas.
// This is slightly more performant and avoids creating a DOM element.
const canvas = typeof OffscreenCanvas !== 'undefined' ? new OffscreenCanvas(0, 0) : document.createElement('canvas');
const ctx = canvas.getContext('2d', { alpha: false });

export function getFeatureLayer(mapboxStyle, map) {
  //return function (feature, layerName, pxPerExtent, options) {
    
  return function (feature, layerName, zoom, tile) {
    const properties = feature.properties;
    const labelCache = this['*']?.cache;

    //const self = featureLayerBase(feature, layerName, pxPerExtent, options);
    // Find the corresponding layer style in the Mapbox style
    const styleLayer = mapboxStyle.layers.find(l =>
      l['source-layer'] === layerName &&
      l.type === 'symbol' &&
      createFilter(l.filter)(properties, zoom)
    );

    if (!styleLayer) {
      return null; // Don't render if no style matches
    }

    // Check if the layer is visible at the current zoom level.
    if ((styleLayer.minzoom && zoom < styleLayer.minzoom) || (styleLayer.maxzoom && zoom >= styleLayer.maxzoom)) {
      return null;
    }
    const visibility = resolveValue(styleLayer.layout?.visibility, zoom, properties);
    if (visibility === 'none') {
      return null;
    }

    const paint = styleLayer.paint || {};
    const layout = styleLayer.layout || {};

    // Resolve text properties from the style
    const lang = map.options.lang;
    let text = properties['name_' + lang] || properties['name'];
    const fs = resolveValue(layout['text-size'], zoom, properties) || 0;

    if (!text || fs <= 0) {
      return null;
    }

    const fontFamily = (mapboxStyle["ol:webfonts"] || mapboxStyle.metadata["ol:webfonts"]) || 'sans-serif';
    ctx.font = `${fs}px ${fontFamily}`;
    const w = ctx.measureText(text).width;

    // --- Label Collision Detection ---
    if (labelCache && feature.type === 1) { // Only check for Point features
      const tileKey = tile.x + ':' + tile.y + ':' + tile.z;
      if (!labelCache[tileKey]) {
        labelCache[tileKey] = [];
      }

      const h = fs * 1.5;
      const anchorY = h / 2;

      // Get the screen coordinates of the point relative to the tile.
      // VectorTileFeature geometry is normalized to a 0-4095 range.
      const point = feature.loadGeometry()[0][0];
      const scale = 256 / 4096;
      const tileX = point.x * scale;
      const tileY = point.y * scale;

      // Calculate the bounding box of the label within the tile.
      const margin = 10; // 5px margin on each side
      const box = {
        minX: tileX - (w / 2) - margin,
        maxX: tileX + (w / 2) + margin,
        minY: tileY - anchorY - margin,
        maxY: tileY + (h - anchorY) + margin
      };

      // Check for overlap with existing labels in the cache for this tile.
      const overlaps = labelCache[tileKey].some(b => box.maxX > b.minX && box.minX < b.maxX && box.maxY > b.minY && box.minY < b.maxY);
      if (overlaps) return null; // Hide if it overlaps

      labelCache[tileKey].push(box); // Add the box to the cache for this tile.
    }

    const h = fs * 1.5;
    const anchorY = h / 2;
    
    const fill = resolveValue(paint['text-color'], zoom, properties);
    const stroke = resolveValue(paint['text-halo-color'], zoom, properties);
    const strokeWidth = resolveValue(paint['text-halo-width'], zoom, properties);
    const textElement = SVG.create('text');
    const attributes = {
      'paint-order': 'stroke fill',
      'stroke-width': strokeWidth,
      'font-size': `${fs}px`,
      'font-family': fontFamily,
      'text-anchor': 'middle',
      'x': w / 2,
      'y': fs
    };

    attributes.fill = (typeof fill === 'object' && fill.color) ? fill.color : fill;
    attributes['fill-opacity'] = (typeof fill === 'object' && fill.opacity) ? fill.opacity : 1;

    attributes.stroke = (typeof stroke === 'object' && stroke.color) ? stroke.color : stroke;
    attributes['stroke-opacity'] = (typeof stroke === 'object' && stroke.opacity) ? stroke.opacity : 1;

    for (const key in attributes) {
      textElement.setAttribute(key, attributes[key]);
    }
    textElement.textContent = text;
    const group = SVG.create("g");
    group.appendChild(textElement);

    const svg = SVG.create('svg');
    svg.setAttribute('width', w);
    svg.setAttribute('height', h);
    svg.setAttribute('viewBox', `0 0 ${w} ${h}`);

    
    const styleElement = SVG.create('style');
    styleElement.textContent = `@font-face { font-family: "${fontFamily}"; src: local('${fontFamily}'), url("/fonts/space-grotesk-latin-ext-wght-normal.woff2") format("woff2-variations"); }`;
    svg.appendChild(styleElement);
  

    svg.appendChild(group);
    const svgString = new XMLSerializer().serializeToString(svg);
    const iconUrl = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svgString)));
    //console.log(svgString);

    const icon = L.icon({
      iconUrl: iconUrl,
      iconSize: [w, h],
      iconAnchor: [w / 2, anchorY]
    });
    
    // Return a divIcon so our custom applyImageStyle function can use it.
    //return { icon: L.divIcon({ html: svgString, iconSize: [w, h], iconAnchor: [w / 2, anchorY] })};
   //return { icon: icon };
    return svgIcon(group, w, h, w / 2, anchorY);
  };
}
function svgIcon(svg, width, height, anchorX, anchorY) {
  return {
    icon : {
      options: {
        svg: svg,
        iconSize: [width, height],
        iconAnchor: [anchorX, anchorY]
      }
    }
  };
}