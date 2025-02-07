import React, { useState, useEffect } from "react";
import useCommonStore from "../store/map.js";
import useEventStore from "../store/event.js";
import { generateEventId, generateFilename } from "../helpers/common.js";
import { postRequest } from "../apis/client";
import useAuthStore from "../store/auth";

const CACHE_KEY = "earthquake_data";
const EARTHQUAKE_RADIUS = 500;

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

  const fiveYearsAgo = new Date();
  fiveYearsAgo.setFullYear(fiveYearsAgo.getFullYear() - 5);

  useEffect(() => {
    const fetchEarthquakeData = async () => {
      try {
        setLoading(true);

        const cachedData = localStorage.getItem(CACHE_KEY);
        if (cachedData) {
          const { timestamp, data } = JSON.parse(cachedData);
          const isCacheValid = Date.now() - timestamp < 24 * 60 * 60 * 1000;
          if (isCacheValid) {
            setEarthquakes(data);
            setLoading(false);
            return;
          }
        }

        const response = await fetch(
          `https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime=${fiveYearsAgo.toISOString()}&endtime=${new Date().toISOString()}&minlatitude=35&maxlatitude=43&minlongitude=25&maxlongitude=45`,
        );

        if (!response.ok) {
          console.log("Failed to fetch earthquake data");
        }

        const data = await response.json();
        const features = data.features.filter(
          (quake) => quake.properties.mag >= 6.5,
        );

        const userLocation = mapboxConfig.center;

        const nearbyEarthquakes = features.filter((quake) => {
          const distance = haversineDistance(
            userLocation[1],
            userLocation[0],
            quake.geometry.coordinates[1],
            quake.geometry.coordinates[0],
          );
          return distance <= EARTHQUAKE_RADIUS;
        });

        localStorage.setItem(
          CACHE_KEY,
          JSON.stringify({ timestamp: Date.now(), data: nearbyEarthquakes }),
        );

        setEarthquakes(nearbyEarthquakes);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchEarthquakeData();
  }, [mapboxConfig.center]);

  const handleCheckboxChange = (quake, checked, index) => {
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
    const filename = generateFilename(action.id, "earthquake");
    const time = quake.properties.time;
    const date = new Date(time);
    const day = String(date.getDate()).padStart(2, "0");
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const year = date.getFullYear();
    const eventtype = "earthquake";

    const formattedDate = `${day}-${month}-${year}`;

    const params = {
      userid,
      eventid,
      filename,
      eventtype,
      date: formattedDate,
      status: "processing",
      analysis: action.name,
      location: quake.properties.place,
      latitude: quake.geometry.coordinates[0],
      longitude: quake.geometry.coordinates[1],
    };
    console.log(params);
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
                          handleCheckboxChange(quake, e.target.checked, index)
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
