import React from "react";
import ReactDOM from "react-dom/client";
import "@/assets/styles/main.scss";
import "bootstrap/dist/js/bootstrap.bundle.min.js";
import Index from "./components/Index";
import { BrowserRouter } from "react-router-dom";

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <BrowserRouter>
    <Index />
  </BrowserRouter>,
);
