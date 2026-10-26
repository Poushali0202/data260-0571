import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "../api.js";

export default function Login({ onLogin }) {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    try {
      const user = await login(username, password);
      onLogin(user);
      navigate("/");
    } catch {
      setError("Invalid username or password");
    }
  }

  return (
    <div className="card">
      <h2>Log in</h2>
      {error && <p className="error">{error}</p>}
      <form onSubmit={handleSubmit}>
        <label>
          Username
          <input value={username} onChange={(e) => setUsername(e.target.value)} required />
        </label>
        <label>
          Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>
        <button type="submit">Log in</button>
      </form>
    </div>
  );
}
