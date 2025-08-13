import React, { useEffect } from "react";

import useCommonStore from "../store/map";
import useLayerStore from "../store/layer";
import { isValidBlob } from "../helpers/common.js";

const Overlay = () => {
  const { map } = useCommonStore();
  const { layers, selectedLayers } = useLayerStore();

  const displayOnMap = async () => {
    if (map) {
      for (const [index, layer] of layers.entries()) {
        const isValid = await isValidBlob(layer.image);
        const layerId = `raster-layer-${index}`;
        const sourceId = `raster-source-${index}`;
        if (selectedLayers.includes(layer.filename) && isValid) {
          const features = layer.metadata?.features?.[0];
          const coordinates = features?.geometry?.coordinates;
          const [lowerLeft, upperLeft, upperRight, lowerRight] =
            coordinates?.[0]?.slice(0, 4) || [];
          console.log(
            [lowerLeft, upperLeft, upperRight, lowerRight],
            layer.image
          );

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
          } else {
            map.removeLayer(layerId);
            map.removeSource(sourceId);
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
