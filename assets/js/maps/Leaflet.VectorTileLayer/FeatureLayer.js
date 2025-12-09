/*
 * Copyright 2017, Joachim Kuebart <joachim.kuebart@gmail.com>
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *
 *   1. Redistributions of source code must retain the above copyright
 *      notice, this list of conditions and the following disclaimer.
 *
 *   2. Redistributions in binary form must reproduce the above copyright
 *      notice, this list of conditions and the following disclaimer in the
 *      documentation and/or other materials provided with the
 *      distribution.
 *
 *   3. Neither the name of the copyright holder nor the names of its
 *      contributors may be used to endorse or promote products derived
 *      from this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
 * LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 * INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 * CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 * POSSIBILITY OF SUCH DAMAGE.
 */

/*property
    _map, addClass, addInteractiveTarget, addTo, applyOptions, bbox, className,
    color, create, dashArray, dashOffset, feature, fill, fillColor, fillOpacity,
    fillRule, graphics, hidden, icon, iconAnchor, iconSize, iconUrl,
    interactive, layerName, lineCap, lineJoin, loadGeometry, map, opacity,
    options, pointsToPath, properties, prototype, radius, removeAttribute,
    removeClass, removeFrom, removeInteractiveTarget, scaleBy, scalePoint,
    setAttribute, setStyle, stroke, type, types, weight, x, y
*/

import {
    CircleMarker,
    DomUtil,
    Layer,
    Path,
    Polygon,
    SVG,
    bounds,
    extend,
    point
} from "leaflet";

import {VectorTileFeature} from "@mapbox/vector-tile";

function featureLayerBase(feature, layerName, pxPerExtent, options) {
    const self = new Layer(options);

    self.feature = feature;
    self.layerName = layerName;

    // Compatibility with Leaflet.VectorGrid
    self.properties = feature.properties;

    /*
     * FeatureLayers only serve as event targets and are never actually
     * "added" to the map, so we override the base class's addTo.
     */
    self.addTo = function addTo(map) {
        // Required by addInteractiveTarget.
        self._map = map;
        self.addInteractiveTarget(self.graphics);
    };

    self.removeFrom = function removeFrom() {
        self.removeInteractiveTarget(self.graphics);
        delete self._map;
    };

    self.scalePoint = function scalePoint(p) {
        return point(p).scaleBy(pxPerExtent);
    };

    self.bbox = function bbox() {
        const [x0, y0, x1, y1] = feature.bbox();
        return bounds(self.scalePoint([x0, y0]), self.scalePoint([x1, y1]));
    };

    // Configure this feature layer for its options at a basic level.
    self.applyOptions = function applyOptions(options) {
        if (options.className) {
            DomUtil.addClass(self.graphics, options.className);
        }
        // Apply style based on options alone with no overrides.
        self.setStyle({});
    };

    return self;
}
export {featureLayerBase};

function applyBasicStyle(element, style) {
    if (style.interactive) {
        /*
         * Leaflet's "interactive" class only applies to
         * renderers that are immediate descendants of a
         * pane.
         */
        element.setAttribute("pointer-events", "auto");
        DomUtil.addClass(element, "leaflet-interactive");
    } else {
        DomUtil.removeClass(element, "leaflet-interactive");
        element.removeAttribute("pointer-events");
    }

    if (style.hidden) {
        element.setAttribute("visibility", "hidden");
    } else {
        element.removeAttribute("visibility");
    }
}
export {applyBasicStyle};

function applyPathStyle(path, style) {
    if (style.stroke) {
        path.setAttribute("stroke", style.color);
        path.setAttribute("stroke-opacity", style.opacity);
        path.setAttribute("stroke-width", style.weight);
        path.setAttribute("stroke-linecap", style.lineCap);
        path.setAttribute("stroke-linejoin", style.lineJoin);

        if (style.dashArray) {
            path.setAttribute("stroke-dasharray", style.dashArray);
        } else {
            path.removeAttribute("stroke-dasharray");
        }

        if (style.dashOffset) {
            path.setAttribute("stroke-dashoffset", style.dashOffset);
        } else {
            path.removeAttribute("stroke-dashoffset");
        }
    } else {
        path.setAttribute("stroke", "none");
    }

    if (style.fill) {
        path.setAttribute("fill", style.fillColor || style.color);
        path.setAttribute("fill-opacity", style.fillOpacity);
        path.setAttribute("fill-rule", style.fillRule || "evenodd");
    } else {
        path.setAttribute("fill", "none");
    }

    return path;
}
export {applyPathStyle};

function applyImageStyle(image, style) {
    if (style.icon && style.icon.options.iconUrl) {
        const iconImage = SVG.create("image");
        iconImage.setAttribute("width", style.icon.options.iconSize[0]);
        iconImage.setAttribute("height", style.icon.options.iconSize[1]);
        iconImage.setAttribute("href", style.icon.options.iconUrl);
        image.appendChild(iconImage);
    } else if (style.icon && style.icon.options.svg) {
        image.appendChild(style.icon.options.svg);
    }
}
export {applyImageStyle};

function featureCircleLayer(feature, layerName, pxPerExtent, options) {
    options = extend({}, CircleMarker.prototype.options, options);
    const self = featureLayerBase(feature, layerName, pxPerExtent, options);

    const pt = self.scalePoint(feature.loadGeometry()[0][0]);
    self.graphics = SVG.create("circle");
    self.graphics.setAttribute("cx", pt.x);
    self.graphics.setAttribute("cy", pt.y);

    self.setStyle = function setStyle(style) {
        style = extend({}, options, style);
        applyBasicStyle(self.graphics, style);
        applyPathStyle(self.graphics, style);
        self.graphics.setAttribute("r", style.radius);
    };

    self.applyOptions(options);

    return self;
}
export {featureCircleLayer};

function featurePathLayer(feature, layerName, pxPerExtent, options) {
    const featureType = VectorTileFeature.types[feature.type];
    options = extend(
        {},
        (
            "Polygon" === featureType
            ? Polygon.prototype.options
            : Path.prototype.options
        ),
        options
    );

    const self = featureLayerBase(feature, layerName, pxPerExtent, options);

    const geometry = feature.loadGeometry();
    self.graphics = SVG.create("path");
    self.graphics.setAttribute("d", SVG.pointsToPath(
        geometry.map((ring) => ring.map(self.scalePoint)),
        "Polygon" === featureType
    ));

    self.setStyle = function setStyle(style) {
        style = extend({}, options, style);
        applyBasicStyle(self.graphics, style);
        applyPathStyle(self.graphics, style);
    };

    self.applyOptions(options);

    return self;
}
export {featurePathLayer};

function featureIconLayer(feature, layerName, pxPerExtent, options) {
    const self = featureLayerBase(feature, layerName, pxPerExtent, options);

    self.setStyle = function setStyle(style) {
        style = extend({}, options, style);
        applyBasicStyle(self.graphics, style);
        applyImageStyle(self.graphics, style);
    };

    self.graphics = SVG.create("g");

    // The x and y attributes should be 0, and the transform attribute should be used to translate the group to the correct position.
    const pos = self.scalePoint(feature.loadGeometry()[0][0]);
    const anchor = options.icon.options.iconAnchor || [0, 0];
    self.graphics.setAttribute("transform", `translate(${pos.x - anchor[0]}, ${pos.y - anchor[1]})`);

    self.applyOptions(options);


    return self;
}
export {featureIconLayer};

function defaultFeatureLayer(feature, layerName, pxPerExtent, options) {
    switch (VectorTileFeature.types[feature.type]) {
    case "Point":
        if (options.icon) {
            return featureIconLayer(feature, layerName, pxPerExtent, options);
        }
        return featureCircleLayer(feature, layerName, pxPerExtent, options);

    case "Polygon":
    case "LineString":
        return featurePathLayer(feature, layerName, pxPerExtent, options);

    default:
        throw new Error("Unknown feature type");
    }
}
export {defaultFeatureLayer};
