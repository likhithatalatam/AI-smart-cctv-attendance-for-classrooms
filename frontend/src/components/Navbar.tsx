import { useNavigate, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import {
  MdDashboard,
  MdPersonAdd,
  MdEdit,
  MdBarChart,
  MdLogout,
  MdOutlineAdminPanelSettings,
  MdOutlineAcUnit,
} from "react-icons/md";
import "../styles/navbar.css";

export default function Navbar() {
  const navigate = useNavigate();
  const location = useLocation();

  const [role, setRole] = useState<string | null>(null);

  useEffect(() => {
    setRole(localStorage.getItem("role"));
  }, []);

  const isActive = (path: string) =>
    location.pathname === path ? "active" : "";

  const logout = () => {
    localStorage.clear();
    navigate("/");
  };

  return (
    <div className="navbar">
      {/* TOP */}
      <div className="navbar-top">
        <span className="navbar-title">CCTV Attendance</span>

        {/* ROLE INDICATOR */}
        {role === "admin" && (
          <div className="navbar-role">
            {/* <MdOutlineAdminPanelSettings className="nav-icon" /> */}
            <span>Admin</span>
          </div>
        )}

        {role === "faculty" && (
          <div className="navbar-role">
            {/* <MdOutlineAcUnit className="nav-icon" /> */}
            <span>Faculty</span>
          </div>
        )}
      </div>

      {/* DASHBOARD – BOTH */}
      <div
        className={`navbar-item ${isActive("/dashboard")}`}
        onClick={() => navigate("/dashboard")}
      >
        <MdDashboard className="nav-icon" />
        <span>Dashboard</span>
      </div>

      {/* ADMIN ONLY */}
      {role === "admin" && (
        <div
          className={`navbar-item ${isActive("/admin/master-data")}`}
          onClick={() => navigate("/admin/master-data")}
        >
          <MdOutlineAdminPanelSettings className="nav-icon" />
          <span>Master Data</span>
        </div>
      )}

      {/* BOTH ADMIN & FACULTY */}
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

      {/* LOGOUT – BOTH */}
      <div className="navbar-item logout" onClick={logout}>
        <MdLogout className="nav-icon" />
        <span>Logout</span>
      </div>
    </div>
  );
}
