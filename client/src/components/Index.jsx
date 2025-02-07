import React from "react";
import App from "./App";
import LoginPage from "./LoginPage";
import useAuthStore from "../store/auth";

function Index() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  return (
    <React.StrictMode>
      {!isAuthenticated ? <LoginPage /> : <App />}
    </React.StrictMode>
  );
}

export default Index;
