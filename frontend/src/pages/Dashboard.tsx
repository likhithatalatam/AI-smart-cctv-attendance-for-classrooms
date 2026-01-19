import { useEffect, useState } from "react";
import axios from "axios";
import "../styles/dashboard.css";

const API = import.meta.env.VITE_API_BASE || "http://127.0.0.1:5000";

export default function Dashboard() {
  const [stats, setStats] = useState<any>(null);

  useEffect(() => {
    const token = localStorage.getItem("token");

    axios
      .get(`${API}/api/dashboard-stats`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
      .then((res) => {
        setStats(res.data);
      })
      .catch((err) => {
        console.error("Dashboard stats error:", err);
      });
  }, []);


  return (
    <div className="dashboard-page">
      <h1 className="dashboard-title">Dashboard</h1>
      <p className="dashboard-subtitle">
        Welcome to CCTV Attendance System
      </p>

      {!stats ? (
        <p>Loading dashboard...</p>
      ) : (
        <div className="stats-grid">
          <div className="stat-card">
            <h3>Total Students</h3>
            <span>{stats.totalStudents}</span>
          </div>
          <div className="stat-card">
            <h3>Present Today</h3>
            <span>{stats.presentToday}</span>
          </div>
          <div className="stat-card">
            <h3>Absent Today</h3>
            <span>{stats.absentToday}</span>
          </div>
          <div className="stat-card">
            <h3>Attendance Rate</h3>
            <span>{stats.attendanceRate}%</span>
          </div>
        </div>
      )}

    </div>
  );
}
