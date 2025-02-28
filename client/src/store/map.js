import { create } from "zustand";

const useCommonStore = create((set) => ({
  map: null,
  mapboxConfig: {
    center: [37.8, 34.5],
    zoom: 7,
    country: "turkey",
    bounds: { minlat: 35.0, maxlat: 43.0, minlon: 25.0, maxlon: 45.0 },
  },
  setMap: (map) => set({ map }),
  setMapboxCenter: (center) =>
    set((state) => ({
      mapboxConfig: { ...state.mapboxConfig, center },
    })),
  setMapboxZoom: (zoom) =>
    set((state) => ({
      mapboxConfig: { ...state.mapboxConfig, zoom },
    })),
  setMapboxCountry: (country) =>
    set((state) => ({
      mapboxConfig: { ...state.mapboxConfig, country },
    })),
  setCountryBounds: (bounds) =>
    set((state) => ({
      mapboxConfig: { ...state.mapboxConfig, bounds },
    })),
}));

export default useCommonStore;
