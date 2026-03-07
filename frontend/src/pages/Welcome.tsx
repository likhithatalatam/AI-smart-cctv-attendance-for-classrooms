import { useNavigate } from "react-router-dom";
import "../styles/welcome.css";

export default function Welcome() {
    const navigate = useNavigate();

    return (
        <div className="welcome-page">
            <div className="welcome-content">
                <h1>IDEAL INSTITUTE OF TECHNOLOGY</h1>
                <h2>CCTV Attendance Portal</h2>
                <p>Smart and secure attendance management system</p>

                <div className="welcome-actions">
                    <button onClick={() => navigate("/select-role")}>
                        Login
                    </button>
                </div>
            </div>
        </div>
    );
}
