---
title: Karte
layout: print
weight: 3
params:
  print: true
  pages: 2
---


Auf der Karte werden nur die Herkunftsorte von Bügeln angezeigt, deren Ort sich an Hand eines Aufdrucks identifizieren ließen.

{{< print-map src="list/map.geojson" style="shortbread" cluster=true marker="{src: 'images/geomarker.svg', scale: 0.1, anchorXUnits: 'fraction', anchorYUnits: 'fraction', anchor: [0.9, 1]}" >}}