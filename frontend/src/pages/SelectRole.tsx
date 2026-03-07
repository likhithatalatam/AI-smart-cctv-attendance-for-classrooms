import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { GraduationCap, UserCog, User } from "lucide-react";
import "../styles/role.css";

export default function SelectRole() {
    const navigate = useNavigate();
    const [role, setRole] = useState("faculty");

    const continueLogin = () => {
        navigate(`/login?role=${role}`);
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
                <h1>Select Login Type</h1>
                <p>Please choose your role</p>

                <div className="role-options">

                    <div
                        className={`role-option ${role === "student" ? "active" : ""}`}
                        onClick={() => setRole("student")}
                    >
                        <GraduationCap size={40} />
                        <span>Student</span>
                    </div>

                    <div
                        className={`role-option ${role === "faculty" ? "active" : ""}`}
                        onClick={() => setRole("faculty")}
                    >
                        <User size={40} />
                        <span>Faculty</span>
                    </div>

                    <div
                        className={`role-option ${role === "admin" ? "active" : ""}`}
                        onClick={() => setRole("admin")}
                    >
                        <UserCog size={40} />
                        <span>Admin</span>
                    </div>

                </div>

                <button className="primary" onClick={continueLogin}>
                    Continue
                </button>

            </div>
        </div>
    );
}