import { useEffect, useRef, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import "../styles/register.css";

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

  /* ===== Images ===== */
  const [image1, setImage1] = useState<File | null>(null);
  const [image2, setImage2] = useState<File | null>(null);
  const [preview1, setPreview1] = useState<string | null>(null);
  const [preview2, setPreview2] = useState<string | null>(null);

  /* ===== Camera ===== */
  const [cameraFor, setCameraFor] = useState<1 | 2 | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  /* ===== Auth check ===== */
  useEffect(() => {
    if (!localStorage.getItem("token")) {
      navigate("/");
    }
  }, [navigate]);

  /* ===== Open Camera ===== */
  const openCamera = async (imgNo: 1 | 2) => {
    setCameraFor(imgNo);
    const stream = await navigator.mediaDevices.getUserMedia({ video: true });

    if (videoRef.current) {
      videoRef.current.srcObject = stream;
      videoRef.current.play();
    }
  };

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
      } else {
        setImage2(file);
        setPreview2(previewURL);
      }
    });

    const stream = video.srcObject as MediaStream;
    stream.getTracks().forEach((t) => t.stop());
    setCameraFor(null);
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
    } else {
      setImage2(file);
      setPreview2(previewURL);
    }
  };

  /* ===== Register Student ===== */
  const registerStudent = async () => {
    setMsg("");

    try {
      const formData = new FormData();
      formData.append("roll_no", rollNo);
      formData.append("name", name);
      formData.append("department", department);
      formData.append("year", year);
      formData.append("section", section);
      formData.append("image1", image1!);
      formData.append("image2", image2!);

      await axios.post(`${API}/api/register_student`, formData, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
          "Content-Type": "multipart/form-data",
        },
      });

      setMsg("Student registered successfully");

      setRollNo("");
      setName("");
      setDepartment("");
      setYear("");
      setSection("");
      setImage1(null);
      setImage2(null);
      setPreview1(null);
      setPreview2(null);
    } catch (err: any) {
      setMsg(err.response?.data?.error || "Registration failed");
    }
  };

  /* ===== Form Validation ===== */
  const isFormValid =
    rollNo &&
    name &&
    department &&
    year &&
    section &&
    image1 &&
    image2;

  return (
    <div className="register-page">
      <h1 className="register-title">Student Registration</h1>
      <p className="register-subtitle">
        Enter student details and upload two images
      </p>

      <div className="register-card">
        {/* ===== Form Fields ===== */}
        <div className="form-grid">
          <input
            placeholder="Roll Number"
            value={rollNo}
            onChange={(e) => setRollNo(e.target.value)}
          />

          <input
            placeholder="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />

          <select
            value={department}
            onChange={(e) => setDepartment(e.target.value)}
          >
            <option value="">Select Department</option>
            {DEPARTMENTS.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>

          <select value={year} onChange={(e) => setYear(e.target.value)}>
            <option value="">Select Year</option>
            {YEARS.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>

          <select
            value={section}
            onChange={(e) => setSection(e.target.value)}
          >
            <option value="">Select Section</option>
            {SECTIONS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        {/* ===== Image Upload ===== */}
        <div className="upload-grid">
          <div className="upload-box">
            <h4>Image 1</h4>
            <button onClick={() => openCamera(1)}>Open Camera</button>
            <label className="file-upload">
              Upload Image
              <input
                type="file"
                accept="image/*"
                onChange={(e) => handleFile(e, 1)}
                hidden
              />
            </label>
            {preview1 && (
              <img src={preview1} className="image-preview" />
            )}
          </div>

          <div className="upload-box">
            <h4>Image 2</h4>
            <button onClick={() => openCamera(2)}>Open Camera</button>
            <label className="file-upload">
              Upload Image
              <input
                type="file"
                accept="image/*"
                onChange={(e) => handleFile(e, 2)}
                hidden
              />
            </label>

            {preview2 && (
              <img src={preview2} className="image-preview" />
            )}
          </div>
        </div>

        {/* ===== Submit ===== */}
        <button
          className="register-btn"
          onClick={registerStudent}
          disabled={!isFormValid}
        >
          Register Student
        </button>

        {msg && <p className="success_message">{msg}</p>}

        {/* ===== Camera Preview ===== */}
        {cameraFor && (
          <div className="camera-box">
            <video ref={videoRef} autoPlay />
            <button onClick={capturePhoto}>Capture</button>
            <canvas ref={canvasRef} style={{ display: "none" }} />
          </div>
        )}
      </div>
    </div>
  );
}
