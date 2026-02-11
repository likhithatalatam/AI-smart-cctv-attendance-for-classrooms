import { useEffect, useState } from "react";
import axios from "axios";
import "../../styles/attendance-tracker.css";

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

  const [batch, setBatch] = useState("");
  const [batches, setBatches] = useState<any[]>([]);
  const [branches, setBranches] = useState<any[]>([]);
  const [sections, setSections] = useState<any[]>([]);

  // 🔹 RESET SELECTED STUDENT WHEN FILTERS CHANGE
  // 1️⃣ Reset stats when filters change
  useEffect(() => {
    setSelectedStudent(null);
    setTotalDays(0);
    setPresentDays(0);
    setPercentage(0);
  }, [batch, department, year, section]);

  // 2️⃣ Initial load
  useEffect(() => {
    loadSettings();
    loadMasters();
  }, []);

  // 3️⃣ Reload students on filter change
  useEffect(() => {
    loadStudents();
  }, [batch, department, year, section]);

  // 4️⃣ Auto refresh masters on window focus
  useEffect(() => {
    const onFocus = () => {
      loadMasters();
    };

    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, []);

  const loadMasters = async () => {
    const headers = { Authorization: `Bearer ${token}` };

    const [batchRes, branchRes] = await Promise.all([
      axios.get(`${API}/api/admin/batches`, { headers }),
      axios.get(`${API}/api/admin/branches`, { headers }),
    ]);

    setBatches(batchRes.data);
    setBranches(branchRes.data);
  };


  // ---------------- LOAD DATA ----------------
  const loadStudents = async () => {
    // 🚫 do nothing until required filters are selected
    if (!batch || !department || !year) {
      setStudents([]);
      return;
    }

    const res = await axios.get(`${API}/api/students`, {
      headers: { Authorization: `Bearer ${token}` },
      params: {
        dept: department,
        year: year,
        section: section || undefined,
        batch: batch,
      },
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

  const loadSections = async () => {
    if (!batch || !department || !year) {
      setSections([]);
      return;
    }

    const branch = branches.find(
      (b) => b.name === department && String(b.batch_id) === batch
    );

    if (!branch) {
      setSections([]);
      return;
    }

    const res = await axios.get(`${API}/api/admin/sections`, {
      headers: { Authorization: `Bearer ${token}` },
      params: {
        batch_id: batch,
        branch_id: branch.id,
        year: year,
      },
    });

    setSections(res.data);
  };

  useEffect(() => {
    loadSections();
  }, [batch, department, year]);

  const canExport =
    !!batch &&
    !!department &&
    !!year &&
    !!settings?.start_date &&
    !!settings?.end_date;

  const exportDisabled =
    !batch ||
    !department ||
    !year ||
    !settings?.start_date ||
    !settings?.end_date;

  //  ----------------
  const exportReport = async (type: "pdf" | "excel") => {
    if (!canExport) return;

    const params: any = {
      type,
      batch,
      dept: department,
      year,
    };

    // ✅ send section ONLY if selected
    if (section) {
      params.section = section;
    }

    const response = await axios.get(`${API}/api/export/attendance`, {
      params,
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
  if (!token) return null;
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
          {/* BATCH */}
          <select
            value={batch}
            onChange={(e) => {
              setBatch(e.target.value);
              setDepartment("");
              setYear("");
              setSection("");
            }}
          >
            <option value="">All Batches</option>
            {batches.map((b) => (
              <option key={b.id} value={b.id.toString()}>
                {b.label}
              </option>
            ))}
          </select>

          {/* BRANCH */}
          <select
            value={department}
            onChange={(e) => {
              setDepartment(e.target.value);
              setYear("");
              setSection("");
            }}
            disabled={!batch}
          >
            <option value="">All Departments</option>
            {branches
              .filter((b) => String(b.batch_id) === batch)
              .map((b) => (
                <option key={b.id} value={b.name}>
                  {b.name}
                </option>
              ))}
          </select>

          {/* YEAR */}
          <select
            value={year}
            onChange={(e) => {
              setYear(e.target.value);
              setSection("");
            }}
            disabled={!batch || !department}
          >
            <option value="">All Years</option>
            <option value="1">1</option>
            <option value="2">2</option>
            <option value="3">3</option>
            <option value="4">4</option>
          </select>

          {/* SECTION */}
          <select
            value={section}
            onChange={(e) => setSection(e.target.value)}
            disabled={!batch || !department || !year}
          >
            <option value="">All Sections</option>
            {sections.map((s) => (
              <option key={s.id} value={s.name}>
                {s.name}
              </option>
            ))}
          </select>
        </div>

        <div className="export-btns">

          <button
            onClick={() => exportReport("pdf")}
            disabled={exportDisabled}
          >
            Export PDF
          </button>

          <button
            onClick={() => exportReport("excel")}
            disabled={exportDisabled}
          >
            Export Excel
          </button>
        </div>
      </div>


      {(!batch || !department || !year) && (
        <p className="hint-text">
          Please select Batch, Department and Year to view students
        </p>
      )}

      {batch && department && year && (
        <div className="tracker-layout">
          <div className="student-list">
            {students.length === 0 ? (
              <p className="no-data">No students found</p>
            ) : (
              students.map((s) => {
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
              })
            )}
          </div>
        </div>
      )}

    </div>
  );
}
