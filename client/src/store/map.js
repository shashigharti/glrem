import { create } from "zustand";

const useCommonStore = create((set) => ({
  map: null,
  mapboxConfig: {
    center: [37.8, 34.5],
    zoom: 5,
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
}));

export default useCommonStore;
