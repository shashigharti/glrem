import { create } from "zustand";

const useEventStore = create((set) => ({
  earthquakes: [],
  selectedEarthquakes: [],
  setEarthquakes: (earthquakes) =>
    set(() => ({
      earthquakes,
    })),
  setSelectedEarthquakes: (indexes) =>
    set(() => ({
      selectedEarthquakes: indexes,
    })),

  actions: {
    earthquake: [
      { id: "intf", name: "Interferogram", api: "/geospatial/interferogram" },
      {
        id: "cd",
        name: "Change Detection",
        api: "/geospatial/change-detection",
      },
    ],
  },
}));

export default useEventStore;
