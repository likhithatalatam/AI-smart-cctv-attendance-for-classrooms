import { BrowserRouter, Routes, Route } from "react-router-dom";
import Welcome from "./pages/Welcome";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Dashboard from "./pages/Dashboard";
import StudentRegistration from "./pages/StudentRegistration";
import ManualAttendance from "./pages/ManualAttendance";
import AttendanceTracker from "./pages/AttendanceTracker";
import Navbar from "./components/Navbar";
import ProtectedRoute from "./components/ProtectedRoute";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* ===== PUBLIC ROUTES ===== */}
        <Route path="/" element={<Welcome />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />


        {/* ===== PROTECTED ROUTES ===== */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <>
                <Navbar />
                <Dashboard />
              </>
            </ProtectedRoute>
          }
        />

        <Route
          path="/register"
          element={
            <ProtectedRoute>
              <>
                <Navbar />
                <StudentRegistration />
              </>
            </ProtectedRoute>
          }
        />

        <Route
          path="/manual"
          element={
            <ProtectedRoute>
              <>
                <Navbar />
                <ManualAttendance />
              </>
            </ProtectedRoute>
          }
        />

        <Route
          path="/attendance"
          element={
            <ProtectedRoute>
              <>
                <Navbar />
                <AttendanceTracker />
              </>
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
