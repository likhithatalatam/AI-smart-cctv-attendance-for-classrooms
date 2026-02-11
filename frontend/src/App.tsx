import { BrowserRouter, Routes, Route } from "react-router-dom";
import Welcome from "./pages/Welcome";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import StudentRegistration from "./pages/faculty/StudentRegistration";
import ManualAttendance from "./pages/faculty/ManualAttendance";
import AttendanceTracker from "./pages/faculty/AttendanceTracker";
import Navbar from "./components/Navbar";
import ProtectedRoute from "./components/ProtectedRoute";
import MasterData from "./pages/admin/AdminMasterData";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* ===== PUBLIC ROUTES ===== */}
        <Route path="/" element={<Welcome />} />
        <Route path="/login" element={<Login />} />


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
        <Route
          path="/admin/master-data"
          element={
            <ProtectedRoute>
              <>
                <Navbar />
                <MasterData />
              </>
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
