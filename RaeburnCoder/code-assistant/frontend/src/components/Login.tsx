import { useState } from "react";
import { login } from "../api";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await login(username, password);
      sessionStorage.setItem("token", res.token);
      window.location.reload();
    } catch (err) {
      setError("Invalid credentials");
    }
  };

  return (
    <div style={{ maxWidth: "400px", margin: "2rem auto" }}>
      <h2>Sign In</h2>
      <form onSubmit={handleSubmit}>
        <div>
          <input
            value={username}
            onChange={e => setUsername(e.target.value)}
            placeholder="Username"
            style={{ marginBottom: "0.5rem", width: "100%" }}
          />
        </div>
        <div>
          <input
            value={password}
            onChange={e => setPassword(e.target.value)}
            type="password"
            placeholder="Password"
            style={{ marginBottom: "0.5rem", width: "100%" }}
          />
        </div>
        <button type="submit">Login</button>
      </form>
      {error && <div style={{ color: "red" }}>{error}</div>}
    </div>
  );
}
