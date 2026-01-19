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
from functools import wraps

from flask import Flask, request, jsonify, g
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from passlib.hash import pbkdf2_sha256
from datetime import date

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
    resources={r"/api/*": {"origins": "http://localhost:5173"}},
    supports_credentials=True,
    allow_headers=["Authorization", "Content-Type"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
)
from flask import make_response


@APP.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = make_response()
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
        response.headers["Access-Control-Allow-Methods"] = (
            "GET, POST, PUT, DELETE, OPTIONS"
        )
        return response, 200


# allow all origins for now (development)

# ---------- Base directory ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------- Config ----------
APP.config["SQLALCHEMY_DATABASE_URI"] = (
    f"sqlite:///{os.path.join(BASE_DIR, 'attendance.db')}"
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

    def set_password(self, password):
        self.password_hash = pbkdf2_sha256.hash(password)

    def verify_password(self, password):
        return pbkdf2_sha256.verify(password, self.password_hash)


class Student(DB.Model):
    __tablename__ = "students"
    id = DB.Column(DB.Integer, primary_key=True)
    roll_no = DB.Column(DB.String(64), unique=True, nullable=False)
    name = DB.Column(DB.String(200), nullable=False)
    department = DB.Column(DB.String(128))
    year = DB.Column(DB.String(32))
    section = DB.Column(DB.String(32))
    photo_url = DB.Column(DB.String(1024))


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
    method = DB.Column(DB.String(50), default="manual")  # manual / auto / recognition
    source = DB.Column(DB.String(255), nullable=True)  # e.g., camera_id or script name
    extra = DB.Column(DB.JSON, nullable=True)  # details like frame_id, confidence


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


def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):

        # ✅ Allow CORS preflight requests
        if request.method == "OPTIONS":
            return jsonify({}), 200

        auth = request.headers.get("Authorization")
        if not auth:
            return jsonify({"error": "Authorization header missing"}), 401

        parts = auth.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return jsonify({"error": "Invalid Authorization header format"}), 401

        token = parts[1]
        payload = decode_token(token)
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401

        g.current_user = User.query.get(payload["user_id"])
        if not g.current_user:
            return jsonify({"error": "User not found"}), 401

        return f(*args, **kwargs)

    return decorated


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
            Attendance.method == "manual",
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

        image1 = request.files.get("image1")
        image2 = request.files.get("image2")

        if not roll_no or not name:
            return jsonify({"error": "roll_no and name required"}), 400

        if not image1 or not image2:
            return jsonify({"error": "Two images are required"}), 400

        # Check duplicate
        if Student.query.filter_by(roll_no=roll_no).first():
            return jsonify({"error": "Student already exists"}), 409

        # Create dataset directory
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
        )

        DB.session.add(student)
        DB.session.commit()

        return (
            jsonify({"msg": "Student registered successfully", "roll_no": roll_no}),
            201,
        )

    except Exception as e:
        print("REGISTER ERROR:", e)
        return jsonify({"error": str(e)}), 500


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
    # support ?q=search (search roll_no or name) and pagination ?page & ?per_page
    q = request.args.get("q", "").strip()
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 100))
    query = Student.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            DB.or_(
                Student.name.ilike(like),
                Student.roll_no.ilike(like),
                Student.department.ilike(like),
            )
        )
    pag = query.order_by(Student.roll_no.asc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    items = [
        {
            "id": s.id,
            "roll_no": s.roll_no,
            "name": s.name,
            "department": s.department,
            "year": s.year,
            "section": s.section,  # ✅ ADD THIS LINE
            "photo_url": s.photo_url,
        }
        for s in pag.items
    ]
    return (
        jsonify(
            {
                "students": items,
                "total": pag.total,
                "page": pag.page,
                "per_page": pag.per_page,
            }
        ),
        200,
    )


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


# ---- Attendance marking (manual) ----
@APP.route("/api/attendance/manual", methods=["POST"])
@auth_required
def manual_attendance():
    data = request.json or {}
    roll_no = data.get("roll_no")
    status = data.get("status", "present")  # present / absent
    timestamp = data.get("timestamp")
    source = data.get("source", "manual-ui")

    if not roll_no:
        return jsonify({"error": "roll_no required"}), 400

    student = Student.query.filter_by(roll_no=roll_no).first()
    if not student:
        return jsonify({"error": "student not found"}), 404

    # Parse timestamp
    ts = datetime.datetime.utcnow()
    if timestamp:
        try:
            ts = datetime.datetime.fromisoformat(timestamp)
        except Exception:
            return jsonify({"error": "invalid timestamp format"}), 400

    # Same-day range
    start = ts.replace(hour=0, minute=0, second=0, microsecond=0)
    end = ts.replace(hour=23, minute=59, second=59, microsecond=999999)

    existing = Attendance.query.filter(
        Attendance.student_id == student.id,
        Attendance.timestamp >= start,
        Attendance.timestamp <= end,
        Attendance.method == "manual",
    ).first()

    # UPDATE if exists
    if existing:
        existing.extra = {"status": status}
        DB.session.commit()
        return jsonify({"msg": "attendance updated"}), 200

    # CREATE if not exists
    att = Attendance(
        student_id=student.id,
        timestamp=ts,
        method="manual",
        source=source,
        extra={"status": status},
    )

    DB.session.add(att)
    DB.session.commit()

    return jsonify({"msg": "attendance created"}), 201


@APP.route("/api/attendance/by-date", methods=["GET"])
@auth_required
def attendance_by_date():
    date_str = request.args.get("date")
    if not date_str:
        return jsonify({"error": "date required"}), 400

    try:
        selected_date = datetime.date.fromisoformat(date_str)
    except Exception:
        return jsonify({"error": "invalid date format"}), 400

    start = datetime.datetime.combine(selected_date, datetime.time.min)
    end = datetime.datetime.combine(selected_date, datetime.time.max)

    records = Attendance.query.filter(
        Attendance.timestamp >= start,
        Attendance.timestamp <= end,
    ).all()

    result = {}

    for r in records:
        result[r.student_id] = {
            "status": r.extra.get("status", "present") if r.extra else "present",
            "method": r.method or "manual",
        }

    return jsonify(result), 200


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
    Public endpoint intended for trusted internal network / script usage.
    Expected JSON:
    {
      "recognized_id": "CS123",   # or a face-id that maps to student.roll_no
      "confidence": 0.93,
      "camera_id": "cam-01",
      "timestamp": "2025-12-08T10:30:00Z",
      "meta": {...}
    }
    Notes: this endpoint is intentionally left public for edge devices to call.
    Protect using network rules or API-key in production.
    """
    data = request.json or {}
    recognized_id = data.get("recognized_id")
    confidence = data.get("confidence")
    camera_id = data.get("camera_id", "camera")
    timestamp = data.get("timestamp")
    meta = data.get("meta", {})

    if not recognized_id:
        return jsonify({"error": "recognized_id required"}), 400

    # Attempt to find student by roll_no
    student = Student.query.filter_by(roll_no=recognized_id).first()
    student_id = student.id if student else None

    # record recognition log
    rec = RecognitionLog(
        recognized_id=recognized_id,
        student_id=student_id,
        confidence=confidence,
        meta=meta,
    )
    DB.session.add(rec)
    DB.session.flush()  # get rec.id without commit

    # choose timestamp
    ts = datetime.datetime.utcnow()
    if timestamp:
        try:
            ts = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except Exception:
            pass

    # if a matching student exists, create attendance record
    att_id = None
    if student:
        att = Attendance(
            student_id=student.id,
            timestamp=ts,
            method="recognition",
            source=camera_id,
            extra={"confidence": confidence},
        )
        DB.session.add(att)
        DB.session.commit()
        att_id = att.id
        return (
            jsonify(
                {
                    "msg": "attendance marked",
                    "attendance_id": att_id,
                    "student": {"id": student.id, "roll_no": student.roll_no},
                }
            ),
            201,
        )

    DB.session.commit()
    # not mapped to a student
    return (
        jsonify(
            {
                "msg": "recognized id logged but no student mapped",
                "recognition_id": rec.id,
            }
        ),
        200,
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
    # For local dev only. In production use gunicorn/uwsgi.
    port = int(os.environ.get("PORT", 5000))
    APP.run(host="0.0.0.0", port=port, debug=True)
