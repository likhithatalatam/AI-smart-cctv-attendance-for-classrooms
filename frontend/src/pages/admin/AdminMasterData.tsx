import { useEffect, useState } from "react";
import axios from "axios";
import "../../styles/masterData.css";
import { useNavigate } from "react-router-dom";

const API = import.meta.env.VITE_API_BASE || "http://127.0.0.1:5000";

type TabType = "branches" | "batches" | "subjects" | "sections";

export default function MasterData() {
    const [activeTab, setActiveTab] = useState<TabType>("branches");
    const [data, setData] = useState<any[]>([]);
    const [showModal, setShowModal] = useState(false);
    const [formData, setFormData] = useState<any>({});
    const [branches, setBranches] = useState<any[]>([]);
    const [batches, setBatches] = useState<any[]>([]);
    const [editId, setEditId] = useState<number | null>(null);
    const navigate = useNavigate();
    const token = localStorage.getItem("token");


    const fetchBranches = async () => {
        const res = await axios.get(API + "/api/admin/branches", {
            headers: { Authorization: `Bearer ${token}` },
        });
        setBranches(res.data);
    };

    const fetchBatches = async () => {
        const res = await axios.get(API + "/api/admin/batches", {
            headers: { Authorization: `Bearer ${token}` },
        });
        setBatches(res.data);
    };

    /* ---------------- FETCH ACTIVE TAB DATA ---------------- */
    useEffect(() => {
        fetchData();
    }, [activeTab]);

    const fetchData = async () => {
        let url = "";

        if (activeTab === "branches") url = "/api/admin/branches";
        if (activeTab === "batches") url = "/api/admin/batches";
        if (activeTab === "subjects") url = "/api/admin/subjects";
        if (activeTab === "sections") url = "/api/admin/sections";

        const res = await axios.get(API + url, {
            headers: { Authorization: `Bearer ${token}` },
        });

        setData(res.data);
    };


    useEffect(() => {
        fetchBranches();
        fetchBatches();
    }, []);

    /* ---------------- BRANCH MAP ---------------- */
    const branchMap: Record<number, string> = {};
    branches.forEach((b) => {
        branchMap[b.id] = b.name;
    });
    const batchMap: Record<number, string> = {};
    batches.forEach((b) => {
        batchMap[b.id] = b.label;
    });

    const handleEdit = (row: any) => {
        setEditId(row.id);        // mark edit mode
        setFormData({ ...row });
        setShowModal(true);
    };

    /* ---------------- ADD HANDLER ---------------- */
    const handleAdd = async () => {
        if (activeTab === "sections") {
            if (
                !formData.name ||
                !formData.batch_id ||
                !formData.branch_id ||
                !formData.year
            ) {
                alert("Please fill all fields");
                return;
            }
        }
        let url = "";

        if (activeTab === "branches") url = "/api/admin/branches";
        if (activeTab === "batches") url = "/api/admin/batches";
        if (activeTab === "subjects") url = "/api/admin/subjects";
        if (activeTab === "sections") url = "/api/admin/sections";
        if (activeTab === "branches") {
            if (!formData.name || !formData.batch_id) {
                alert("Select batch and enter branch name");
                return;
            }
        }
        const payload: any = {};

        if (activeTab === "branches") {
            payload.name = formData.name;
            payload.batch_id = formData.batch_id;
        }

        if (activeTab === "sections") {
            payload.name = formData.name;
            payload.batch_id = formData.batch_id;
            payload.branch_id = formData.branch_id;
            payload.year = formData.year;
        }

        if (activeTab === "subjects") {
            payload.name = formData.name;
            payload.batch_id = formData.batch_id;
            payload.branch_id = formData.branch_id;
            payload.year = formData.year;
        }

        if (activeTab === "batches") {
            payload.start_year = formData.start_year;
            payload.end_year = formData.end_year;
        }

        if (editId) {
            await axios.put(`${API}${url}/${editId}`, payload, {
                headers: { Authorization: `Bearer ${token}` },
            });
        } else {
            await axios.post(API + url, payload, {
                headers: { Authorization: `Bearer ${token}` },
            });
        }

        setShowModal(false);
        setFormData({});

        //refresh active table
        await fetchData();

        //refresh master dropdown sources
        await fetchBatches();
        await fetchBranches();
    };

    /* ---------------- DELETE HANDLER ---------------- */
    const handleDelete = async (id: number) => {
        const isBatch = activeTab === "batches";

        const message = isBatch
            ? "Deleting this batch will REMOVE all students, branches, sections, subjects and attendance. Continue?"
            : "Are you sure you want to delete this item?";

        if (!window.confirm(message)) return;

        let url = "";

        if (activeTab === "branches") url = `/api/admin/branches/${id}`;
        if (activeTab === "batches") url = `/api/admin/batches/${id}`;
        if (activeTab === "subjects") url = `/api/admin/subjects/${id}`;
        if (activeTab === "sections") url = `/api/admin/sections/${id}`;

        await axios.delete(API + url, {
            headers: { Authorization: `Bearer ${token}` },
        });

        fetchData();
    };

    /* ---------------- COLUMN ORDER (ID REMOVED) ---------------- */
    const columnMap: Record<TabType, string[]> = {
        batches: ["label", "start_year", "end_year"],
        branches: ["batch_id", "name"],
        sections: ["batch_id", "branch_id", "name", "year"],
        subjects: ["batch_id", "branch_id", "year", "name"],
    };

    return (
        <div className="master-container">
            <h2 className="master-title">Master Data</h2>
            <p className="master-subtitle">
                Manage branches, sections, batches and subjects
            </p>

            {/* Tabs */}
            <div className="master-tabs">
                {["batches", "branches", "sections", "subjects"].map((tab) => (
                    <button
                        key={tab}
                        className={`tab-btn ${activeTab === tab ? "active" : ""}`}
                        onClick={() => setActiveTab(tab as TabType)}
                    >
                        {tab.toUpperCase()}
                    </button>
                ))}
            </div>

            {/* Card */}
            <div className="master-card">
                <div className="master-card-header">
                    <h3>{activeTab.toUpperCase()}</h3>
                    <button
                        className="add-btn"
                        onClick={() => {
                            setFormData({
                                name: "",
                                batch_id: null,
                                branch_id: null,
                                year: null,
                            });
                            setShowModal(true);
                        }}
                    >
                        + Add
                    </button>
                </div>
                <div className="master-table-wrapper">
                    <table className="master-table">
                        <thead>
                            <tr>
                                <th>S.No</th>
                                {columnMap[activeTab].map((col) => (
                                    <th key={col}>
                                        {col === "branch_id"
                                            ? "Branch"
                                            : col === "batch_id"
                                                ? "Batch"
                                                : col === "year"
                                                    ? "Year"
                                                    : col === "name" && activeTab === "branches"
                                                        ? "Branch"
                                                        : col === "name" && activeTab === "sections"
                                                            ? "Section"
                                                            : col === "name" && activeTab === "subjects"
                                                                ? "Subject"
                                                                : col === "label"
                                                                    ? "Batch"
                                                                    : col}
                                    </th>
                                ))}
                                <th>Actions</th>
                            </tr>
                        </thead>

                        <tbody>
                            {data.map((row, idx) => (
                                <tr key={row.id}>
                                    <td>{idx + 1}</td>

                                    {columnMap[activeTab].map((col) => (
                                        <td key={col}>
                                            {col === "branch_id"
                                                ? branchMap[row.branch_id] || "-"
                                                : col === "batch_id"
                                                    ? batchMap[row.batch_id] || "-"
                                                    : String(row[col] ?? "-")}
                                        </td>
                                    ))}

                                    <td style={{ display: "flex", gap: "8px" }}>
                                        <button
                                            className="edit-btn"
                                            onClick={() => handleEdit(row)}
                                        >
                                            Edit
                                        </button>

                                        <button
                                            className="delete-btn"
                                            onClick={() => handleDelete(row.id)}
                                        >
                                            Delete
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* ADD MODAL */}
            {showModal && (
                <div className="modal-overlay">
                    <div className="modal-box">
                        <h3>Add {activeTab.slice(0, -1)}</h3>

                        {/* BRANCH */}
                        {activeTab === "branches" && (
                            <>
                                <input
                                    type="text"
                                    placeholder="Branch name"
                                    value={formData.name || ""}
                                    onChange={(e) =>
                                        setFormData({ ...formData, name: e.target.value.toUpperCase() })
                                    }
                                />

                                {/* SELECT BATCH FIRST */}
                                <select
                                    value={formData.batch_id || ""}
                                    onChange={(e) =>
                                        setFormData({
                                            ...formData,
                                            batch_id: e.target.value ? Number(e.target.value) : null
                                        })
                                    }
                                >
                                    <option value="">Select Batch</option>
                                    {batches.map((b) => (
                                        <option key={b.id} value={b.id}>
                                            {b.label}
                                        </option>
                                    ))}
                                </select>
                            </>
                        )}

                        {/* SECTION */}
                        {activeTab === "sections" && (
                            <>
                                <input
                                    type="text"
                                    placeholder="Section name (A / B / C)"
                                    value={formData.name || ""}
                                    onChange={(e) =>
                                        setFormData({ ...formData, name: e.target.value.toUpperCase() })
                                    }
                                />

                                {/* STEP 1: BATCH */}
                                <select
                                    value={formData.batch_id ?? ""}
                                    onChange={(e) => {
                                        const value = e.target.value;

                                        setFormData({
                                            ...formData,
                                            batch_id: value ? Number(value) : null,
                                            branch_id: null,
                                        });
                                    }}
                                >
                                    <option value="">Select Batch</option>
                                    {batches.map((b) => (
                                        <option key={b.id} value={b.id}>
                                            {b.label}
                                        </option>
                                    ))}
                                </select>

                                {/* STEP 2: BRANCH (FILTERED BY BATCH) */}
                                <select
                                    value={formData.branch_id ?? ""}
                                    disabled={!formData.batch_id}
                                    onChange={(e) => {
                                        const value = e.target.value;

                                        setFormData({
                                            ...formData,
                                            branch_id: value ? Number(value) : null,
                                        });
                                    }}
                                >
                                    <option value="">
                                        {formData.batch_id ? "Select Branch" : "Select Batch First"}
                                    </option>

                                    {branches
                                        .filter((b) => b.batch_id === formData.batch_id)
                                        .map((b) => (
                                            <option key={b.id} value={b.id}>
                                                {b.name}
                                            </option>
                                        ))}
                                </select>

                                {/* YEAR */}
                                <select
                                    value={formData.year ?? ""}
                                    onChange={(e) => {
                                        const value = e.target.value;

                                        setFormData({
                                            ...formData,
                                            year: value ? Number(value) : null,
                                        });
                                    }}
                                >
                                    <option value="">Select Year</option>
                                    <option value={1}>1st Year</option>
                                    <option value={2}>2nd Year</option>
                                    <option value={3}>3rd Year</option>
                                    <option value={4}>4th Year</option>
                                </select>
                            </>
                        )}


                        {/* BATCH */}
                        {activeTab === "batches" && (
                            <>
                                <input
                                    type="number"
                                    placeholder="Start year"
                                    value={formData.start_year || ""}
                                    onChange={(e) =>
                                        setFormData({
                                            ...formData,
                                            start_year: Number(e.target.value),
                                        })
                                    }
                                />
                                <input
                                    type="number"
                                    placeholder="End year"
                                    value={formData.end_year || ""}
                                    onChange={(e) =>
                                        setFormData({
                                            ...formData,
                                            end_year: Number(e.target.value),
                                        })
                                    }
                                />
                            </>
                        )}

                        {/* SUBJECT */}
                        {activeTab === "subjects" && (
                            <>
                                <input
                                    type="text"
                                    placeholder="Subject name"
                                    value={formData.name || ""}
                                    onChange={(e) =>
                                        setFormData({ ...formData, name: e.target.value })
                                    }
                                />
                                <select
                                    value={formData.batch_id || ""}
                                    onChange={(e) =>
                                        setFormData({
                                            ...formData,
                                            batch_id: Number(e.target.value),
                                            branch_id: null, // reset
                                        })
                                    }
                                >
                                    <option value="">Select Batch</option>
                                    {batches.map(b => (
                                        <option key={b.id} value={b.id}>
                                            {b.label}
                                        </option>
                                    ))}
                                </select>
                                <select
                                    value={formData.branch_id || ""}
                                    onChange={(e) =>
                                        setFormData({
                                            ...formData,
                                            branch_id: Number(e.target.value),
                                        })
                                    }
                                >
                                    <option value="">Select Branch</option>
                                    {branches
                                        .filter(b => b.batch_id === formData.batch_id)
                                        .map((b) => (
                                            <option key={b.id} value={b.id}>
                                                {b.name}
                                            </option>
                                        ))}
                                </select>

                                <select
                                    value={formData.year || ""}
                                    onChange={(e) =>
                                        setFormData({
                                            ...formData,
                                            year: Number(e.target.value),
                                        })
                                    }
                                >
                                    <option value="">Select Year</option>
                                    <option value={1}>1st Year</option>
                                    <option value={2}>2nd Year</option>
                                    <option value={3}>3rd Year</option>
                                    <option value={4}>4th Year</option>
                                </select>
                            </>
                        )}

                        <div className="modal-actions">
                            <button onClick={() => setShowModal(false)}>Cancel</button>
                            <button className="save-btn" onClick={handleAdd}>
                                {editId ? "Update" : "Save"}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
