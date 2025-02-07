import React, { useState } from "react";
import { postRequest } from "../apis/client";
import useAuthStore from "../store/auth";

function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const login = useAuthStore((state) => state.login);

  const handleSubmit = async (event) => {
    event.preventDefault();

    const loginData = { username, password };

    const response = await postRequest(
      `${import.meta.env.VITE_APP_ENDPOINT}/user/login`,
      loginData,
    );

    if (response && response.username) {
      login(response.username);
    } else {
      setError(response?.message || "Login failed. Try again!");
    }
  };

  return (
    <div className="login-container">
      <div className="login-box">
        <h2>Log In</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              type="text"
              className="form-control"
              id="username"
              placeholder="Enter your username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              className="form-control"
              id="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>
          <button type="submit" className="btn btn-primary">
            Login
          </button>
        </form>
        {error && <p className="error-message">{error}</p>}
      </div>
    </div>
  );
}

export default LoginPage;
