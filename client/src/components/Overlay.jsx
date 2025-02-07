import React, { useEffect } from "react";

import useCommonStore from "../store/map";
import useLayerStore from "../store/layer";
import { isValidBlob } from "../helpers/common.js";

const Overlay = () => {
  const { map } = useCommonStore();
  const { layers, selectedLayers } = useLayerStore();

  const displayOnMap = async () => {
    if (map) {
      const lowerLeft = [35.47083333, 35.42388889]; // Lower Left
      const upperLeft = [35.47083333, 39.02972221999961]; // Upper Left
      const upperRight = [39.00555556000081, 39.02972221999961]; // Upper Right
      const lowerRight = [39.00555556000081, 35.42388889]; // Lower Right

      for (const [index, layer] of layers.entries()) {
        const isValid = await isValidBlob(layer.image);
        if (selectedLayers.includes(layer.filename) && isValid) {
          const layerId = `raster-layer-${index}`;
          const sourceId = `raster-source-${index}`;
          const features = layer.metadata?.features?.[0];
          let coordinates = features?.geometry?.coordinates;
          const [lowerLeft, upperLeft, upperRight, lowerRight] =
            coordinates?.[0]?.slice(0, 4) || [];

          if (coordinates && !map.getLayer(layerId)) {
            map.addSource(sourceId, {
              type: "image",
              url: layer.image,
              coordinates: [lowerLeft, lowerRight, upperRight, upperLeft],
            });

            map.addLayer({
              id: layerId,
              type: "raster",
              source: sourceId,
              paint: {
                "raster-opacity": 0.7,
              },
            });
          }
        }
      }
    }
  };

  useEffect(() => {
    if (!map || !layers.length) return;
    displayOnMap();
  }, [map, layers, selectedLayers]);

  return null;
};

export default Overlay;
