import { useEffect, useRef, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import "../../styles/register.css";

const API = import.meta.env.VITE_API_BASE || "http://127.0.0.1:5000";

/* ===== Dropdown Options ===== */
const DEPARTMENTS = ["CSE", "CSM", "COS", "ECE", "MECH"];
const YEARS = ["1", "2", "3", "4"];
const SECTIONS = ["A", "B", "C", "D"];

export default function StudentRegistration() {
  const navigate = useNavigate();

  /* ===== Form Fields ===== */
  const [rollNo, setRollNo] = useState("");
  const [name, setName] = useState("");
  const [department, setDepartment] = useState("");
  const [year, setYear] = useState("");
  const [section, setSection] = useState("");
  const [msg, setMsg] = useState("");
  const [image1Submitted, setImage1Submitted] = useState(false);
  const [image2Submitted, setImage2Submitted] = useState(false);
  const [isError, setIsError] = useState(false);
  const [batch, setBatch] = useState("");

  /* ===== Images ===== */
  const [image1, setImage1] = useState<File | null>(null);
  const [image2, setImage2] = useState<File | null>(null);
  const [preview1, setPreview1] = useState<string | null>(null);
  const [preview2, setPreview2] = useState<string | null>(null);

  /* ===== Image Source Tracking ===== */
  const [image1FromCamera, setImage1FromCamera] = useState(false);
  const [image2FromCamera, setImage2FromCamera] = useState(false);

  /* ===== Camera ===== */
  const [cameraFor, setCameraFor] = useState<1 | 2 | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const [branches, setBranches] = useState<any[]>([]);
  const [sections, setSections] = useState<any[]>([]);
  const [subjects, setSubjects] = useState<any[]>([]);
  const [batches, setBatches] = useState<any[]>([]);

  /* ===== Auth check ===== */
  useEffect(() => {
    if (!localStorage.getItem("token")) navigate("/");
  }, [navigate]);

  /* ===== Open Camera ===== */
  const openCamera = async (imgNo: 1 | 2) => {
    setCameraFor(imgNo);

    const stream = await navigator.mediaDevices.getUserMedia({ video: true });
    streamRef.current = stream;

    if (videoRef.current) {
      videoRef.current.srcObject = stream;
      videoRef.current.play();
    }
  };
  useEffect(() => {
    const token = localStorage.getItem("token");
    const headers = { Authorization: `Bearer ${token}` };

    const fetchMasterData = async () => {
      try {
        const [branchesRes, subjectsRes, sectionsRes, batchesRes] = await Promise.all([
          axios.get(`${API}/api/branches`, { headers }),
          axios.get(`${API}/api/subjects`, { headers }),
          axios.get(`${API}/api/sections`, { headers }),
          axios.get(`${API}/api/batches`, { headers }),
        ]);

        setBranches(branchesRes.data);
        setSubjects(subjectsRes.data);
        setSections(sectionsRes.data);
        setBatches(batchesRes.data);
      } catch (err) {
        console.error("Failed to load master data", err);
      }
    };

    fetchMasterData();
  }, []);
  useEffect(() => {
    if (!batch || !year || !department) {
      setSections([]);
      return;
    }

    const token = localStorage.getItem("token");
    const headers = { Authorization: `Bearer ${token}` };

    const selectedBranch = branches.find(
      (b) => b.name === department && String(b.batch_id) === batch
    );

    if (!selectedBranch) {
      setSections([]);
      return;
    }

    axios.get(`${API}/api/sections`, {
      headers,
      params: {
        batch_id: batch,
        branch_id: selectedBranch.id,
        year: year,
      },
    })
      .then(res => {
        setSections(res.data);
      })
      .catch(err => console.error("Sections error:", err));

  }, [batch, year, department, branches]);

  const filteredBranches = branches.filter(
    (b) => String(b.batch_id) === batch
  );

  /* ===== Capture Photo ===== */
  const capturePhoto = () => {
    if (!videoRef.current || !canvasRef.current || !cameraFor) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx?.drawImage(video, 0, 0);

    canvas.toBlob((blob) => {
      if (!blob) return;

      const file = new File([blob], `image${cameraFor}.jpg`, {
        type: "image/jpeg",
      });

      const previewURL = URL.createObjectURL(blob);

      if (cameraFor === 1) {
        setImage1(file);
        setPreview1(previewURL);
        setImage1FromCamera(true);
      } else {
        setImage2(file);
        setPreview2(previewURL);
        setImage2FromCamera(true);
      }
    });

    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setCameraFor(null);
  };

  /* ===== Retake Camera Image ===== */
  const retakeImage = (imgNo: 1 | 2) => {
    if (imgNo === 1) {
      setImage1(null);
      setPreview1(null);
      setImage1FromCamera(false);
      setImage1Submitted(false);
    } else {
      setImage2(null);
      setPreview2(null);
      setImage2FromCamera(false);
      setImage2Submitted(false);
    }
    openCamera(imgNo);
  };

  /* ===== Delete Uploaded Image ===== */
  const deleteImage = (imgNo: 1 | 2) => {
    if (imgNo === 1) {
      setImage1(null);
      setPreview1(null);
      setImage1FromCamera(false);
    } else {
      setImage2(null);
      setPreview2(null);
      setImage2FromCamera(false);
    }
  };

  /* ===== File Upload ===== */
  const handleFile = (
    e: React.ChangeEvent<HTMLInputElement>,
    imgNo: 1 | 2
  ) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const previewURL = URL.createObjectURL(file);

    if (imgNo === 1) {
      setImage1(file);
      setPreview1(previewURL);
      setImage1FromCamera(false);
    } else {
      setImage2(file);
      setPreview2(previewURL);
      setImage2FromCamera(false);
    }
  };

  const registerStudent = async () => {
    setMsg("");
    if (
      !rollNo ||
      !name ||
      !department ||
      !year ||
      !section ||
      !batch ||
      !image1 ||
      !image2
    ) {
      setMsg("Please fill all fields and upload both images");
      setIsError(true);
      return;
    }

    try {

      const formData = new FormData();
      formData.append("roll_no", rollNo);
      formData.append("name", name);
      formData.append("department", department);
      formData.append("year", year);
      formData.append("section", section);
      formData.append("batch", batch);
      formData.append("image1", image1!);
      formData.append("image2", image2!);

      await axios.post(`${API}/api/register_student`, formData, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      });
      setSubmitted(true);
      setMsg("Student registered successfully");
      setIsError(false);

      setRollNo("");
      setName("");
      setDepartment("");
      setYear("");
      setSection("");
      setBatch("");
      setImage1(null);
      setImage2(null);
      setPreview1(null);
      setPreview2(null);
      setImage1FromCamera(false);
      setImage2FromCamera(false);

      setTimeout(() => setMsg(""), 1500);

    } catch (err: any) {
      setMsg(err.response?.data?.error || "Registration failed");
    }
  };

  const isFormValid =
    rollNo && name && department && year && section && batch && image1 && image2;

  return (
    <div className="register-page">
      <h1 className="register-title">Student Registration</h1>
      <p className="register-subtitle">
        Enter student details and upload two images
      </p>

      <div className="register-card">
        <div className="form-grid">
          <input placeholder="Roll Number" value={rollNo} onChange={(e) => setRollNo(e.target.value)} />
          <input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} />

          <select
            value={batch}
            onChange={(e) => {
              setBatch(e.target.value);
              setYear("");
              setDepartment("");
              setSection("");
            }}
          >
            <option value="">Select Batch</option>
            {batches.map((b) => (
              <option key={b.id} value={String(b.id)}>
                {b.label}
              </option>
            ))}
          </select>
          <select
            value={year}
            onChange={(e) => {
              setYear(e.target.value);
              setDepartment("");
              setSection("");
            }}
            disabled={!batch}
          >
            <option value="">Select Year</option>
            {YEARS.map(y => <option key={y}>{y}</option>)}
          </select>
          <select
            value={department}
            onChange={(e) => {
              setDepartment(e.target.value);
              setSection("");
            }}
          >
            <option value="">Select Department</option>
            {filteredBranches.map((b) => (
              <option key={b.id}>{b.name}</option>
            ))}
          </select>

          <select
            value={section}
            onChange={(e) => setSection(e.target.value)}
            disabled={!batch || !year || !department}
          >
            <option value="">Select Section</option>
            {sections.map((s) => (
              <option key={s.id} value={s.name}>
                {s.name}
              </option>
            ))}
          </select>
        </div>

        <div className="upload-grid">
          {/* IMAGE 1 */}
          <div className="upload-box">
            <h4>Image 1</h4>

            {!preview1 && cameraFor !== 1 && (
              <>
                <button onClick={() => openCamera(1)}>Open Camera</button>
                <label className="file-upload">
                  Upload Image
                  <input hidden type="file" accept="image/*" onChange={(e) => handleFile(e, 1)} />
                </label>
              </>
            )}

            {cameraFor === 1 && (
              <div className="camera-box">
                <video ref={videoRef} autoPlay />
                <button onClick={capturePhoto}>Capture</button>
                <canvas ref={canvasRef} style={{ display: "none" }} />
              </div>
            )}

            {preview1 && (
              <>
                <img src={preview1} className="image-preview" />

                {!image1Submitted && (
                  <div style={{ display: "flex", gap: "10px" }}>
                    <button onClick={() => retakeImage(1)}>
                      Retake
                    </button>

                    <button onClick={() => setImage1Submitted(true)}>
                      Submit
                    </button>
                  </div>
                )}
              </>
            )}
          </div>

          {/* IMAGE 2 */}
          <div className="upload-box">
            <h4>Image 2</h4>

            {!preview2 && cameraFor !== 2 && (
              <>
                <button onClick={() => openCamera(2)}>Open Camera</button>
                <label className="file-upload">
                  Upload Image
                  <input hidden type="file" accept="image/*" onChange={(e) => handleFile(e, 2)} />
                </label>
              </>
            )}

            {cameraFor === 2 && (
              <div className="camera-box">
                <video ref={videoRef} autoPlay />
                <button onClick={capturePhoto}>Capture</button>
                <canvas ref={canvasRef} style={{ display: "none" }} />
              </div>
            )}

            {preview2 && (
              <>
                <img src={preview2} className="image-preview" />

                {!image2Submitted && (
                  <div style={{ display: "flex", gap: "10px" }}>
                    <button onClick={() => retakeImage(2)}>
                      Retake
                    </button>

                    <button onClick={() => setImage2Submitted(true)}>
                      Submit
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
        <button className="register-btn" onClick={registerStudent}>
          Register Student
        </button>

        {msg && (
          <p className={isError ? "error_message" : "success_message"}>
            {msg}
          </p>
        )}
      </div>
    </div>
  );
}
