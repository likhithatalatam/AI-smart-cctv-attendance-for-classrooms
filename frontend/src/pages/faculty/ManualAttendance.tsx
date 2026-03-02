import { useEffect, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import "../../styles/attendance.css";
import "react-toastify/dist/ReactToastify.css";

const API = import.meta.env.VITE_API_BASE || "http://127.0.0.1:5000";

interface Student {
  id: number;
  roll_no: string;
  name: string;
}

interface MasterItem {
  id: number;
  name?: string;
  label?: string;
  batch_id?: number;
  branch_id?: number;
  year?: number;
}

interface Subject {
  id: number;
  name: string;
}

const PERIODS = [1, 2, 3, 4, 5, 6, 7];

export default function ManualAttendance() {
  const navigate = useNavigate();
  const token = localStorage.getItem("token");

  /* ---------- MASTER DATA ---------- */
  const [branches, setBranches] = useState<MasterItem[]>([]);
  const [sections, setSections] = useState<MasterItem[]>([]);
  const [batches, setBatches] = useState<MasterItem[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);

  /* ---------- FILTERS ---------- */
  const [branch, setBranch] = useState("");
  const [year, setYear] = useState("");
  const [section, setSection] = useState("");
  const [batch, setBatch] = useState("");
  const [date, setDate] = useState("");


  /* ---------- DATA ---------- */
  const [students, setStudents] = useState<Student[]>([]);
  const [periodSubjects, setPeriodSubjects] = useState<Record<number, number>>(
    {}
  );

  const [attendanceMap, setAttendanceMap] = useState<
    Record<number, Record<number, { status: string; method: string }>>
  >({});

  const [msg, setMsg] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const filteredBranches = branches.filter(
    b => String(b.batch_id) === batch
  );
  /* ---------- AUTH ---------- */
  useEffect(() => {
    if (!token) navigate("/");
  }, []);

  const authHeader = {
    headers: { Authorization: `Bearer ${token}` },
  };

  /* ---------- LOAD MASTER DATA ---------- */
  useEffect(() => {
    axios.get(`${API}/api/batches`, authHeader)
      .then(r => setBatches(r.data));
  }, []);

  useEffect(() => {
    if (!batch) {
      setBranches([]);
      return;
    }

    axios.get(`${API}/api/branches`, {
      ...authHeader,
      params: { batch_id: batch }
    })
      .then(r => setBranches(r.data))
      .catch(console.error);

  }, [batch]);

  /* ---------- LOAD SECTIONS (BRANCH + YEAR) ---------- */
  useEffect(() => {
    if (!batch || !branch || !year) {
      setSections([]);
      setSection("");
      return;
    }

    const selectedBranch = branches.find(
      b => b.name === branch && String(b.batch_id) === batch
    );
    if (!selectedBranch) return;

    axios.get(`${API}/api/sections`, {
      ...authHeader,
      params: {
        batch_id: batch,
        branch_id: selectedBranch.id,
        year,
      },
    }).then(r => setSections(r.data));
  }, [batch, branch, year, branches]);

  useEffect(() => {
    if (!batch || !branch || !year || !section || !date) return;

    const selectedBranch = branches.find(
      b => b.name === branch && String(b.batch_id) === batch
    );

    if (!selectedBranch) return;

    axios.get(`${API}/api/period-subjects`, {
      headers: { Authorization: `Bearer ${token}` },
      params: {
        batch,
        branch_id: selectedBranch.id,
        year,
        section,
        date
      }
    })
      .then(res => {
        setPeriodSubjects(res.data);
      });

  }, [batch, branch, year, section, date, branches]);

  useEffect(() => {
    if (!date || !batch || !branch || !year || !section) return;

    const fetchAttendance = () => {
      axios
        .get(`${API}/api/attendance/by-date`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
          params: {
            date,
            batch,
            dept: branch,
            year,
            section,
          },
        })
        .then(res => {
          const raw = res.data;
          const mapped: Record<number, Record<number, any>> = {};

          Object.entries(raw).forEach(([studentId, periods]: any) => {
            mapped[Number(studentId)] = {};
            Object.entries(periods).forEach(([period, info]: any) => {
              mapped[Number(studentId)][Number(period)] = info;
            });
          });

          setAttendanceMap(mapped);
        })
        .catch(() => { });
    };

    // CALL IMMEDIATELY
    fetchAttendance();

    // THEN START AUTO REFRESH
    const interval = setInterval(fetchAttendance, 4000);

    return () => clearInterval(interval);
  }, [date, batch, branch, year, section]);

  useEffect(() => {
    if (!batch || !branch || !year) {
      setSubjects([]);
      return;
    }

    const selectedBranch = branches.find(
      b => b.name === branch && String(b.batch_id) === batch
    );
    if (!selectedBranch) return;

    axios
      .get(`${API}/api/subjects`, {
        ...authHeader,
        params: {
          batch_id: batch,
          branch_id: selectedBranch.id,
          year,
        },
      })
      .then(r => setSubjects(r.data))
      .catch(console.error);
  }, [batch, branch, year, branches]);


  /* ---------- LOAD STUDENTS ---------- */
  useEffect(() => {
    if (!token || !branch || !year || !section || !batch) return;

    axios
      .get(`${API}/api/students`, {
        headers: { Authorization: `Bearer ${token}` },
        params: {
          dept: branch,
          year,
          section,
          batch,
        },
      })
      .then(r => setStudents(r.data.students))
      .catch(err => console.error("STUDENTS ERROR:", err));
  }, [token, branch, year, section, batch]);


  const savePeriodSubjects = async () => {
    if (!batch || !branch || !year) {
      setMsg("Select batch, branch and year");
      return;
    }

    const selectedBranch = branches.find(
      b => b.name === branch && String(b.batch_id) === batch
    );

    if (!selectedBranch) return;

    await axios.post(
      `${API}/api/admin/period-subjects`,
      {
        batch,
        branch_id: selectedBranch.id,
        year,
        section,
        date,
        periodSubjects

      },
      authHeader
    );

    setMsg("Period subjects saved successfully");
  };
  /* ---------- MARK MANUAL ATTENDANCE ---------- */
  const markAttendance = async (
    student: Student,
    period: number,
    status: "present" | "absent"
  ) => {
    if (!date) {
      setMsg("Please select date");
      return;
    }

    const subject_id = periodSubjects[period];
    if (!subject_id) {
      setMsg(`Select subject for Period ${period}`);
      return;
    }

    setSubmitting(true);
    setMsg("");

    try {
      await axios.post(
        `${API}/api/attendance/manual`,
        {
          roll_no: student.roll_no,
          date,
          period,
          subject_id,
          status,
        },
        authHeader
      );

      setAttendanceMap(prev => ({
        ...prev,
        [student.id]: {
          ...(prev[student.id] || {}),
          [period]: { status, method: "manual" },
        },
      }));

      setMsg(`${student.roll_no} → P${period} ${status.toUpperCase()}`);
    } catch (err: any) {
      setMsg(err.response?.data?.error || "Failed");
    } finally {
      setSubmitting(false);
    }
  };

  /* ---------- UI (UNCHANGED) ---------- */
  if (!token) return null;
  return (
    <div className="attendance-page">
      <h1 className="attendance-title">Manual Attendance (Period-wise)</h1>

      <div className="attendance-card">
        <div className="date-row">
          <input type="date" value={date} onChange={e => setDate(e.target.value)} />

          <select
            value={batch}
            onChange={e => {
              setBatch(e.target.value);
              setYear("");
              setBranch("");
              setSection("");
            }}
          >
            <option value="">Batch</option>
            {batches.map(b => (
              <option key={b.id} value={String(b.id)}>
                {b.label}
              </option>
            ))}
          </select>

          <select
            value={year}
            onChange={e => {
              setYear(e.target.value);
              setBranch("");
              setSection("");
            }}
            disabled={!batch}
          >
            <option value="">Year</option>
            <option value="1">1</option>
            <option value="2">2</option>
            <option value="3">3</option>
            <option value="4">4</option>
          </select>

          <select
            value={branch}
            onChange={e => {
              setBranch(e.target.value);
              setSection("");
            }}
            disabled={!batch || !year}
          >
            <option value="">Branch</option>
            {filteredBranches.map(b => (
              <option key={b.id} value={b.name}>
                {b.name}
              </option>
            ))}
          </select>

          <select
            value={section}
            onChange={e => setSection(e.target.value)}
            disabled={!batch || !year || !branch}
          >
            <option value="">Section</option>
            {sections.map(s => (
              <option key={s.id} value={s.name}>{s.name}</option>
            ))}
          </select>
        </div>
        <button
          className="save-period-btn"
          onClick={savePeriodSubjects}
        >
          Save Period Subjects
        </button>
        <p className="attendance-msg">{msg || "\u00A0"}</p>

        <div className="table-wrapper">
          <table className="attendance-table">
            <thead>
              <tr>
                <th>Roll No</th>
                <th>Name</th>
                {PERIODS.map(p => (
                  <th key={p}>
                    P{p}
                    <select
                      value={periodSubjects[p] || ""}
                      onChange={e =>
                        setPeriodSubjects(prev => ({
                          ...prev,
                          [p]: Number(e.target.value),
                        }))
                      }
                    >
                      <option value="">Subject</option>
                      {subjects.map(s => (
                        <option key={s.id} value={s.id}>{s.name}</option>
                      ))}
                    </select>
                  </th>
                ))}
              </tr>
            </thead>

            <tbody>
              {students.map(s => (
                <tr key={s.id}>
                  <td>{s.roll_no}</td>
                  <td>{s.name}</td>

                  {PERIODS.map(p => (
                    <td key={p}>
                      <button
                        disabled={submitting}
                        className={`present-btn ${attendanceMap[s.id]?.[p]?.status === "present" ? "active" : ""}`}
                        onClick={() => markAttendance(s, p, "present")}
                      >
                        P
                      </button>

                      <button
                        disabled={submitting}
                        className={`absent-btn ${attendanceMap[s.id]?.[p]?.status === "absent" ? "active" : ""}`}
                        onClick={() => markAttendance(s, p, "absent")}
                      >
                        A
                      </button>

                      {attendanceMap[s.id]?.[p] && (
                        <div className="method-label">
                          {attendanceMap[s.id][p].method.toUpperCase()} /{" "}
                          {attendanceMap[s.id][p].status === "present" ? "P" : "A"}
                        </div>
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>

        </div>
      </div>
    </div>
  );
}
