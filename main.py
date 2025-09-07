from fastapi import FastAPI, HTTPException, Query, Depends
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

app = FastAPI()


from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For prototype; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB Setup
ENGINE = create_engine("sqlite:///campus.db", echo=True)
Session = sessionmaker(bind=ENGINE)
Base = declarative_base()

class College(Base):
    __tablename__ = "colleges"
    id = Column(Integer, primary_key=True)
    name = Column(String)

class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String, unique=True)
    college_id = Column(Integer, ForeignKey("colleges.id"))

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    type = Column(String)  # e.g., 'Workshop', 'Fest'
    date = Column(DateTime)
    college_id = Column(Integer, ForeignKey("colleges.id"))
    cancelled = Column(Boolean, default=False)

class Registration(Base):
    __tablename__ = "registrations"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    event_id = Column(Integer, ForeignKey("events.id"))
    registered_at = Column(DateTime, default=datetime.utcnow)
    attended = Column(Boolean, default=False)
    attended_at = Column(DateTime, nullable=True)
    feedback_rating = Column(Integer, nullable=True)  # 1-5

    __table_args__ = (UniqueConstraint('student_id', 'event_id'),)

Base.metadata.create_all(ENGINE)

# Pydantic Models
class EventCreate(BaseModel):
    name: str
    type: str
    date: datetime
    college_id: int

class EventResponse(BaseModel):
    id: int
    name: str
    type: str
    date: datetime
    college_id: int
    cancelled: bool

class RegistrationCreate(BaseModel):
    student_id: int
    event_id: int

class RegistrationResponse(BaseModel):
    id: int
    student_id: int
    event_id: int
    registered_at: datetime
    attended: bool
    attended_at: Optional[datetime]
    feedback_rating: Optional[int]

class AttendanceUpdate(BaseModel):
    attended: bool

class FeedbackUpdate(BaseModel):
    rating: int  # 1-5

class CancelEvent(BaseModel):
    cancelled: bool

# Simple Admin Dependency (for prototype - in real app, use JWT/OAuth)
def get_current_admin():
    # Simulate admin auth - in production, validate token/header
    return {"role": "admin"}

# Admin Endpoints (Protected in real app)
@app.post("/events", response_model=EventResponse)
def create_event(event: EventCreate, current_admin: dict = Depends(get_current_admin)):
    with Session() as session:
        db_event = Event(**event.dict())
        session.add(db_event)
        session.commit()
        session.refresh(db_event)
        return db_event

@app.get("/events", response_model=List[EventResponse])
def list_events(college_id: Optional[int] = Query(None), current_admin: dict = Depends(get_current_admin)):
    with Session() as session:
        query = session.query(Event)
        if college_id:
            query = query.filter(Event.college_id == college_id)
        events = query.all()
        return events

@app.patch("/events/{event_id}", response_model=EventResponse)
def update_event_cancelled(event_id: int, update: CancelEvent, current_admin: dict = Depends(get_current_admin)):
    with Session() as session:
        db_event = session.query(Event).filter(Event.id == event_id).first()
        if not db_event:
            raise HTTPException(404, "Event not found")
        db_event.cancelled = update.cancelled
        session.commit()
        session.refresh(db_event)
        return db_event

# Student/Other Endpoints (No auth for prototype)
@app.post("/registrations", response_model=RegistrationResponse)
def register_student(reg: RegistrationCreate):
    with Session() as session:
        db_reg = Registration(**reg.dict())
        session.add(db_reg)
        try:
            session.commit()
            session.refresh(db_reg)
            return db_reg
        except IntegrityError:
            raise HTTPException(409, "Duplicate registration")

@app.patch("/registrations/{reg_id}", response_model=RegistrationResponse)
def mark_attendance(reg_id: int, update: AttendanceUpdate):
    with Session() as session:
        db_reg = session.query(Registration).filter(Registration.id == reg_id).first()
        if not db_reg:
            raise HTTPException(404, "Registration not found")
        db_reg.attended = update.attended
        if update.attended:
            db_reg.attended_at = datetime.utcnow()
        session.commit()
        session.refresh(db_reg)
        return db_reg

@app.patch("/registrations/{reg_id}/feedback", response_model=RegistrationResponse)
def collect_feedback(reg_id: int, update: FeedbackUpdate):
    if not 1 <= update.rating <= 5:
        raise HTTPException(400, "Rating must be 1-5")
    with Session() as session:
        db_reg = session.query(Registration).filter(Registration.id == reg_id).first()
        if not db_reg:
            raise HTTPException(404, "Registration not found")
        if not db_reg.attended:
            raise HTTPException(400, "Cannot feedback without attendance")
        db_reg.feedback_rating = update.rating
        session.commit()
        session.refresh(db_reg)
        return db_reg

# Reports (Accessible to admins/students as per needs)
@app.get("/reports/event/{event_id}")
def event_report(event_id: int):
    with Session() as session:
        total_regs = session.query(func.count(Registration.id)).filter(Registration.event_id == event_id).scalar()
        attended = session.query(func.count(Registration.id)).filter(Registration.event_id == event_id, Registration.attended == True).scalar()
        avg_feedback = session.query(func.avg(Registration.feedback_rating)).filter(Registration.event_id == event_id, Registration.feedback_rating != None).scalar() or 0
        attendance_pct = (attended / total_regs * 100) if total_regs > 0 else 0
        return {
            "total_registrations": total_regs,
            "attendance_percentage": attendance_pct,
            "average_feedback": avg_feedback
        }

@app.get("/reports/event-popularity")
def event_popularity(type: Optional[str] = Query(None), college_id: Optional[int] = Query(None)):
    with Session() as session:
        query = session.query(Event.id, Event.name, func.count(Registration.id).label("regs")) \
            .outerjoin(Registration, Registration.event_id == Event.id) \
            .filter(Event.cancelled == False)
        if type:
            query = query.filter(Event.type == type)
        if college_id:
            query = query.filter(Event.college_id == college_id)
        results = query.group_by(Event.id).order_by(func.count(Registration.id).desc()).all()
        return [{"event_id": r[0], "name": r[1], "registrations": r[2]} for r in results]

@app.get("/reports/student-participation/{student_id}")
def student_participation(student_id: int):
    with Session() as session:
        attended_events = session.query(func.count(Registration.event_id)).filter(Registration.student_id == student_id, Registration.attended == True).scalar()
        return {"attended_events": attended_events}

# Bonus
@app.get("/reports/top-active-students")
def top_active_students(college_id: Optional[int] = Query(None)):
    with Session() as session:
        query = session.query(Student.id, Student.name, func.count(Registration.id).label("attendances")) \
            .join(Registration, Registration.student_id == Student.id) \
            .filter(Registration.attended == True)
        if college_id:
            query = query.filter(Student.college_id == college_id)
        results = query.group_by(Student.id).order_by(func.count(Registration.id).desc()).limit(3).all()
        return [{"student_id": r[0], "name": r[1], "attendances": r[2]} for r in results]

@app.get("/reports/events")
def flexible_events(type: Optional[str] = Query(None), college_id: Optional[int] = Query(None)):
    with Session() as session:
        query = session.query(Event.id, Event.name, func.count(Registration.id).label("regs")) \
            .outerjoin(Registration, Registration.event_id == Event.id) \
            .filter(Event.cancelled == False)
        if type:
            query = query.filter(Event.type == type)
        if college_id:
            query = query.filter(Event.college_id == college_id)
        results = query.group_by(Event.id).all()
        return [{"event_id": r[0], "name": r[1], "registrations": r[2]} for r in results]

# For testing, add some seed data endpoint (optional)
@app.post("/seed")
def seed_data():
    with Session() as session:
        # Add sample data
        college = College(name="Sample College")
        session.add(college)
        session.commit()
        session.refresh(college)
        student1 = Student(name="Alice", email="alice@example.com", college_id=college.id)
        student2 = Student(name="Bob", email="bob@example.com", college_id=college.id)
        session.add_all([student1, student2])
        session.commit()
        session.refresh(student1)
        session.refresh(student2)
        event1 = Event(name="Hackathon", type="Workshop", date=datetime(2025, 9, 7), college_id=college.id)
        event2 = Event(name="Tech Fest", type="Fest", date=datetime(2025, 9, 8), college_id=college.id)
        session.add_all([event1, event2])
        session.commit()
        session.refresh(event1)
        session.refresh(event2)
        reg1 = Registration(student_id=student1.id, event_id=event1.id, attended=True)
        reg2 = Registration(student_id=student2.id, event_id=event1.id, attended=True)
        reg3 = Registration(student_id=student1.id, event_id=event2.id, attended=True)
        session.add_all([reg1, reg2, reg3])
        session.commit()
        return {"message": "Seeded"}

# Debug endpoints (optional, for testing)
@app.get("/debug/events")
def list_events_debug():
    with Session() as session:
        return [{"id": e.id, "name": e.name, "type": e.type, "college_id": e.college_id, "cancelled": e.cancelled} for e in session.query(Event).all()]

@app.get("/debug/students")
def list_students_debug():
    with Session() as session:
        return [{"id": s.id, "name": s.name, "email": s.email, "college_id": s.college_id} for s in session.query(Student).all()]

@app.get("/debug/registrations")
def list_regs_debug():
    with Session() as session:
        return [{"id": r.id, "student_id": r.student_id, "event_id": r.event_id, "attended": r.attended, "feedback_rating": r.feedback_rating} for r in session.query(Registration).all()]