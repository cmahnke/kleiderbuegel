---
title: "Map view"
metaPage: true
displayinlist: false
---

This page displays the entries with (reconstructed) geo-information on a map. The map uses the external service [OpenStreetmap](https://www.openstreetmap.org/), so you have to consent to its use.

{{< html/iframe-consent >}}
    {{< maps/osm src="/post/map.geojson" >}}
{{< /html/iframe-consent >}}

{{< html/link file="/post/map.geojson" content="Download GeoJSON" >}}
