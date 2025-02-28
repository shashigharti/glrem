import React, { useState, useEffect } from "react";
import useCommonStore from "../store/map.js";
import useEventStore from "../store/event.js";
import { generateEventId } from "../helpers/common.js";
import { postRequest, getRequest } from "../apis/client";
import useAuthStore from "../store/auth";

const CACHE_KEY = "earthquake_data";
const EARTHQUAKE_RADIUS = 900;

const haversineDistance = (lat1, lon1, lat2, lon2) => {
  const R = 6371;
  const toRadians = (deg) => (deg * Math.PI) / 180;

  const dLat = toRadians(lat2 - lat1);
  const dLon = toRadians(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRadians(lat1)) *
      Math.cos(toRadians(lat2)) *
      Math.sin(dLon / 2) ** 2;
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
};

const Events = () => {
  const { userid } = useAuthStore();

  const { mapboxConfig } = useCommonStore();
  const {
    actions,
    earthquakes,
    setEarthquakes,
    selectedEarthquakes,
    setSelectedEarthquakes,
  } = useEventStore();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("earthquake");
  const [fireEvents] = useState(0);
  const [floodEvents] = useState(0);

  const handleTabChange = (tab) => setActiveTab(tab);

  const tenYearsAgo = new Date();
  tenYearsAgo.setFullYear(tenYearsAgo.getFullYear() - 10);

  useEffect(() => {
    const fetchEarthquakeData = async () => {
      try {
        setLoading(true);
        const cache_key = `${CACHE_KEY}_${mapboxConfig.country}`;
        const cachedData = localStorage.getItem(cache_key);
        // console.log(cache_key, cachedData);
        if (cachedData) {
          const { timestamp, data } = JSON.parse(cachedData);
          const isCacheValid = Date.now() - timestamp < 24 * 60 * 60 * 1000;
          if (isCacheValid) {
            setEarthquakes(data);
            setLoading(false);
            return;
          }
        }
        const { minlat, minlon, maxlat, maxlon } = mapboxConfig.bounds;
        const coordinates = `${minlat},${maxlat},${minlon},${maxlon}`;
        const starttime = tenYearsAgo.toISOString();
        const endtime = new Date().toISOString();
        const minmagnitude = 5;
        const url = `${import.meta.env.VITE_APP_ENDPOINT}/events/earthquakes`;

        const data = await getRequest(url, {
          coordinates,
          starttime,
          endtime,
          minmagnitude,
        });
        console.log(url);

        if (!data || data.error) {
          console.error(
            "Failed to fetch earthquake data:",
            data?.error || "Unknown error",
          );
          return;
        }
        let features = data.features;
        console.log(features);
        const userLocation = mapboxConfig.center;

        let nearbyEarthquakes = features.filter((quake) => {
          const distance = haversineDistance(
            userLocation[1],
            userLocation[0],
            quake.geometry.coordinates[1],
            quake.geometry.coordinates[0],
          );
          return distance <= EARTHQUAKE_RADIUS;
        });
        
        if (import.meta.env.VITE_EXAMPLE_EARTHQUAKES) {
          const earthquakeIds = import.meta.env.VITE_EXAMPLE_EARTHQUAKES
            ? import.meta.env.VITE_EXAMPLE_EARTHQUAKES.split(",")
            : [];

          console.log(earthquakeIds);

          nearbyEarthquakes = features.filter((quake) =>
            earthquakeIds.includes(quake.id),
          );
        }

        localStorage.setItem(
          cache_key,
          JSON.stringify({ timestamp: Date.now(), data: nearbyEarthquakes }),
        );

        setEarthquakes(nearbyEarthquakes);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    console.log(mapboxConfig.bounds);

    fetchEarthquakeData();
  }, [mapboxConfig.bounds]);

  const handleCheckboxChange = (checked, index) => {
    if (checked) {
      setSelectedEarthquakes([...selectedEarthquakes, index]);
    } else {
      setSelectedEarthquakes(
        selectedEarthquakes.filter(
          (prevSeletedIndex) => prevSeletedIndex !== index,
        ),
      );
    }
  };

  const handleIntfClick = (event, quake, action) => {
    event.preventDefault();
    const eventid = generateEventId(quake, "earthquake");
    // const eventDate = new Date(quake.properties.time);
    // const year = eventDate.getUTCFullYear();
    // const month = (eventDate.getUTCMonth() + 1).toString().padStart(2, "0");
    // const day = eventDate.getUTCDate().toString().padStart(2, "0");
    // const hours = eventDate.getUTCHours().toString().padStart(2, "0");
    // const minutes = eventDate.getUTCMinutes().toString().padStart(2, "0");
    // const seconds = eventDate.getUTCSeconds().toString().padStart(2, "0");
    // const formattedDate = `${year}-${month}-${day}T${hours}:${minutes}:${seconds}Z`;
    // const eventtype = "earthquake";
    // const filename = generateFilename(eventid, action.id, "earthquake");

    console.log("auth", auth);

    const params = {
      userid,
      eventid,
      // filename,
      // eventtype,
      // eventdate: formattedDate,
      // status: "processing",
      // analysis: action.name,
      // location: quake.properties.place,
      // latitude: quake.geometry.coordinates[0],
      // longitude: quake.geometry.coordinates[1],
      // country: mapboxConfig.country,
      // magnitude: quake.properties["mag"],
    };
    console.log(params, quake);
    requestAnalysis(params);
  };

  const requestAnalysis = async (params) => {
    try {
      const response = await postRequest(
        `${import.meta.env.VITE_APP_ENDPOINT}/geospatial/interferogram`,
        params,
      );
      console.log("Response:", response);
    } catch (error) {
      console.error("Error in POST request:", error);
    }
  };

  if (error) return <p>Error: {error}</p>;

  return (
    <div className="events">
      <h6 className="title">Recent Events</h6>
      <ul className="nav nav-tabs">
        <li className="nav-item position-relative">
          <button
            className={`nav-link ${activeTab === "earthquake" ? "active" : ""}`}
            onClick={() => handleTabChange("earthquake")}
          >
            <i className="bi bi-broadcast"></i>
            {earthquakes.length > 0 && (
              <span className="badge bg-danger position-absolute top-0 start-100 translate-middle">
                {earthquakes.length}
              </span>
            )}
          </button>
        </li>
        <li className="nav-item position-relative">
          <button
            className={`nav-link ${activeTab === "flood" ? "active" : ""}`}
            onClick={() => handleTabChange("flood")}
          >
            <i className="bi bi-water"></i>
            {floodEvents > 0 && (
              <span className="badge bg-danger position-absolute top-0 start-100 translate-middle">
                {floodEvents}
              </span>
            )}
          </button>
        </li>
        <li className="nav-item position-relative">
          <button
            className={`nav-link ${activeTab === "fire" ? "active" : ""}`}
            onClick={() => handleTabChange("fire")}
          >
            <i className="bi bi-fire"></i>
            {fireEvents > 0 && (
              <span className="badge bg-danger position-absolute top-0 start-100 translate-middle">
                {fireEvents}
              </span>
            )}
          </button>
        </li>
      </ul>

      <div className="tab-content">
        {activeTab === "earthquake" && (
          <div className="tab-content__earthquake">
            {loading ? (
              <p>Loading...</p>
            ) : (
              <ul className="list-group">
                {earthquakes.map((quake, index) => (
                  <li key={index} className="list-group-item">
                    <div className="quake-info">
                      <input
                        type="checkbox"
                        onChange={(e) =>
                          handleCheckboxChange(e.target.checked, index)
                        }
                      />
                      Id: {quake.id}, Magnitude:{quake.properties.mag}, Date:
                      {new Date(quake.properties.time).toLocaleDateString(
                        "en-US",
                        {
                          year: "numeric",
                          month: "short",
                          day: "2-digit",
                        },
                      )}
                      , Lat: {quake.geometry.coordinates[1].toFixed(2)}, Lng:{" "}
                      {quake.geometry.coordinates[0].toFixed(2)}
                    </div>

                    <div className="icons">
                      {actions["earthquake"].map((action, index) => {
                        const handleClick = (event) => {
                          handleIntfClick(event, quake, action);
                        };

                        return (
                          <a
                            key={index}
                            href="#"
                            role="button"
                            onClick={handleClick}
                          >
                            {action.name} <i className="bi bi-download"></i>
                          </a>
                        );
                      })}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {activeTab === "flood" && (
          <div className="tab-content__flood">
            <p>No flood events available.</p>
          </div>
        )}

        {activeTab === "fire" && (
          <div className="tab-content__fire">
            <p>No fire events available.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default Events;
