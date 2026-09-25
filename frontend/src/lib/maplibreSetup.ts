import * as maplibregl from "maplibre-gl";

// Module-scope side effect: runs once, the first time ANY component
// imports this file, before that component can construct a Map. Must be
// imported (for side effects) by every component that uses maplibre-gl -
// setWorkerUrl is a library-global setting, not per-Map, but Turbopack can
// split components into separate chunks that each get their own first
// chance to construct a Map before a *different* component's copy of this
// call would have run. See MapView.tsx's comment for why this is needed at
// all (MapLibre v6's worker is a separate .mjs module Turbopack can't
// resolve at its default relative path).
maplibregl.setWorkerUrl("/maplibre-worker/maplibre-gl-worker.mjs");

export { maplibregl };
