import React, { useState, useEffect } from "react";
import AnalysisTable from "./AnalysisTable";
import { getRequest } from "../apis/client";
import useLayerStore from "../store/layer";
import useAnalysisStore from "../store/analysis";

const AnalysisList = () => {
  const { userRequestedAnalysisList, setUserRequestedAnalysisList } =
    useAnalysisStore();
  const [selectedTab, setSelectedTab] = useState("earthquake");
  const { layers, setLayers } = useLayerStore();

  const fetchRequestedAnalysisFiles = async () => {
    try {
      const response = await getRequest(
        `${import.meta.env.VITE_APP_ENDPOINT}/geospatial/tasks`,
      );
      setUserRequestedAnalysisList(response);
    } catch (err) {
      console.log("Failed to fetch earthquake data.");
    }
  };

  const handleAddLayerButtonClick = (event, eventid, filename) => {
    event.preventDefault();

    const fileExists = layers.find((layer) => layer.filename === filename);

    if (fileExists) {
      console.log(`Layer with filename "${filename}" is already in cache.`);
      return;
    }

    const newLayer = { eventid, filename };
    setLayers([...layers, newLayer]);
  };

  const handleRegenerateButtonClick = (event) => {
    event.preventDefault();
  };

  useEffect(() => {
    fetchRequestedAnalysisFiles();
  }, []);

  return (
    <div className="analysis">
      <div className="tabs">
        <ul className="nav nav-tabs" id="myTab" role="tablist">
          {["earthquake", "flood", "fire"].map((tab) => (
            <li className="nav-item" role="presentation" key={tab}>
              <a
                className={`nav-link ${selectedTab === tab ? "active" : ""}`}
                id={`${tab}-tab`}
                data-bs-toggle="tab"
                href={`#${tab}`}
                role="tab"
                onClick={() => setSelectedTab(tab)}
              >
                <i
                  className={`bi bi-${tab === "earthquake" ? "broadcast" : tab}`}
                ></i>{" "}
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </a>
            </li>
          ))}
        </ul>

        <div className="tab-content mt-3" id="myTabContent">
          {["earthquake", "flood", "fire"].map((tab) => (
            <div
              key={tab}
              className={`tab-pane fade ${selectedTab === tab ? "show active" : ""}`}
              id={tab}
              role="tabpanel"
              aria-labelledby={`${tab}-tab`}
            >
              {userRequestedAnalysisList ? (
                <AnalysisTable
                  files={userRequestedAnalysisList}
                  handleRegenerateButtonClick={handleRegenerateButtonClick}
                  handleAddLayerButtonClick={handleAddLayerButtonClick}
                />
              ) : (
                "No requests found"
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default AnalysisList;
