import React, { useEffect } from "react";
import useLayerStore from "../store/layer";
import { fetchLayer } from "../apis/layer";

const LayerComponent = () => {
  const {
    useTile,
    layers,
    setLayers,
    selectedLayers,
    setSelectedLayers,
    loadLayers,
  } = useLayerStore();

  useEffect(() => {
    loadLayers();
  }, []);

  const handleLayerClick = async (eventid, filename, checked) => {
    if (checked) {
      setSelectedLayers([...selectedLayers, filename]);
    } else {
      setSelectedLayers(selectedLayers.filter((layer) => layer !== filename));
    }

    if (useTile) return;
    const layer = layers.find((layer) => layer.filename === filename);
    console.log(layer);
    if (
      !layer?.image ||
      typeof layer.image === "string" ||
      !(layer.image instanceof Blob)
    ) {
      const { image, metadata } = await fetchLayer(eventid);

      if (image instanceof Blob) {
        const imageUrl = URL.createObjectURL(image);
        layer.image = imageUrl;
      }

      const updatedLayers = layers.map((layer) =>
        layer.filename === filename ? { ...layer, image, metadata } : layer,
      );
      setLayers(updatedLayers);
    }
  };

  console.log(layers);
  if (!layers || layers.length === 0) {
    return null;
  }

  return (
    <div className="files-container">
      <h6>Layers</h6>
      <ul style={{ listStyleType: "none", padding: 0 }}>
        {layers.map((layer, index) => (
          <li key={index} style={{ marginBottom: "8px" }}>
            <input
              type="checkbox"
              id={layer.filename}
              checked={selectedLayers.includes(layer.filename)}
              onChange={(e) =>
                handleLayerClick(
                  layer.eventid,
                  layer.filename,
                  e.target.checked,
                )
              }
            />
            <label htmlFor={layer.filename} style={{ marginLeft: "10px" }}>
              {layer.filename}
            </label>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default LayerComponent;
