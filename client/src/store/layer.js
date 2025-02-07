import { create } from "zustand";

const useLayerStore = create((set) => ({
  layers: [],
  useTile: false,
  selectedLayers: [],

  setSelectedLayers: (selectedLayers) =>
    set(() => ({
      selectedLayers,
    })),

  setLayers: (layers) => {
    set(() => ({ layers }));
    localStorage.setItem("layers", JSON.stringify(layers));
  },

  loadLayers: () => {
    try {
      const savedLayers = JSON.parse(localStorage.getItem("layers")) || [];
      set(() => ({ layers: savedLayers }));
    } catch (error) {
      console.error("Error loading layers from localStorage:", error);
      set(() => ({ layers: [] }));
    }
  },
}));

export default useLayerStore;
