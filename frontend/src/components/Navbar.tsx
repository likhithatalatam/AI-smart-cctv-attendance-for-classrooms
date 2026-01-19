import { useNavigate, useLocation } from "react-router-dom";
import {
  MdDashboard,
  MdPersonAdd,
  MdEdit,
  MdBarChart,
  MdLogout,
} from "react-icons/md";
import "../styles/navbar.css";

export default function Navbar() {
  const navigate = useNavigate();
  const location = useLocation();

  const isActive = (path: string) =>
    location.pathname === path ? "active" : "";

  const logout = () => {
    localStorage.removeItem("token");
    navigate("/");
  };

  return (
    <div className="navbar">
      {/* Title */}
      <div className="navbar-top">
        <span className="navbar-title">CCTV Attendance</span>
      </div>

      {/* Menu */}
      <div
        className={`navbar-item ${isActive("/dashboard")}`}
        onClick={() => navigate("/dashboard")}
      >
        <MdDashboard className="nav-icon" />
        <span>Dashboard</span>
      </div>

      <div
        className={`navbar-item ${isActive("/register")}`}
        onClick={() => navigate("/register")}
      >
        <MdPersonAdd className="nav-icon" />
        <span>Register Student</span>
      </div>

      <div
        className={`navbar-item ${isActive("/manual")}`}
        onClick={() => navigate("/manual")}
      >
        <MdEdit className="nav-icon" />
        <span>Manual Attendance</span>
      </div>

      <div
        className={`navbar-item ${isActive("/attendance")}`}
        onClick={() => navigate("/attendance")}
      >
        <MdBarChart className="nav-icon" />
        <span>Attendance Tracker</span>
      </div>

      {/* Logout */}
      <div className="navbar-item logout" onClick={logout}>
        <MdLogout className="nav-icon" />
        <span>Logout</span>
      </div>
    </div>
  );
}
