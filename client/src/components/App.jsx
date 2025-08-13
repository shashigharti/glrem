import React, { useState } from "react";
import Events from "./Events";
import { Link } from "react-router-dom";
import MapboxPage from "./MapboxPage";
import AnalysisList from "./AnalysisList";
import Layer from "./Layer";
import useAuthStore from "../store/auth";
import CountrySelector from "./CountrySelector";

const App = () => {
  const [activeTab, setActiveTab] = useState("map");

  const logout = useAuthStore((state) => state.logout);
  const handleLogout = () => {
    logout();
  };

  return (
    <div className="container-fluid main">
      <nav className="navbar navbar-expand-lg navbar-light bg-light">
        <div className="container-fluid">
          <div className="navbar-brand">GLREM Space</div>
          <CountrySelector />
          <div className="ml-auto">
            <Link to="/login" onClick={handleLogout} className="btn btn-link">
              Logout
            </Link>
          </div>
        </div>
      </nav>

      <nav className="nav nav-tabs">
        <button
          className={`nav-link ${activeTab === "map" ? "active" : ""}`}
          onClick={() => setActiveTab("map")}
        >
          Map View
        </button>
        <button
          className={`nav-link ${activeTab === "analysis" ? "active" : ""}`}
          onClick={() => setActiveTab("analysis")}
        >
          Analysis
        </button>
      </nav>

      <div className="tab-content">
        {activeTab === "map" && (
          <div className="tab-pane active">
            <div className="row">
              <div className="col-sm-12 col-md-10 col-lg-10">
                <MapboxPage />
              </div>
              <div className="col-sm-12 col-md-2 col-lg-2 features">
                <div className="analysis-container">
                  <Events />
                  <Layer />
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === "analysis" && (
          <div className="tab-pane active">
            <div className="row">
              <div className="col-sm-12">
                <AnalysisList />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default App;
