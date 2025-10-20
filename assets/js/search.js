import { Instance, Input, ResultList, FilterPills } from "@pagefind/modular-ui";
import i18next from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";

//export function setupSearch(elem, lang) {
//  new PagefindUI({ element: "#search", showSubResults: true });
//}

translations = {
  "en": {
    "search-filter": {
      "section": "Section",
      "tag": "Tag",
      "type": "Entity type"
    },
    "search-sections": {
      "collections": "Collections",
      "home": "Homepage",
      "iiif": "IIIF",
      "links": "Links",
      "post": "Blog"
    }
  },
  "de": {
    "search-filter": {
      "section": "Bereich",
      "tag": "Schlagwort",
      "type": "Entitätstyp"
    },
    "search-sections": {
      "collections": "Sammlungen",
      "home": "Startseite",
      "iiif": "IIIF",
      "links": "Links",
      "post": "Blog"
    }
  }
}

class CMFilterPills extends FilterPills {
  pillInner(val, count) {
    let label = val
    if (i18next.exists(`search-sections:${val}`)) {
      label = i18next.t(`search-sections:${val}`)
    }
    if (this.total) {
        return `<span aria-label="${label}" data-filter-count="${count}">${label} (${count})</span>`;
    } else {
        return `<span aria-label="${label}">${label}</span>`;
    }
}
}

i18next.use(LanguageDetector).init({
  debug: false,
  fallbackLng: "de",
  resources: translations,
  supportedLngs: ['de', 'en'],
});

window.addEventListener('DOMContentLoaded', (event) => {
  const bundlePath = "/index/"
  const urlParams = new URLSearchParams(window.location.search);
  const query = urlParams.get('q');
  const searchInputSelector = "#search-box";
  const filterContainer = document.querySelector("#search-filter");
  let filterInitialized = false

  document.querySelector(searchInputSelector).addEventListener("input", (event) => {
    const newQuery = event.target.value
    urlParams.set("q", newQuery);
    history.replaceState(null, null, "?"+urlParams.toString());
  })

  document.querySelector('.search-button').addEventListener("click", (event) => {
    const enterEvent = new KeyboardEvent('keydown', {
      key: 'Enter',
      code: 'Enter',
      which: 13,
      keyCode: 13,
    });
    document.querySelector(searchInputSelector).dispatchEvent(enterEvent);
  })

  const instance = new Instance({
      bundlePath: bundlePath
  });
  instance.add(new Input({
      inputElement: searchInputSelector
  }));
  instance.on("filters", (filters) => {
    if (!filterInitialized) {
      for (const [filter, values] of Object.entries(filters.available)) {
        /*
        const filterContainer = document.createElement("ul");
        for (const [value, count] of Object.entries(values)) {
          //console.log(`${value}: ${count}`);
          const tag = document.createElement("li");
          tag.innerText = `${value} (${count})`
          filterContainer.appendChild(tag);
        }
        */
        let filterLabel = filter
        if (i18next.exists(`search-filter:${filter}`)) {
          filterLabel = i18next.t(`search-filter:${filter}`)
        }
        const filterElementId = `search-filter-${filter}`
        const filterElement = document.createElement("fieldset");
        const filterElementLabel = document.createElement("legend");
        filterElementLabel.innerText = filterLabel

        filterElement.id = filterElementId
        filterElement.classList.add(filter)
        filterElement.classList.add("search-filter-single")
        filterContainer.appendChild(filterElement)
        instance.add(new CMFilterPills({
          containerElement: `#${filterElementId}`,
          filter: filter,
          selectMultiple: true,
          alwaysShow: false
        }));
        filterElement.appendChild(filterElementLabel)
      }
      filterInitialized = true
    }
  });


  /*

  //instance

  */

  instance.add(new ResultList({
      containerElement: "#search-results"
  }));


  document.querySelector(searchInputSelector).focus();
  if (query !== null && query !== "") {
    document.querySelector(searchInputSelector).value = query;
    instance.triggerSearch(query)
  } else {
      instance.triggerLoad();
  }

})
