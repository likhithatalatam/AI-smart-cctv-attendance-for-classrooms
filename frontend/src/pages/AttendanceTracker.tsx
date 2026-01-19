import { useEffect, useState } from "react";
import axios from "axios";
import "../styles/attendance-tracker.css";

const API = import.meta.env.VITE_API_BASE || "http://127.0.0.1:5000";

interface Student {
  id: number;
  roll_no: string;
  name: string;
  department: string;
  year: string;
  section?: string; // 👈 section may be missing
}

interface AttendanceSettings {
  start_date: string;
  end_date: string;
  holidays: string[];
}

export default function AttendanceTracker() {
  const token = localStorage.getItem("token");

  const [students, setStudents] = useState<Student[]>([]);
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null);

  const [department, setDepartment] = useState("");
  const [year, setYear] = useState("");
  const [section, setSection] = useState("");

  const [settings, setSettings] = useState<AttendanceSettings | null>(null);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  const [totalDays, setTotalDays] = useState(0);
  const [presentDays, setPresentDays] = useState(0);
  const [percentage, setPercentage] = useState(0);

  // 🔹 RESET SELECTED STUDENT WHEN FILTERS CHANGE
  useEffect(() => {
    setSelectedStudent(null);
    setTotalDays(0);
    setPresentDays(0);
    setPercentage(0);
  }, [department, year, section]);

  useEffect(() => {
    loadStudents();
    loadSettings();
  }, []);

  // ---------------- LOAD DATA ----------------
  const loadStudents = async () => {
    const res = await axios.get(`${API}/api/students`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    setStudents(res.data.students);
  };

  const loadSettings = async () => {
    const res = await axios.get(`${API}/api/attendance/settings`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    setSettings(res.data);
    setStartDate(res.data.start_date || "");
    setEndDate(res.data.end_date || "");
  };

  // ---------------- SAVE SETTINGS ----------------
  const saveAttendancePeriod = async () => {
    if (!startDate || !endDate) {
      alert("Please select start and end date");
      return;
    }

    await axios.post(
      `${API}/api/attendance/settings`,
      {
        start_date: startDate,
        end_date: endDate,
        holidays: settings?.holidays || [],
        exclude_sundays: true,
      },
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );

    await loadSettings();
    alert("Attendance period updated");
  };

  // ---------------- CALCULATE DAYS ----------------
  const calculateWorkingDays = () => {
    if (!settings) return 0;

    let count = 0;
    let current = new Date(settings.start_date);
    const end = new Date(settings.end_date);

    while (current <= end) {
      const day = current.getDay();
      const dateStr = current.toISOString().split("T")[0];

      if (day !== 0 && !settings.holidays.includes(dateStr)) {
        count++;
      }
      current.setDate(current.getDate() + 1);
    }
    return count;
  };

  // ---------------- LOAD STUDENT SUMMARY ----------------
  const loadStudentStats = async (student: Student) => {
    setSelectedStudent(student);

    const res = await axios.get(
      `${API}/api/attendance/summary/${student.id}`,
      { headers: { Authorization: `Bearer ${token}` } }
    );

    const total = calculateWorkingDays();
    const present = res.data.present_days;

    setTotalDays(total);
    setPresentDays(present);
    setPercentage(total ? Math.round((present / total) * 100) : 0);
  };

  // ---------------- FILTER (FIXED) ----------------
  const filteredStudents = students.filter((s) => {
    const deptMatch =
      !department || s.department?.trim() === department;

    const yearMatch =
      !year || s.year?.toString().trim() === year;

    const sectionMatch =
      !section || s.section?.trim() === section;

    return deptMatch && yearMatch && sectionMatch;
  });



  // ---------------- 
  //  ----------------
  const exportReport = async (type: "pdf" | "excel") => {
    const response = await axios.get(`${API}/api/export/attendance`, {
      params: {
        dept: department || undefined,
        year: year || undefined,
        section: section || undefined,
        type,
      },
      headers: { Authorization: `Bearer ${token}` },
      responseType: "blob",
    });

    const blob = new Blob([response.data]);
    const url = window.URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download =
      type === "pdf"
        ? "attendance_report.pdf"
        : "attendance_report.xlsx";
    a.click();

    window.URL.revokeObjectURL(url);
  };

  // ---------------- UI ----------------
  return (
    <div className="tracker-page">
      <h1>Attendance Tracker</h1>

      {/* Attendance Period */}
      <div className="period-box">
        <label>
          Start Date
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
        </label>

        <label>
          End Date
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
          />
        </label>

        <button onClick={saveAttendancePeriod}>Save Period</button>
      </div>

      {/* Filters */}
      <div className="filters">
        <div>
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

        <div>
          <button onClick={() => exportReport("pdf")}>Export PDF</button>
          <button onClick={() => exportReport("excel")}>Export Excel</button>
        </div>
      </div>

      <div className="tracker-layout">
        <div className="student-list">
          {filteredStudents.map((s) => {
            const isSelected = selectedStudent?.id === s.id;

            return (
              <div
                key={s.id}
                onClick={() => loadStudentStats(s)}
                className={`student-item ${isSelected ? "active" : ""}`}
              >
                <div className="student-main">
                  <strong>{s.roll_no}</strong>
                  <span>{s.name}</span>
                </div>

                {isSelected && (
                  <div className="inline-summary">
                    <span><b>Total:</b> {totalDays}</span>
                    <span><b>Present:</b> {presentDays}</span>
                    <span><b>{percentage}%</b></span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

    </div>
  );
}
