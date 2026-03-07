import { useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import "../styles/login.css";

const API = import.meta.env.VITE_API_BASE || "http://127.0.0.1:5000";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [msg, setMsg] = useState("");
  const navigate = useNavigate();

  const login = async () => {
    setMsg("");
    try {
      const res = await axios.post(`${API}/api/login`, {
        username,
        password,
      });

      localStorage.setItem("token", res.data.token);
      localStorage.setItem("role", res.data.user.role);

      const role = res.data.user.role;

      if (role === "student") {
        navigate("/student-dashboard");
      } else {
        navigate("/dashboard");
      }

    } catch {
      setMsg("Invalid username or password");
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="backbtn">
          <button
            type="button"
            className="back-btn"
            onClick={() => navigate("/")}
          >
            ← Back
          </button>
        </div>
        <h1>Login</h1>
        <p>Access your CCTV attendance dashboard</p>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            login();
          }}
        >
          <input
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />

          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          <button className="primary" type="submit">
            Login
          </button>
        </form>

        {msg && <div className="login-error">{msg}</div>}

      </div>
    </div>
  );
}
