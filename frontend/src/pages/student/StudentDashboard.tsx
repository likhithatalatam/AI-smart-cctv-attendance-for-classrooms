import { useEffect, useState } from "react";
import axios from "axios";
import "../../styles/studentDashboard.css";

const API = import.meta.env.VITE_API_BASE || "http://127.0.0.1:5000";

/* Attendance Stats */

interface Stats {
    total_classes: number;
    present: number;
    absent: number;
    percentage: number;
}
/* Student Profile */

interface Profile {
    name: string;
    roll_no: string;
    department: string;
    year: string;
    section: string;
    batch: string;
}
export default function StudentDashboard() {
    const [stats, setStats] = useState<Stats | null>(null);
    const [profile, setProfile] = useState<Profile | null>(null);

    const attendanceStatus = () => {
        if (!stats) return { label: "N/A", className: "" };

        if (stats.percentage >= 75)
            return { label: "Good", className: "status-good" };

        if (stats.percentage >= 65)
            return { label: "Warning", className: "status-warning" };

        return { label: "Shortage", className: "status-shortage" };
    };

    useEffect(() => {
        const token = localStorage.getItem("token");

        /* Fetch Attendance */

        axios
            .get(`${API}/api/student/my-attendance`, {
                headers: {
                    Authorization: `Bearer ${token}`,
                },
            })
            .then((res) => {
                setStats(res.data);
            })
            .catch((err) => {
                console.error("Attendance error:", err);
            });

        /* Fetch Student Profile */

        axios
            .get(`${API}/api/student/profile`, {
                headers: {
                    Authorization: `Bearer ${token}`,
                },
            })
            .then((res) => {
                setProfile(res.data);
            })
            .catch((err) => {
                console.error("Profile error:", err);
            });
    }, []);

    const handleLogout = () => {
        localStorage.removeItem("token");
        window.location.href = "/login";
    }

    return (
        <div className="student-container">
            <div className="student-header">
                <h1 className="student-title">Student Dashboard</h1>
                <button className="logout-btn" onClick={handleLogout}>Logout</button>
            </div>
            <div className="student-grid">

                {/* PROFILE PANEL */}

                <div className="student-profile">
                    <h2>Profile</h2>

                    <div className="profile-item">
                        <span>Name</span>
                        <strong>{profile?.name || "-"}</strong>
                    </div>

                    <div className="profile-item">
                        <span>Roll No</span>
                        <strong>{profile?.roll_no || "-"}</strong>
                    </div>

                    <div className="profile-item">
                        <span>Batch</span>
                        <strong>{profile?.batch || "-"}</strong>
                    </div>

                    <div className="profile-item">
                        <span>Department</span>
                        <strong>{profile?.department || "-"}</strong>
                    </div>

                    <div className="profile-item">
                        <span>Year</span>
                        <strong>{profile?.year || "-"}</strong>
                    </div>

                    <div className="profile-item">
                        <span>Section</span>
                        <strong>{profile?.section || "-"}</strong>
                    </div>

                    <div className="profile-item">
                        <span>Attendance Status</span>
                        <strong className={attendanceStatus().className}>
                            {attendanceStatus().label}
                        </strong>
                    </div>

                </div>

                {/* ATTENDANCE PANEL */}

                <div className="attendance-panel">

                    <h2>Attendance Overview</h2>

                    <div className="attendance-stats">

                        <div>
                            <p>Total Classes</p>
                            <h3>{stats?.total_classes ?? 0}</h3>
                        </div>

                        <div>
                            <p>Present</p>
                            <h3>{stats?.present ?? 0}</h3>
                        </div>

                        <div>
                            <p>Absent</p>
                            <h3>{stats?.absent ?? 0}</h3>
                        </div>

                    </div>

                    <div className="attendance-progress">

                        <p>Attendance Percentage</p>

                        <div className="progress-bar">
                            <div
                                className="progress-fill"
                                style={{ width: `${stats?.percentage || 0}%` }}
                            ></div>
                        </div>

                        <span>{stats?.percentage ?? 0}%</span>

                    </div>

                </div>

            </div>
        </div>
    );
}