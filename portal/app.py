# portal/app.py
"""
Drop-in Flask backend for CCTV Attendance (sqlite default).

Dependencies (pip):
  pip install Flask Flask_SQLAlchemy Flask_Migrate Flask-CORS PyJWT passlib

This file provides:
- models: User, Student, Attendance, RecognitionLog
- endpoints: student registration, listing/search, manual & auto attendance marking
- JWT-based auth (simple): /api/login
- CORS enabled
- SQLite by default (change SQLALCHEMY_DATABASE_URI in config)

Adjust SECRET_KEY and JWT settings for production.
"""

import os
import datetime
import threading
from functools import wraps

from flask import Flask, request, jsonify, g
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from passlib.hash import pbkdf2_sha256
from datetime import date
from werkzeug.security import generate_password_hash
import jwt
import io
import pandas as pd
from flask import send_file
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.platypus import Spacer
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.styles import getSampleStyleSheet
from encoding_utils import update_encodings


def draw_page_border(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.black)
    canvas.setLineWidth(1)
    canvas.rect(25, 25, A4[0] - 50, A4[1] - 50)
    canvas.restoreState()


# ---------- App ----------
APP = Flask(__name__)
# ---------- CORS ----------
CORS(
    APP,
    resources={
        r"/api/*": {"origins": ["http://localhost:5173", "http://localhost:5174"]}
    },
    supports_credentials=True,
    allow_headers=["Authorization", "Content-Type"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
)
from flask import make_response


def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == "OPTIONS":
            return "", 200

        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return jsonify({"error": "Token missing"}), 401

        try:
            token = auth_header.split(" ")[1]
            data = jwt.decode(token, APP.config["SECRET_KEY"], algorithms=["HS256"])
            request.user = data
        except Exception:
            return jsonify({"error": "Invalid or expired token"}), 401

        return f(*args, **kwargs)

    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = getattr(request, "user", None)
        print("USER ROLE: ", user)
        if not user:
            return jsonify({"error": "Unauthorized"}), 401

        if user.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403

        return f(*args, **kwargs)

    return decorated


@APP.route("/api/sections", methods=["GET"])
@auth_required
def list_sections_public():
    batch_id = request.args.get("batch_id")
    branch_id = request.args.get("branch_id")
    year = request.args.get("year")

    query = Section.query
    if batch_id:
        query = query.filter_by(batch_id=int(batch_id))
    if branch_id:
        query = query.filter_by(branch_id=int(branch_id))
    if year:
        query = query.filter_by(year=int(year))

    return jsonify([{"id": s.id, "name": s.name} for s in query.all()])


@APP.route("/api/batches", methods=["GET"])
@auth_required
def list_batches_public():
    batches = Batch.query.all()
    return jsonify(
        [
            {
                "id": b.id,
                "start_year": b.start_year,
                "end_year": b.end_year,
                "label": f"{b.start_year}-{b.end_year}",
            }
            for b in batches
        ]
    )


@APP.route("/api/branches", methods=["GET"])
@auth_required
def list_branches_public():
    batch_id = request.args.get("batch_id")

    query = Branch.query

    if batch_id:
        query = query.filter_by(batch_id=int(batch_id))

    branches = query.order_by(Branch.name).all()

    return jsonify(
        [{"id": b.id, "name": b.name, "batch_id": b.batch_id} for b in branches]
    )


@APP.route("/api/subjects", methods=["GET", "OPTIONS"])
@auth_required
def list_subjects_public():
    if request.method == "OPTIONS":
        return "", 200

    batch_id = request.args.get("batch_id")
    branch_id = request.args.get("branch_id")
    year = request.args.get("year")

    query = Subject.query
    if batch_id:
        query = query.filter_by(batch_id=int(batch_id))
    if branch_id:
        query = query.filter_by(branch_id=int(branch_id))
    if year:
        query = query.filter_by(year=int(year))

    return jsonify(
        [
            {
                "id": s.id,
                "name": s.name,
                "batch_id": s.batch_id,
                "branch_id": s.branch_id,
                "year": s.year,
            }
            for s in query.all()
        ]
    )


@APP.route("/api/admin/subjects", methods=["GET"])
@auth_required
def list_admin_subjects():
    batch_id = request.args.get("batch_id")
    branch_id = request.args.get("branch_id")
    year = request.args.get("year")

    query = Subject.query

    if batch_id:
        query = query.filter_by(batch_id=int(batch_id))

    if branch_id:
        query = query.filter_by(branch_id=int(branch_id))

    if year:
        query = query.filter_by(year=int(year))

    subjects = query.order_by(Subject.name.asc()).all()

    return (
        jsonify(
            [
                {
                    "id": s.id,
                    "name": s.name,
                    "batch_id": s.batch_id,
                    "branch_id": s.branch_id,
                    "year": s.year,
                }
                for s in subjects
            ]
        ),
        200,
    )


# allow all origins for now (development)

# ---------- Base directory ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------- Config ----------
APP.config["SQLALCHEMY_DATABASE_URI"] = (
    "mysql+pymysql://cctv_user:cctv123@localhost:3306/cctv_attendance"
)

APP.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
APP.config["SECRET_KEY"] = "dev-secret"
APP.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB upload
APP.config["JWT_EXP_DELTA_SECONDS"] = 60 * 60 * 24  # 24 hours


# ---------- Database ----------
DB = SQLAlchemy(APP)
MIGRATE = Migrate(APP, DB)


# ---------- Models ----------
class User(DB.Model):
    __tablename__ = "users"
    id = DB.Column(DB.Integer, primary_key=True)
    username = DB.Column(DB.String(150), unique=True, nullable=False)
    password_hash = DB.Column(DB.String(255), nullable=False)
    role = DB.Column(DB.String(50), default="admin")  # admin / staff
    role = DB.Column(DB.String(50), default="faculty")

    def set_password(self, password):
        self.password_hash = pbkdf2_sha256.hash(password)

    def verify_password(self, password):
        return pbkdf2_sha256.verify(password, self.password_hash)


class Student(DB.Model):
    __tablename__ = "students"
    id = DB.Column(DB.Integer, primary_key=True)
    roll_no = DB.Column(DB.String(64), unique=True, nullable=False)
    name = DB.Column(DB.String(200), nullable=False)

    batch_id = DB.Column(
        DB.Integer, DB.ForeignKey("batches.id"), nullable=False
    )  # ✅ ADD

    department = DB.Column(DB.String(128))
    year = DB.Column(DB.String(32))
    section = DB.Column(DB.String(32))
    photo_url = DB.Column(DB.String(1024))


class PeriodSubject(DB.Model):
    __tablename__ = "period_subjects"

    id = DB.Column(DB.Integer, primary_key=True)
    batch_id = DB.Column(DB.Integer, nullable=False)
    branch_id = DB.Column(DB.Integer, nullable=False)
    year = DB.Column(DB.Integer, nullable=False)
    section = DB.Column(DB.String(50), nullable=False)
    date = DB.Column(DB.Date, nullable=False)
    period = DB.Column(DB.Integer, nullable=False)
    subject_id = DB.Column(DB.Integer, nullable=False)


class AttendanceSettings(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    start_date = DB.Column(DB.Date, nullable=False)
    end_date = DB.Column(DB.Date, nullable=False)
    holidays = DB.Column(DB.JSON, nullable=True)  # list of dates
    exclude_sundays = DB.Column(DB.Boolean, default=True)


class Attendance(DB.Model):
    __tablename__ = "attendances"
    id = DB.Column(DB.Integer, primary_key=True)
    student_id = DB.Column(DB.Integer, DB.ForeignKey("students.id"), nullable=False)
    timestamp = DB.Column(DB.DateTime, default=datetime.datetime.utcnow, nullable=False)
    method = DB.Column(DB.String(50), default="manual")  # manual / recognition
    source = DB.Column(DB.String(255), nullable=True)
    period = DB.Column(DB.Integer, nullable=True)  # ✅ ADD
    subject_id = DB.Column(DB.Integer, nullable=True)  # ✅ ADD
    extra = DB.Column(DB.JSON, nullable=True)


class Branch(DB.Model):
    __tablename__ = "branches"
    id = DB.Column(DB.Integer, primary_key=True)
    name = DB.Column(DB.String(100), nullable=False)
    batch_id = DB.Column(DB.Integer, DB.ForeignKey("batches.id"), nullable=False)


class Section(DB.Model):
    __tablename__ = "sections"
    id = DB.Column(DB.Integer, primary_key=True)
    name = DB.Column(DB.String(50), nullable=False)
    batch_id = DB.Column(DB.Integer, DB.ForeignKey("batches.id"), nullable=False)
    branch_id = DB.Column(DB.Integer, DB.ForeignKey("branches.id"), nullable=False)
    year = DB.Column(DB.Integer, nullable=False)


class Batch(DB.Model):
    __tablename__ = "batches"
    id = DB.Column(DB.Integer, primary_key=True)
    start_year = DB.Column(DB.Integer, nullable=False)
    end_year = DB.Column(DB.Integer, nullable=False)


class Subject(DB.Model):
    __tablename__ = "subjects"
    id = DB.Column(DB.Integer, primary_key=True)
    name = DB.Column(DB.String(100), nullable=False)
    branch_id = DB.Column(DB.Integer, DB.ForeignKey("branches.id"), nullable=False)
    year = DB.Column(DB.Integer, nullable=False)
    batch_id = DB.Column(DB.Integer, DB.ForeignKey("batches.id"), nullable=False)


class RecognitionLog(DB.Model):
    __tablename__ = "recognition_logs"
    id = DB.Column(DB.Integer, primary_key=True)
    recognized_id = DB.Column(
        DB.String(128), nullable=False
    )  # could be roll_no or face-id
    student_id = DB.Column(DB.Integer, DB.ForeignKey("students.id"), nullable=True)
    timestamp = DB.Column(DB.DateTime, default=datetime.datetime.utcnow, nullable=False)
    confidence = DB.Column(DB.Float, nullable=True)
    meta = DB.Column(DB.JSON, nullable=True)


# ---------- Helpers: JWT auth ----------
def generate_token(user):
    payload = {
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "exp": datetime.datetime.utcnow()
        + datetime.timedelta(seconds=APP.config["JWT_EXP_DELTA_SECONDS"]),
    }
    return jwt.encode(payload, APP.config["SECRET_KEY"], algorithm="HS256")


def decode_token(token):
    try:
        payload = jwt.decode(token, APP.config["SECRET_KEY"], algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except Exception:
        return None


from functools import wraps
from flask import request, jsonify, g


# ---------- API endpoints ----------


@APP.route("/api/ping", methods=["GET"])
def ping():
    return (
        jsonify({"status": "ok", "time": datetime.datetime.utcnow().isoformat()}),
        200,
    )


# ---- Auth ----
@APP.route("/api/login", methods=["POST"])
def login():
    try:
        data = request.get_json(force=True)
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return jsonify({"error": "username and password required"}), 400

        user = User.query.filter_by(username=username).first()
        if not user or not user.verify_password(password):
            return jsonify({"error": "invalid credentials"}), 401

        token = generate_token(user)

        return (
            jsonify(
                {
                    "token": token,
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "role": user.role,
                    },
                }
            ),
            200,
        )

    except Exception as e:
        print("LOGIN ERROR:", e)
        return jsonify({"error": str(e)}), 500


@APP.route("/api/logout", methods=["POST"])
def logout():
    # JWT is stateless; instruct client to remove token.
    return jsonify({"msg": "ok"}), 200


@APP.route("/api/dashboard-stats", methods=["GET"])
@auth_required
def dashboard_stats():
    total_students = Student.query.count()
    today = datetime.date.today()

    start = datetime.datetime.combine(today, datetime.time.min)
    end = datetime.datetime.combine(today, datetime.time.max)

    records = (
        Attendance.query.filter(
            Attendance.timestamp >= start,
            Attendance.timestamp <= end,
            Attendance.method.in_(["manual", "recognition"]),
        )
        .order_by(Attendance.timestamp.desc())
        .all()
    )

    student_status = {}

    for r in records:
        if r.student_id not in student_status:
            status = r.extra.get("status") if r.extra else "present"
            student_status[r.student_id] = status

    present_today = sum(1 for status in student_status.values() if status == "present")

    absent_today = max(total_students - present_today, 0)

    attendance_rate = (
        round((present_today / total_students) * 100, 2) if total_students > 0 else 0
    )

    return (
        jsonify(
            {
                "totalStudents": total_students,
                "presentToday": present_today,
                "absentToday": absent_today,
                "attendanceRate": attendance_rate,
            }
        ),
        200,
    )


# ---- Student registration & listing ----
@APP.route("/api/register_student", methods=["POST"])
@auth_required
def register_student():
    try:
        roll_no = request.form.get("roll_no", "").strip().upper()

        name = request.form.get("name", "").strip().upper()

        department = request.form.get("department", "").strip().upper()
        year = request.form.get("year", "").strip()
        section = request.form.get("section", "").strip().upper()
        batch_id = int(request.form.get("batch"))

        # 🔹 CHECK DUPLICATE ROLL NUMBER
        existing_student = Student.query.filter_by(roll_no=roll_no).first()

        if existing_student:
            return jsonify({"error": "Student already exists"}), 400

        image1 = request.files.get("image1")
        image2 = request.files.get("image2")

        if not roll_no or not name:
            return jsonify({"error": "roll_no and name required"}), 400

        if not image1 or not image2:
            return jsonify({"error": "Two images are required"}), 400

        if Student.query.filter_by(roll_no=roll_no).first():
            return jsonify({"error": "Student already exists"}), 409

        dataset_base = os.path.join(BASE_DIR, "dataset")
        os.makedirs(dataset_base, exist_ok=True)

        student_dir = os.path.join(dataset_base, roll_no)
        os.makedirs(student_dir, exist_ok=True)

        img1_path = os.path.join(student_dir, "img1.jpg")
        img2_path = os.path.join(student_dir, "img2.jpg")

        image1.save(img1_path)
        image2.save(img2_path)

        student = Student(
            roll_no=roll_no,
            name=name,
            department=department,
            year=year,
            section=section,
            batch_id=batch_id,
        )

        DB.session.add(student)
        DB.session.commit()

        # 🔹 Run encoding in background (non-blocking)
        def background_encoding():
            try:
                update_encodings(roll_no, [img1_path, img2_path])
                print(f"Encoding completed for {roll_no}")
            except Exception as e:
                print("Encoding failed:", e)

        threading.Thread(target=background_encoding).start()

        return (
            jsonify({"msg": "Student registered successfully", "roll_no": roll_no}),
            201,
        )

    except Exception as e:
        print("REGISTER ERROR:", e)
        return jsonify({"error": str(e)}), 500


@APP.route("/api/admin/period-subjects", methods=["POST"])
@auth_required
def save_period_subjects():
    data = request.json or {}

    batch = data.get("batch")
    branch_id = data.get("branch_id")
    year = data.get("year")
    section = data.get("section")
    date_str = data.get("date")
    period_subjects = data.get("periodSubjects")

    if (
        not batch
        or not branch_id
        or not year
        or not section
        or not date_str
        or not period_subjects
    ):
        return jsonify({"error": "Missing fields"}), 400

    try:
        date_obj = datetime.date.fromisoformat(date_str)
    except ValueError:
        return jsonify({"error": "Invalid date format"}), 400

    # Delete only for this specific section + date
    PeriodSubject.query.filter_by(
        batch_id=int(batch),
        branch_id=int(branch_id),
        year=int(year),
        section=section,
        date=date_obj,
    ).delete()

    # Insert new records
    for period, subject_id in period_subjects.items():
        ps = PeriodSubject(
            batch_id=int(batch),
            branch_id=int(branch_id),
            year=int(year),
            section=section,
            date=date_obj,
            period=int(period),
            subject_id=int(subject_id),
        )
        DB.session.add(ps)

    DB.session.commit()

    return jsonify({"msg": "Period subjects saved"}), 200


@APP.route("/api/period-subjects", methods=["GET"])
@auth_required
def fetch_period_subjects():
    batch = request.args.get("batch")
    branch_id = request.args.get("branch_id")
    year = request.args.get("year")
    section = request.args.get("section")
    date_str = request.args.get("date")

    if not batch or not branch_id or not year or not section or not date_str:
        return jsonify({}), 200

    try:
        date_obj = datetime.date.fromisoformat(date_str)
    except ValueError:
        return jsonify({}), 200

    records = PeriodSubject.query.filter_by(
        batch_id=int(batch),
        branch_id=int(branch_id),
        year=int(year),
        section=section,
        date=date_obj,
    ).all()

    result = {}

    for r in records:
        result[r.period] = r.subject_id

    return jsonify(result), 200


@APP.route("/api/admin/branches", methods=["POST"])
@auth_required
@admin_required
def add_branch():
    data = request.get_json() or {}

    name = data.get("name", "").strip().upper()
    batch_id = data.get("batch_id")

    if not name or not batch_id:
        return jsonify({"error": "name and batch_id required"}), 400

    exists = Branch.query.filter_by(name=name, batch_id=batch_id).first()

    if exists:
        return jsonify({"error": "Branch already exists for this batch"}), 409

    branch = Branch(name=name, batch_id=batch_id)
    DB.session.add(branch)
    DB.session.commit()

    return jsonify({"message": "Branch added"}), 201


@APP.route("/api/admin/batches", methods=["GET"])
@auth_required
def list_batches():
    batches = Batch.query.all()

    result = []
    for b in batches:
        result.append(
            {
                "id": b.id,
                "start_year": b.start_year,
                "end_year": b.end_year,
                "label": (
                    f"{b.start_year}-{b.end_year}"
                    if b.start_year and b.end_year
                    else "-"
                ),
            }
        )

    return jsonify(result), 200


@APP.route("/api/admin/branches/<int:id>", methods=["DELETE"])
@auth_required
@admin_required
def delete_branch(id):
    branch = Branch.query.get(id)
    if not branch:
        return jsonify({"error": "Branch not found"}), 404

    DB.session.delete(branch)
    DB.session.commit()
    return jsonify({"message": "Branch deleted"}), 200


@APP.route("/api/admin/branches/<int:id>", methods=["PUT"])
@auth_required
@admin_required
def update_branch(id):
    branch = Branch.query.get(id)
    if not branch:
        return jsonify({"error": "Branch not found"}), 404

    data = request.get_json() or {}

    name = (data.get("name") or "").strip().upper()
    batch_id = data.get("batch_id")

    if not name or batch_id is None:
        return jsonify({"error": "name and batch_id required"}), 400

    # duplicate check
    exists = Branch.query.filter(
        Branch.name == name, Branch.batch_id == batch_id, Branch.id != id
    ).first()

    if exists:
        return jsonify({"error": "Branch already exists"}), 409

    branch.name = name
    branch.batch_id = batch_id
    DB.session.commit()

    return jsonify({"message": "Branch updated"}), 200


@APP.route("/api/admin/users", methods=["POST"])
@auth_required
@admin_required
def create_user():
    data = request.json or {}

    username = data.get("username")
    password = data.get("password")
    role = data.get("role", "faculty")

    if not username or not password:
        return jsonify({"error": "username and password required"}), 400

    # check duplicate user
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "User already exists"}), 409

    user = User(username=username, role=role)
    user.set_password(password)

    DB.session.add(user)
    DB.session.commit()

    return jsonify({"message": "User created", "role": role}), 201


@APP.route("/api/admin/sections", methods=["POST"])
@auth_required
@admin_required
def add_section():
    try:
        data = request.get_json() or {}
        print("RAW DATA:", data)

        name = (data.get("name") or "").strip().upper()

        batch_id = data.get("batch_id")
        branch_id = data.get("branch_id")
        year = data.get("year")

        if not name or batch_id is None or branch_id is None or year is None:
            return jsonify({"error": "name, batch_id, branch_id, year required"}), 400

        try:
            batch_id = int(batch_id)
            branch_id = int(branch_id)
            year = int(year)
        except ValueError:
            return jsonify({"error": "IDs must be numbers"}), 400

        exists = Section.query.filter_by(
            name=name, batch_id=batch_id, branch_id=branch_id, year=year
        ).first()

        if exists:
            return jsonify({"error": "Section already exists"}), 409

        section = Section(name=name, batch_id=batch_id, branch_id=branch_id, year=year)

        DB.session.add(section)
        DB.session.commit()

        return jsonify({"message": "Section added"}), 201

    except Exception as e:
        DB.session.rollback()
        print("ADD SECTION ERROR:", e)
        return jsonify({"error": str(e)}), 500


@APP.route("/api/admin/sections", methods=["GET"])
@auth_required
def list_sections():
    try:
        batch_id = request.args.get("batch_id")
        branch_id = request.args.get("branch_id")
        year = request.args.get("year")

        query = Section.query

        if batch_id is not None:
            query = query.filter_by(batch_id=int(batch_id))

        if branch_id is not None:
            query = query.filter_by(branch_id=int(branch_id))

        if year is not None:
            query = query.filter_by(year=int(year))

        sections = query.order_by(Section.name).all()

        return (
            jsonify(
                [
                    {
                        "id": s.id,
                        "name": s.name,
                        "batch_id": s.batch_id,
                        "branch_id": s.branch_id,
                        "year": s.year,
                    }
                    for s in sections
                ]
            ),
            200,
        )

    except Exception as e:
        print("SECTION FILTER ERROR:", e)
        return jsonify({"error": str(e)}), 500


@APP.route("/api/admin/sections/<int:id>", methods=["DELETE"])
@auth_required
@admin_required
def delete_section(id):
    section = Section.query.get(id)

    if not section:
        return jsonify({"error": "Section not found"}), 404

    DB.session.delete(section)
    DB.session.commit()

    return jsonify({"message": "Section deleted"}), 200


@APP.route("/api/admin/sections/<int:id>", methods=["PUT"])
@auth_required
@admin_required
def update_section(id):
    section = Section.query.get(id)
    if not section:
        return jsonify({"error": "Section not found"}), 404

    data = request.get_json() or {}

    name = (data.get("name") or "").strip().upper()
    batch_id = data.get("batch_id")
    branch_id = data.get("branch_id")
    year = data.get("year")

    if not name or batch_id is None or branch_id is None or year is None:
        return jsonify({"error": "All fields required"}), 400

    try:
        batch_id = int(batch_id)
        branch_id = int(branch_id)
        year = int(year)
    except ValueError:
        return jsonify({"error": "IDs must be numbers"}), 400

    # duplicate check
    exists = Section.query.filter(
        Section.name == name,
        Section.batch_id == batch_id,
        Section.branch_id == branch_id,
        Section.year == year,
        Section.id != id,
    ).first()

    if exists:
        return jsonify({"error": "Section already exists"}), 409

    section.name = name
    section.batch_id = batch_id
    section.branch_id = branch_id
    section.year = year
    DB.session.commit()

    return jsonify({"message": "Section updated"}), 200


@APP.route("/api/admin/branches", methods=["GET"])
@auth_required
def list_branches():
    branches = Branch.query.order_by(Branch.batch_id, Branch.name).all()

    return jsonify(
        [
            {"id": b.id, "name": b.name, "batch_id": b.batch_id}  # 🔥 REQUIRED
            for b in branches
        ]
    )


@APP.route("/api/admin/batches", methods=["POST"])
@auth_required
@admin_required
def add_batch():
    data = request.get_json() or {}

    try:
        start_year = int(data.get("start_year"))
        end_year = int(data.get("end_year"))
    except (TypeError, ValueError):
        return jsonify({"error": "start_year and end_year must be numbers"}), 400

    if start_year >= end_year:
        return jsonify({"error": "Invalid batch range"}), 400

    exists = Batch.query.filter_by(start_year=start_year, end_year=end_year).first()

    if exists:
        return jsonify({"error": "Batch already exists"}), 409

    batch = Batch(start_year=start_year, end_year=end_year)
    DB.session.add(batch)
    DB.session.commit()

    return jsonify({"message": "Batch added successfully"}), 201


@APP.route("/api/admin/batches/<int:id>", methods=["DELETE"])
@auth_required
@admin_required
def delete_batch(id):
    batch = Batch.query.get(id)
    if not batch:
        return jsonify({"error": "Batch not found"}), 404

    try:
        students = Student.query.filter_by(batch_id=id).all()
        student_ids = [s.id for s in students]
        if student_ids:
            Attendance.query.filter(Attendance.student_id.in_(student_ids)).delete(
                synchronize_session=False
            )
        Student.query.filter_by(batch_id=id).delete(synchronize_session=False)
        Subject.query.filter_by(batch_id=id).delete(synchronize_session=False)
        Section.query.filter_by(batch_id=id).delete(synchronize_session=False)
        Branch.query.filter_by(batch_id=id).delete(synchronize_session=False)
        DB.session.delete(batch)

        DB.session.commit()

        return jsonify({"message": "Batch and all related data deleted"}), 200

    except Exception as e:
        DB.session.rollback()
        print("DELETE BATCH ERROR:", e)
        return jsonify({"error": "Failed to delete batch", "details": str(e)}), 500


@APP.route("/api/admin/batches/<int:id>", methods=["PUT"])
@auth_required
@admin_required
def update_batch(id):
    batch = Batch.query.get(id)
    if not batch:
        return jsonify({"error": "Batch not found"}), 404

    data = request.get_json() or {}

    try:
        start_year = int(data.get("start_year"))
        end_year = int(data.get("end_year"))
    except (TypeError, ValueError):
        return jsonify({"error": "start_year and end_year must be numbers"}), 400

    if start_year >= end_year:
        return jsonify({"error": "Invalid batch range"}), 400

    # duplicate check
    exists = Batch.query.filter(
        Batch.start_year == start_year, Batch.end_year == end_year, Batch.id != id
    ).first()

    if exists:
        return jsonify({"error": "Batch already exists"}), 409

    batch.start_year = start_year
    batch.end_year = end_year
    DB.session.commit()

    return jsonify({"message": "Batch updated"}), 200


@APP.route("/api/admin/subjects", methods=["POST"])
@auth_required
@admin_required
def add_subject():
    data = request.get_json() or {}

    name = (data.get("name") or "").strip().upper()

    try:
        batch_id = int(data.get("batch_id"))
        branch_id = int(data.get("branch_id"))
        year = int(data.get("year"))
    except (TypeError, ValueError):
        return jsonify({"error": "batch_id, branch_id, year must be numbers"}), 400

    if not name:
        return jsonify({"error": "name required"}), 400

    if year not in [1, 2, 3, 4]:
        return jsonify({"error": "year must be between 1 and 4"}), 400

    exists = Subject.query.filter_by(
        name=name, batch_id=batch_id, branch_id=branch_id, year=year
    ).first()

    if exists:
        return jsonify({"error": "Subject already exists"}), 409

    subject = Subject(
        name=name,
        batch_id=batch_id,
        branch_id=branch_id,
        year=year,
    )

    DB.session.add(subject)
    DB.session.commit()

    return jsonify({"message": "Subject added"}), 201


@APP.route("/api/admin/subjects/<int:id>", methods=["DELETE"])
@auth_required
@admin_required
def delete_subject(id):
    subject = Subject.query.get(id)
    if not subject:
        return jsonify({"error": "Subject not found"}), 404

    DB.session.delete(subject)
    DB.session.commit()
    return jsonify({"message": "Subject deleted"}), 200


@APP.route("/api/admin/subjects/<int:id>", methods=["PUT"])
@auth_required
@admin_required
def update_subject(id):
    subject = Subject.query.get(id)
    if not subject:
        return jsonify({"error": "Subject not found"}), 404

    data = request.get_json() or {}

    name = (data.get("name") or "").strip().upper()
    batch_id = data.get("batch_id")
    branch_id = data.get("branch_id")
    year = data.get("year")

    if not name or batch_id is None or branch_id is None or year is None:
        return jsonify({"error": "All fields required"}), 400

    try:
        batch_id = int(batch_id)
        branch_id = int(branch_id)
        year = int(year)
    except ValueError:
        return jsonify({"error": "IDs must be numbers"}), 400

    # duplicate check
    exists = Subject.query.filter(
        Subject.name == name,
        Subject.batch_id == batch_id,
        Subject.branch_id == branch_id,
        Subject.year == year,
        Subject.id != id,
    ).first()

    if exists:
        return jsonify({"error": "Subject already exists"}), 409

    subject.name = name
    subject.batch_id = batch_id
    subject.branch_id = branch_id
    subject.year = year
    DB.session.commit()

    return jsonify({"message": "Subject updated"}), 200


@APP.route("/api/student/<int:student_id>", methods=["DELETE"])
@auth_required
def delete_student(student_id):
    student = Student.query.get(student_id)
    if not student:
        return jsonify({"error": "student not found"}), 404

    roll_no = student.roll_no

    # delete attendance    Attendance.query.filter_by(student_id=student.id).delete()

    # delete student
    DB.session.delete(student)
    DB.session.commit()

    # delete dataset folder
    dataset_path = os.path.join(BASE_DIR, "dataset", roll_no)
    if os.path.exists(dataset_path):
        import shutil

        shutil.rmtree(dataset_path)

    return jsonify({"msg": "student and dataset deleted"}), 200


@APP.route("/api/students", methods=["GET"])
@auth_required
def list_students():
    dept = request.args.get("dept")
    year = request.args.get("year")
    section = request.args.get("section")
    batch = request.args.get("batch")

    query = Student.query

    if dept:
        query = query.filter_by(department=dept)

    if year:
        query = query.filter_by(year=year)

    if section:
        query = query.filter_by(section=section)

    if batch:
        query = query.filter_by(batch_id=int(batch))  # ✅ NOW VALID

    students = query.order_by(Student.roll_no.asc()).all()

    return (
        jsonify(
            {
                "students": [
                    {
                        "id": s.id,
                        "roll_no": s.roll_no,
                        "name": s.name,
                        "department": s.department,
                        "year": s.year,
                        "section": s.section,
                    }
                    for s in students
                ]
            }
        ),
        200,
    )


# @APP.route("/api/admin/subjects", methods=["GET"])
# @auth_required
# def list_subjects():
#     batch_id = request.args.get("batch_id")
#     branch_id = request.args.get("branch_id")
#     year = request.args.get("year")

#     query = Subject.query

#     if batch_id:
#         query = query.filter_by(batch_id=int(batch_id))

#     if branch_id:
#         query = query.filter_by(branch_id=int(branch_id))

#     if year:
#         query = query.filter_by(year=int(year))

#     subjects = query.order_by(Subject.name.asc()).all()

#     return (
#         jsonify(
#             [
#                 {
#                     "id": s.id,
#                     "name": s.name,
#                     "batch_id": s.batch_id,
#                     "branch_id": s.branch_id,
#                     "year": s.year,
#                 }
#                 for s in subjects
#             ]
#         ),
#         200,
#     )


@APP.route("/api/attendance/settings", methods=["POST"])
@auth_required
def set_attendance_settings():
    data = request.json or {}

    start_date = data.get("start_date")
    end_date = data.get("end_date")
    holidays = data.get("holidays", [])
    exclude_sundays = data.get("exclude_sundays", True)

    if not start_date or not end_date:
        return jsonify({"error": "start_date and end_date required"}), 400

    AttendanceSettings.query.delete()

    settings = AttendanceSettings(
        start_date=datetime.date.fromisoformat(start_date),
        end_date=datetime.date.fromisoformat(end_date),
        holidays=holidays,
        exclude_sundays=exclude_sundays,
    )

    DB.session.add(settings)
    DB.session.commit()

    return jsonify({"msg": "attendance settings saved"}), 200


@APP.route("/api/attendance/settings", methods=["GET"])
@auth_required
def get_attendance_settings():
    settings = AttendanceSettings.query.first()

    if not settings:
        return (
            jsonify(
                {
                    "start_date": None,
                    "end_date": None,
                    "holidays": [],
                    "exclude_sundays": True,
                }
            ),
            200,
        )

    return (
        jsonify(
            {
                "start_date": settings.start_date.isoformat(),
                "end_date": settings.end_date.isoformat(),
                "holidays": settings.holidays or [],
                "exclude_sundays": settings.exclude_sundays,
            }
        ),
        200,
    )


@APP.route("/api/attendance/by-date", methods=["GET"])
@auth_required
def attendance_by_date():
    date_str = request.args.get("date")
    batch = request.args.get("batch")
    dept = request.args.get("dept")
    year = request.args.get("year")
    section = request.args.get("section")

    if not date_str:
        return jsonify({}), 200

    attendance_date = datetime.date.fromisoformat(date_str)

    start = datetime.datetime.combine(attendance_date, datetime.time.min)
    end = datetime.datetime.combine(attendance_date, datetime.time.max)

    # 🔥 JOIN Attendance → Student
    query = (
        DB.session.query(Attendance)
        .join(Student, Attendance.student_id == Student.id)
        .filter(
            Attendance.timestamp >= start,
            Attendance.timestamp <= end,
        )
    )

    # 🔥 APPLY FILTERS
    if batch:
        query = query.filter(Student.batch_id == int(batch))
    if dept:
        query = query.filter(Student.department == dept)
    if year:
        query = query.filter(Student.year == str(year))
    if section:
        query = query.filter(Student.section == section)

    records = query.all()

    result = {}

    for r in records:
        sid = r.student_id

        if sid not in result:
            result[sid] = {}

        # 🔹 recognition → mark all periods present
        if r.method == "recognition" and r.period:
            result[sid][r.period] = {
                "status": r.extra.get("status", "present"),
                "method": "recognition",
            }

        # 🔹 manual attendance
        if r.method == "manual" and r.period:
            result[sid][r.period] = {
                "status": r.extra.get("status"),
                "method": "manual",
            }

    return jsonify(result), 200


from sqlalchemy import func


@APP.route("/api/attendance/manual", methods=["POST"])
@auth_required
def manual_attendance():
    data = request.json or {}

    roll_no = data.get("roll_no")
    status = data.get("status", "present")
    date_str = data.get("date")
    period = data.get("period")
    subject_id = data.get("subject_id")
    source = data.get("source", "manual-ui")

    # -------- VALIDATION --------
    if not roll_no or not date_str or period is None or subject_id is None:
        return jsonify({"error": "roll_no, date, period, subject_id required"}), 400

    try:
        period = int(period)
        subject_id = int(subject_id)
    except ValueError:
        return jsonify({"error": "period and subject_id must be numbers"}), 400

    if period < 1 or period > 7:
        return jsonify({"error": "period must be 1 to 7"}), 400

    student = Student.query.filter_by(roll_no=roll_no).first()
    if not student:
        return jsonify({"error": "student not found"}), 404

    try:
        attendance_date = datetime.date.fromisoformat(date_str)
    except ValueError:
        return jsonify({"error": "invalid date format"}), 400

    ts = datetime.datetime.combine(attendance_date, datetime.datetime.utcnow().time())

    # -------- CHECK EXISTING --------
    existing = Attendance.query.filter(
        Attendance.student_id == student.id,
        func.date(Attendance.timestamp) == attendance_date,
        Attendance.method == "manual",
        Attendance.period == period,
        Attendance.subject_id == subject_id,
    ).first()

    if existing:
        existing.extra = {"status": status}
        DB.session.commit()
        return jsonify({"msg": "attendance updated", "method": "manual"}), 200

    # -------- CREATE --------
    att = Attendance(
        student_id=student.id,
        timestamp=ts,
        method="manual",
        source=source,
        period=period,
        subject_id=subject_id,
        extra={"status": status},
    )

    DB.session.add(att)
    DB.session.commit()

    return jsonify({"msg": "attendance created", "method": "manual"}), 201


@APP.route("/api/attendance/summary/<int:student_id>", methods=["GET"])
@auth_required
def attendance_summary(student_id):
    # total attendance days (distinct dates)
    total_days = (
        DB.session.query(
            DB.func.count(DB.func.distinct(DB.func.date(Attendance.timestamp)))
        )
        .filter(
            Attendance.student_id == student_id,
            Attendance.method.in_(["manual", "recognition"]),
        )
        .scalar()
    )

    # present days
    present_days = (
        DB.session.query(
            DB.func.count(DB.func.distinct(DB.func.date(Attendance.timestamp)))
        )
        .filter(
            Attendance.student_id == student_id,
            Attendance.method.in_(["manual", "recognition"]),
            Attendance.extra != None,
        )
        .scalar()
    )

    percentage = round((present_days / total_days) * 100, 2) if total_days else 0

    return (
        jsonify(
            {
                "total_days": total_days,
                "present_days": present_days,
                "percentage": percentage,
            }
        ),
        200,
    )


@APP.route("/api/export/attendance", methods=["GET"])
@auth_required
def export_attendance():
    dept = request.args.get("dept")
    year = request.args.get("year")
    section = request.args.get("section")
    batch = request.args.get("batch")
    export_type = request.args.get("type", "pdf")

    settings = AttendanceSettings.query.first()
    if not settings:
        return jsonify({"error": "Attendance settings not configured"}), 400

    query = Student.query
    if dept:
        query = query.filter_by(department=dept)
    if year:
        query = query.filter_by(year=year)
    if section:
        query = query.filter_by(section=section)
    if batch:
        query = query.filter_by(batch_id=int(batch))
    students = query.all()

    rows = []

    def working_days():
        count = 0
        current = settings.start_date
        while current <= settings.end_date:
            if current.weekday() != 6 and str(current) not in settings.holidays:
                count += 1
            current += datetime.timedelta(days=1)
        return count

    total_days = working_days()

    for s in students:
        present_days = (
            DB.session.query(
                DB.func.count(DB.func.distinct(DB.func.date(Attendance.timestamp)))
            )
            .filter(
                Attendance.student_id == s.id,
                Attendance.method.in_(["manual", "recognition"]),
            )
            .scalar()
        )

        percentage = round((present_days / total_days) * 100, 2) if total_days else 0

        rows.append(
            {
                "Roll No": s.roll_no,
                "Name": s.name,
                "Department": s.department,
                "Year": s.year,
                "Section": s.section,
                "Total Days": total_days,
                "Present": present_days,
                "Percentage": percentage,
            }
        )

    df = pd.DataFrame(rows)

    if export_type == "pdf":
        buffer = io.BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=40,
            leftMargin=40,
            topMargin=60,
            bottomMargin=40,
        )

        styles = getSampleStyleSheet()
        elements = []

        title_style = ParagraphStyle(
            "TitleStyle",
            parent=styles["Title"],
            alignment=1,
            spaceAfter=10,
        )

        subtitle_style = ParagraphStyle(
            "SubTitleStyle",
            parent=styles["Normal"],
            alignment=1,
            spaceAfter=20,
        )

        cell_style = ParagraphStyle(
            "CellStyle",
            parent=styles["Normal"],
            fontSize=9,
            leading=11,
        )

        elements.append(Paragraph("<b>IDEAL INSTITUTE OF TECHNOLOGY</b>", title_style))
        elements.append(Paragraph("Attendance Report", subtitle_style))

        # ---------- Table ----------
        table_data = [
            [
                "Roll No",
                "Name",
                "Dept",
                "Year",
                "Section",
                "Total",
                "Present",
                "%",
            ]
        ]

        for _, row in df.iterrows():
            table_data.append(
                [
                    Paragraph(str(row["Roll No"]), cell_style),
                    Paragraph(str(row["Name"]), cell_style),  # 👈 TEXT WRAPS HERE
                    Paragraph(str(row["Department"]), cell_style),
                    Paragraph(str(row["Year"]), cell_style),
                    Paragraph(row["Section"] or "-", cell_style),
                    Paragraph(str(row["Total Days"]), cell_style),
                    Paragraph(str(row["Present"]), cell_style),
                    Paragraph(f'{row["Percentage"]}%', cell_style),
                ]
            )

        table = Table(
            table_data,
            repeatRows=1,
            colWidths=[70, 140, 45, 40, 45, 50, 50, 45],  # 👈 Proper widths
            hAlign="CENTER",
        )

        table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )

        elements.append(table)

        doc.build(
            elements,
            onFirstPage=draw_page_border,
            onLaterPages=draw_page_border,
        )

        buffer.seek(0)
        return send_file(
            buffer,
            as_attachment=True,
            download_name="attendance_report.pdf",
            mimetype="application/pdf",
        )

    if export_type == "excel":
        output = io.BytesIO()

        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Attendance")

            workbook = writer.book
            worksheet = writer.sheets["Attendance"]

            # ---- Styling ----
            header_format = workbook.add_format(
                {
                    "bold": True,
                    "border": 1,
                    "align": "center",
                    "valign": "middle",
                }
            )

            cell_format = workbook.add_format(
                {
                    "border": 1,
                    "align": "center",
                    "valign": "middle",
                }
            )

            # Apply header format
            for col_num, column_name in enumerate(df.columns):
                worksheet.write(0, col_num, column_name, header_format)
                worksheet.set_column(col_num, col_num, 18)

            # Apply cell borders
            for row in range(1, len(df) + 1):
                for col in range(len(df.columns)):
                    worksheet.write(row, col, df.iloc[row - 1, col], cell_format)

            # Freeze header row
            worksheet.freeze_panes(1, 0)

        output.seek(0)

        return send_file(
            output,
            as_attachment=True,
            download_name="attendance_report.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


# ---- Attendance marking (auto / recognition) ----
@APP.route("/api/attendance/mark", methods=["POST"])
def auto_attendance():
    """
    Face Recognition Attendance API

    Expected JSON:
    {
      "recognized_id": "21CSE001",
      "confidence": 0.93,
      "camera_id": "cam-01",
      "timestamp": "2026-01-27T10:30:00",
      "period": 3            # optional (recommended)
    }
    """

    data = request.json or {}

    recognized_id = data.get("recognized_id")
    confidence = data.get("confidence")
    camera_id = data.get("camera_id", "camera")
    timestamp = data.get("timestamp")
    period = data.get("period")  # optional

    if not recognized_id:
        return jsonify({"error": "recognized_id required"}), 400

    # ---------- FIND STUDENT ----------
    student = Student.query.filter_by(roll_no=recognized_id).first()
    if not student:
        return jsonify({"msg": "recognized id not mapped to student"}), 200

    # ---------- PARSE TIMESTAMP ----------
    ts = datetime.datetime.now()
    if timestamp:
        try:
            ts = datetime.datetime.fromisoformat(timestamp)
        except:
            ts = datetime.datetime.now()
    else:
        ts = datetime.datetime.now()

    start = ts.replace(hour=0, minute=0, second=0, microsecond=0)
    end = ts.replace(hour=23, minute=59, second=59, microsecond=999999)

    # ---------- CHECK MANUAL ATTENDANCE (DO NOT OVERRIDE) ----------
    manual_exists = Attendance.query.filter(
        Attendance.student_id == student.id,
        Attendance.timestamp >= start,
        Attendance.timestamp <= end,
        Attendance.method == "manual",
        Attendance.period == period if period else True,
    ).first()

    if manual_exists:
        return (
            jsonify({"msg": "manual attendance already exists, recognition skipped"}),
            200,
        )

    # ---------- CHECK EXISTING RECOGNITION ----------
    # ---------- CHECK IF RECOGNITION ALREADY DONE TODAY ----------
    existing = Attendance.query.filter(
        Attendance.student_id == student.id,
        Attendance.timestamp >= start,
        Attendance.timestamp <= end,
        Attendance.method == "recognition",
    ).count()

    if existing >= 7:
        return jsonify({"msg": "All periods already marked"}), 200

    # ---------- MARK ALL PERIODS PRESENT ----------
    for period_no in range(1, 8):
        manual_exists = Attendance.query.filter(
            Attendance.student_id == student.id,
            func.date(Attendance.timestamp) == ts.date(),
            Attendance.method == "manual",
            Attendance.period == period_no,
        ).first()

        if manual_exists:
            continue  # manual overrides recognition

        recognition_exists = Attendance.query.filter(
            Attendance.student_id == student.id,
            func.date(Attendance.timestamp) == ts.date(),
            Attendance.method == "recognition",
            Attendance.period == period_no,
        ).first()

        if recognition_exists:
            continue

        att = Attendance(
            student_id=student.id,
            timestamp=ts,
            method="recognition",
            period=period_no,
            source=camera_id,
            extra={"confidence": confidence, "status": "present"},
        )
        DB.session.add(att)
    DB.session.commit()
    return (
        jsonify(
            {
                "msg": "Recognition attendance marked for all periods",
                "student": {"roll_no": student.roll_no},
            }
        ),
        201,
    )


# ---- Fetch attendance records for a student ----
@APP.route("/api/attendance/<int:student_id>", methods=["GET"])
@auth_required
def get_attendance(student_id):
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 200))
    query = Attendance.query.filter_by(student_id=student_id).order_by(
        Attendance.timestamp.desc()
    )
    pag = query.paginate(page=page, per_page=per_page, error_out=False)
    items = [
        {
            "id": a.id,
            "timestamp": a.timestamp.isoformat(),
            "method": a.method,
            "source": a.source,
            "extra": a.extra,
        }
        for a in pag.items
    ]
    return (
        jsonify(
            {
                "attendance": items,
                "total": pag.total,
                "page": pag.page,
                "per_page": pag.per_page,
            }
        ),
        200,
    )


# ---- Utility endpoints (admin) ----
@APP.route("/api/init", methods=["POST"])
def init_db():
    """
    Initialize DB and create an initial admin user.
    Body: {"admin_username":"admin","admin_password":"pass123"}
    Use only once during deploy / local dev.
    """
    data = request.json or {}
    admin_username = data.get("admin_username", "admin")
    admin_password = data.get("admin_password", "admin123")

    DB.create_all()

    existing_admin = User.query.filter_by(username=admin_username).first()
    if existing_admin:
        return jsonify({"msg": "admin already exists"}), 200

    admin = User(username=admin_username, role="admin")
    admin.set_password(admin_password)
    DB.session.add(admin)
    DB.session.commit()
    return jsonify({"msg": "db init complete", "admin_username": admin_username}), 201


# ---------- Error handlers ----------
@APP.errorhandler(404)
def not_found(e):
    return jsonify({"error": "not found"}), 404


@APP.errorhandler(500)
def server_error(e):
    return jsonify({"error": "server error", "message": str(e)}), 500


# ---------- Run ----------
if __name__ == "__main__":
    with APP.app_context():
        DB.create_all()
    # For local dev only. In production use gunicorn/uwsgi.
    port = int(os.environ.get("PORT", 5000))
    APP.run(host="0.0.0.0", port=port, debug=True)
