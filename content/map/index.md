---
title: "Kartenansicht"
metaPage: true
displayinlist: false
hideMeta: true
---

Auf dieser Seite werden die Einträge mit (rekonstruierten) Geo-Informationen auf eine Karte angezeigt. Die Kartenanzeige nutzt den externen Dienst [OpenStreetmap](https://www.openstreetmap.org/), daher muss der Nutzung zugestimmt werden.

{{< html/iframe-consent >}}
    {{< maps/osm src="/list/map.geojson" >}}
{{< /html/iframe-consent >}}

{{< html/link file="/list/map.geojson" content="Download GeoJSON" >}}
