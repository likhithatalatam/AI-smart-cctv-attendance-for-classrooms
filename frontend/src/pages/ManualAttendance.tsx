import { useEffect, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";

import "../styles/attendance.css";

const API = import.meta.env.VITE_API_BASE || "http://127.0.0.1:5000";

interface Student {
  id: number;
  roll_no: string;
  name: string;
  department?: string;
  year?: string;
  section?: string;
}

export default function ManualAttendance() {
  const [students, setStudents] = useState<Student[]>([]);
  const [msg, setMsg] = useState("");
  const [date, setDate] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // 🔹 Filters
  const [department, setDepartment] = useState("");
  const [year, setYear] = useState("");
  const [section, setSection] = useState("");

  // 🔹 attendanceMap: studentId → { status, method }
  const [attendanceMap, setAttendanceMap] = useState<
    Record<number, { status: string; method: string }>
  >({});

  const navigate = useNavigate();
  const token = localStorage.getItem("token");

  // ---------------- AUTH + LOAD STUDENTS ----------------
  useEffect(() => {
    if (!token) {
      navigate("/");
      return;
    }
    loadStudents();
  }, []);

  const loadStudents = async () => {
    const res = await axios.get(`${API}/api/students`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    setStudents(res.data.students);
  };

  // ---------------- LOAD STATUS WHEN DATE CHANGES ----------------
  useEffect(() => {
    if (!date) {
      setAttendanceMap({});
      return;
    }

    let intervalId: any;

    const loadStatus = async () => {
      try {
        const res = await axios.get(
          `${API}/api/attendance/by-date?date=${date}`,
          {
            headers: { Authorization: `Bearer ${token}` },
          }
        );
        setAttendanceMap(res.data);
      } catch {
        // ignore errors silently
      }
    };

    // load immediately
    loadStatus();

    // 🔁 AUTO REFRESH EVERY 3 SECONDS
    intervalId = setInterval(loadStatus, 3000);

    // 🧹 cleanup when date changes or page unmounts
    return () => clearInterval(intervalId);
  }, [date]);


  // ---------------- FILTER LOGIC ----------------
  const filteredStudents = students.filter((s) => {
    const deptMatch =
      !department || s.department?.trim() === department;
    const yearMatch =
      !year || s.year?.toString().trim() === year;
    const sectionMatch =
      !section || s.section?.trim() === section;

    return deptMatch && yearMatch && sectionMatch;
  });

  // ---------------- MARK ATTENDANCE ----------------
  const markAttendance = async (
    studentId: number,
    rollNo: string,
    status: "present" | "absent"
  ) => {
    if (!date) {
      setMsg("Please select a date first");
      return;
    }

    setSubmitting(true);
    setMsg("");

    try {
      await axios.post(
        `${API}/api/attendance/manual`,
        {
          roll_no: rollNo,
          status,
          timestamp: date,
          source: "manual-ui",
        },
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      // 🔹 Update UI immediately
      setAttendanceMap((prev) => ({
        ...prev,
        [studentId]: { status, method: "manual" },
      }));

      setMsg(`Marked ${status.toUpperCase()} for ${rollNo}`);
    } catch (err: any) {
      setMsg(err.response?.data?.error || "Failed to mark attendance");
    } finally {
      setSubmitting(false);
    }
  };

  // ---------------- UI ----------------
  return (
    <div className="attendance-page">
      <h1 className="attendance-title">Manual Attendance</h1>
      <p className="attendance-subtitle">
        Select date and mark student attendance
      </p>

      <div className="attendance-card">
        {/* Date + Filters */}
        <div className="date-row">
          <label>
            Select Date
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />
          </label>

          <select value={department} onChange={(e) => setDepartment(e.target.value)}>
            <option value="">All Departments</option>
            <option value="CSE">CSE</option>
            <option value="COS">COS</option>
            <option value="CSM">CSM</option>
            <option value="ECE">ECE</option>
            <option value="MECH">MECH</option>
          </select>

          <select value={year} onChange={(e) => setYear(e.target.value)}>
            <option value="">All Years</option>
            <option value="1">1</option>
            <option value="2">2</option>
            <option value="3">3</option>
            <option value="4">4</option>
          </select>

          <select value={section} onChange={(e) => setSection(e.target.value)}>
            <option value="">All Sections</option>
            <option value="A">A</option>
            <option value="B">B</option>
            <option value="C">C</option>
            <option value="D">D</option>
          </select>
        </div>

        <p className="attendance-msg">{msg || "\u00A0"}</p>

        {/* Table */}
        <div className="table-wrapper">
          <table className="attendance-table">
            <thead>
              <tr>
                <th>Roll No</th>
                <th>Name</th>
                <th>Action</th>
                <th>Status</th>
                <th>Method</th>
              </tr>
            </thead>

            <tbody>
              {filteredStudents.map((s) => (
                <tr key={s.id}>
                  <td>{s.roll_no}</td>
                  <td>{s.name}</td>

                  <td>
                    <div className="action-buttons">
                      <button
                        className="present-btn"
                        disabled={submitting}
                        onClick={() => markAttendance(s.id, s.roll_no, "present")}
                      >
                        Present
                      </button>

                      <button
                        className="absent-btn"
                        disabled={submitting}
                        onClick={() => markAttendance(s.id, s.roll_no, "absent")}
                      >
                        Absent
                      </button>
                    </div>
                  </td>

                  <td>
                    {attendanceMap[s.id] ? (
                      <span className={`status ${attendanceMap[s.id].status}`}>
                        {attendanceMap[s.id].status.toUpperCase()}
                      </span>
                    ) : (
                      <span className="status pending">-</span>
                    )}
                  </td>

                  <td>
                    {attendanceMap[s.id]?.method ? (
                      <span className={`method ${attendanceMap[s.id].method}`}>
                        {attendanceMap[s.id].method.toUpperCase()}
                      </span>
                    ) : (
                      "-"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
