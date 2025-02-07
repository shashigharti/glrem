import React, { useEffect } from "react";

import useCommonStore from "../store/map";
import useLayerStore from "../store/layer";

const OverlayTile = () => {
  const { map } = useCommonStore();
  const { layers, selectedLayers } = useLayerStore();

  useEffect(() => {
    if (!map || !layers.length) return;

    layers.forEach((layer, index) => {
      if (!selectedLayers.includes(layer.filename)) return;

      const layerId = `overlay-layer-${index}`;
      const sourceId = `overlay-source-${index}`;

      if (!map.getSource(sourceId)) {
        map.addSource(sourceId, {
          type: "raster",
          tiles: [
            `http://ec2-3-92-3-116.compute-1.amazonaws.com/geospatial/tiles?eventid=${layer.eventid}&z={z}&x={x}&y={y}`,
          ],
          tileSize: 256,
          minzoom: 5,
          maxzoom: 8,
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
    });

    return () => {
      layers.forEach((_, index) => {
        const layerId = `overlay-layer-${index}`;
        const sourceId = `overlay-source-${index}`;

        if (map.getLayer(layerId)) map.removeLayer(layerId);
        if (map.getSource(sourceId)) map.removeSource(sourceId);
      });
    };
  }, [map, layers, selectedLayers]);

  return null;
};

export default OverlayTile;
