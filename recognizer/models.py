# src/models.py
from sqlalchemy import Column, Integer, String, Date, DateTime, Time, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from src.db import Base

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    course_id = Column(Integer, ForeignKey("courses.id"))


class Course(Base):
    __tablename__ = "courses"
    code = Column(String, primary_key=True)   # e.g., CS201
    name = Column(String, nullable=False)

class Timetable(Base):
    __tablename__ = "timetable"
    id = Column(Integer, primary_key=True, autoincrement=True)
    classroom_id = Column(String, index=True)
    weekday = Column(Integer, index=True)     # 0=Mon ... 6=Sun
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    course_code = Column(String, ForeignKey("courses.code"))
    __table_args__ = (UniqueConstraint("classroom_id","weekday","start_time","end_time", name="uq_slot"),)

class AttendanceLog(Base):
    __tablename__ = "attendance_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String, ForeignKey("students.id"), index=True)
    classroom_id = Column(String, index=True)
    course_code = Column(String, index=True)  # Course resolved from timetable
    ts = Column(DateTime, index=True)         # exact detection time
    day = Column(Date, index=True)
