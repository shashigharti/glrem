import React, { useState, useEffect, useRef } from "react";
import Map, { NavigationControl, ScaleControl, Marker } from "react-map-gl";

import config from "../config.js";
import useCommonStore from "../store/map";
import useEventStore from "../store/event";
import Overlay from "./Overlay.jsx";

const MapboxPage = () => {
  const { mapboxConfig, setMap } = useCommonStore();
  const { earthquakes, selectedEarthquakes } = useEventStore();

  const [viewport, setViewport] = useState({
    latitude: mapboxConfig.center[1],
    longitude: mapboxConfig.center[0],
    zoom: mapboxConfig.zoom,
  });

  const mapRef = useRef(null);

  useEffect(() => {
    setViewport({
      latitude: mapboxConfig.center[1],
      longitude: mapboxConfig.center[0],
      zoom: mapboxConfig.zoom,
    });
  }, [mapboxConfig]);

  const handleMapLoad = () => {
    if (mapRef.current) {
      setMap(mapRef.current.getMap());
    }
  };

  return (
    <Map
      {...viewport}
      mapboxAccessToken={config.mapBoxToken}
      onMove={(evt) => setViewport(evt.viewState)}
      mapStyle="mapbox://styles/mapbox/streets-v11"
      className="mapboxgl-canvas"
      dragPan
      scrollZoom
      doubleClickZoom
      ref={mapRef}
      onLoad={handleMapLoad}
    >
      <NavigationControl position="top-left" />
      <ScaleControl />
      {/* <Marker
        latitude={mapboxConfig.center[1]}
        longitude={mapboxConfig.center[0]}
      >
        <div
          style={{
            backgroundColor: "red",
            width: "20px",
            height: "20px",
            borderRadius: "50%",
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            color: "white",
            fontSize: "12px",
            fontWeight: "bold",
            textAlign: "center",
          }}
        >
          📍
        </div>
      </Marker> */}

      {earthquakes
        .filter((quake, index) => selectedEarthquakes.includes(index))
        .map((quake, index) => {
          const [longitude, latitude] = quake.geometry.coordinates;
          return (
            <Marker key={index} latitude={latitude} longitude={longitude}>
              <div
                style={{
                  backgroundColor: "blue",
                  width: "20px",
                  height: "20px",
                  borderRadius: "50%",
                  display: "flex",
                  justifyContent: "center",
                  alignItems: "center",
                  color: "white",
                  fontSize: "12px",
                  fontWeight: "bold",
                  textAlign: "center",
                }}
              >
                💥
              </div>
            </Marker>
          );
        })}
      <Overlay />
    </Map>
  );
};

export default MapboxPage;
