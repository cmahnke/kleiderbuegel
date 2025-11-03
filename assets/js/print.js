//import previewr from "pagedjs/polyfill";
import { Previewer } from "pagedjs";


addEventListener("DOMContentLoaded", (event) => {
  let paged = new Previewer();
  let url = window.location;
  let params = new URLSearchParams(url.search);
  if (params.has('print') || params.has('p')) {
    paged.preview().then((flow) => {
        console.log('Rendered', flow.total, 'pages.');
    });
  }

})
