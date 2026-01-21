---
title: "iFrames"
metaPage: true
displayinlist: false
archive: false
news: false
sectionContent: false
layout: iframes-list
sitemap:
  disable: true
build:
  list: never
  publishResources: false
cascade:
  - target:
      kind: '{page,section}'
      lang: de
      path: '**'
    layout: iframe
    params:
      archive: false
      news: false
      metaPage: true
      displayinlist: false
      sitemap:
        disable: true
      build:
        publishResources: true
---
