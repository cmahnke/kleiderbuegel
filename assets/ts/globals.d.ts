/*
 * Type declarations for the global APIs the site's script entry points
 * attach to `window`.
 */

import type { Map as LeafletMap } from 'leaflet';

declare global {
  interface Window {
    PDFObject: import('pdfobject/pdfobject.js').default;
    initSlider(elem: Element | null, size?: number): void;
    initHome(elem: Element | null): void;
    slider(elem: Element | null, size?: number): void;
    initMap(
      element: string,
      geojson?: string,
      source?: string,
      cluster?: boolean,
      marker?: OlIconStyle | false,
      style?: string,
      bbox?: number[]
    ): Promise<LeafletMap>;
  }
}

export {};
