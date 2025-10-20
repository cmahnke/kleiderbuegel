---
title: "Kartenansicht"
metaPage: true
displayinlist: false
hideMeta: true
---

Auf dieser Seite werden die Einträge mit (rekonstruierten) Geo-Informationen auf eine Karte angezeigt. Die Kartenanzeige nutzt den externen Dienst [OpenStreetmap](https://www.openstreetmap.org/), daher muss der Nutzung zugestimmt werden.

{{< html/iframe-consent >}}
    {{< maps/osm-vector-tiles src="/list/map.geojson" style="shortbread" cluster=true marker="{src: '/images/geomarker.svg', scale: 0.1, anchorXUnits: 'fraction', anchorYUnits: 'fraction', anchor: [0.9, 1]}" >}}
{{< /html/iframe-consent >}}

{{< html/link class="download-link" file="../list/map.geojson" content="Download GeoJSON" >}}
