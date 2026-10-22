---
title: "Map view"
params:
  hideMeta: true
  metaPage: true
  displayinlist: false
---

{{< maps/osm-vector-tiles src="/list/map.geojson" style="map-styles/shortbread.json" cluster=true marker="{src: '/images/geomarker.svg', scale: 0.1, anchorXUnits: 'fraction', anchorYUnits: 'fraction', anchor: [0.9, 1]}" >}}
