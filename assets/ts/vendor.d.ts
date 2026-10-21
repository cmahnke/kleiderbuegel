/*
 * Ambient declarations for packages that don't ship TypeScript types, plus
 * shared style/cache types for the map code. This must stay a script file
 * (no imports/exports on the top level) — otherwise the declarations would
 * become module augmentations, which require the augmented module to be
 * typed already.
 */

type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };

type FeatureProperties = Record<string, JsonValue | undefined>;

interface ColorWithOpacity {
  color: string;
  opacity: number;
}

type StyleValue = JsonValue | ColorWithOpacity;

interface LabelBox {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

type LabelCache = Record<string, LabelBox[]>;

interface OlIconStyle {
  src?: string;
  scale?: number;
  anchor?: number[];
  anchorXUnits?: string;
  anchorYUnits?: string;
}

interface MapboxStyleLayer {
  id?: string;
  type: string;
  'source-layer'?: string;
  filter?: JsonValue[];
  minzoom?: number;
  maxzoom?: number;
  paint?: Record<string, JsonValue | undefined>;
  layout?: Record<string, JsonValue | undefined>;
}

interface MapboxStyleSource {
  tiles?: string[];
  attribution?: string;
  [key: string]: JsonValue | undefined;
}

interface MapboxStyle {
  layers: MapboxStyleLayer[];
  sources: Record<string, MapboxStyleSource>;
  metadata?: Record<string, JsonValue | undefined>;
  'ol:webfonts'?: string | string[];
}

/*
 * i18next-browser-languagedetector is only resolvable inside the pnpm store
 * (it isn't a root dependency), so declare the surface used by the map code.
 */
declare module 'i18next-browser-languagedetector' {
  interface LanguageDetectorOptions {
    order?: string[];
    lookupQuerystring?: string;
    htmlTag?: string | HTMLElement;
    [key: string]: unknown;
  }
  export class LanguageDetector {
    constructor(services?: unknown, options?: LanguageDetectorOptions);
    detect(...args: unknown[]): string | undefined;
  }
  export default LanguageDetector;
}

declare module 'js-cookie' {
  interface CookiesStatic {
    get(name?: string): string | undefined;
    set(name: string, value: string, options?: object): void;
    remove(name: string, options?: object): void;
  }
  const Cookies: CookiesStatic;
  export default Cookies;
}

declare module 'pdfobject/pdfobject.js' {
  interface PDFObjectAPI {
    embed(
      url: string,
      target?: string | HTMLElement,
      options?: Record<string, unknown>
    ): HTMLElement | Array<HTMLElement>;
  }
  const PDFObject: PDFObjectAPI;
  export default PDFObject;
}

declare module '*.css' {
  const css: string;
  export default css;
}

declare module '*.scss' {
  const scss: string;
  export default scss;
}
