"""
Campus Copilot - integrated FastAPI backend.

Place this file beside index.html and run:
    python main.py

Then open:
    http://127.0.0.1:8000
"""

import os
import random
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        return None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = "sqlite:///./campus_copilot.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class TimetableItem(Base):
    __tablename__ = "timetable"
    id = Column(Integer, primary_key=True, index=True)
    day = Column(String, index=True)
    time = Column(String)
    subject = Column(String)
    faculty = Column(String)
    room = Column(String)
    type = Column(String)


class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(String, unique=True, index=True)
    category = Column(String)
    location = Column(String)
    description = Column(Text)
    status = Column(String, default="Submitted")
    date = Column(String)


class Lab(Base):
    __tablename__ = "labs"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    location = Column(String)
    capacity = Column(String)
    status = Column(String)
    equipment = Column(String)


class Book(Base):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    author = Column(String)
    status = Column(String)
    tag = Column(String)


class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, index=True)
    lab_id = Column(Integer, index=True)
    requester = Column(String, default="student")
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)


class TicketCreate(BaseModel):
    category: str
    location: str
    description: str


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: str
    category: str
    location: str
    description: str
    status: str
    date: str


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


class BookingRequest(BaseModel):
    lab_id: int
    requester: str = "student"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    seed_database()
    yield

app = FastAPI(title="Campus Copilot API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
openai_client = OpenAI(api_key=OPENAI_API_KEY) if (OpenAI and OPENAI_API_KEY) else None


def seed_database():
    db = SessionLocal()
    try:
        if db.query(TimetableItem).count() == 0:
            db.add_all([
                TimetableItem(day="Tue", time="09:00 - 10:30 AM", subject="Artificial Intelligence & NN", faculty="Prof. Alan Turing", room="Lab 304", type="Lecture"),
                TimetableItem(day="Tue", time="11:00 - 12:30 PM", subject="Database Management Systems", faculty="Dr. Sarah Jenkins", room="Room 201", type="Lecture"),
                TimetableItem(day="Tue", time="02:00 - 03:30 PM", subject="Software Engineering", faculty="Prof. Robert Martin", room="Hall B", type="Lecture"),
                TimetableItem(day="Mon", time="09:00 - 10:30 AM", subject="Computer Networks", faculty="Prof. Vint Cerf", room="Room 204", type="Lecture"),
                TimetableItem(day="Mon", time="11:00 - 12:30 PM", subject="Database Systems Lab", faculty="Dr. Sarah Jenkins", room="Lab 101", type="Practical"),
                TimetableItem(day="Wed", time="10:00 - 11:30 AM", subject="AI & Neural Nets Lab", faculty="Prof. Alan Turing", room="AI Lab 304", type="Practical"),
                TimetableItem(day="Wed", time="01:30 - 03:00 PM", subject="Computer Networks", faculty="Prof. Vint Cerf", room="Room 204", type="Lecture"),
                TimetableItem(day="Thu", time="09:00 - 10:30 AM", subject="Software Engineering", faculty="Prof. Robert Martin", room="Hall B", type="Lecture"),
                TimetableItem(day="Thu", time="11:00 - 12:30 PM", subject="Elective: Cloud Computing", faculty="Dr. Werner Vogels", room="Room 302", type="Lecture"),
                TimetableItem(day="Fri", time="10:00 - 12:00 PM", subject="Open Innovation Workshop", faculty="Guest Industry Speaker", room="Auditorium", type="Seminar"),
            ])

        if db.query(Lab).count() == 0:
            db.add_all([
                Lab(name="AI & Machine Learning Research Lab", location="Tech Block 3rd Floor", capacity="40 Seats", status="Available", equipment="NVIDIA RTX 4090 Workstations"),
                Lab(name="Computer Lab 101", location="Academic Wing A", capacity="60 Seats", status="In Use (Class)", equipment="Intel i7 PCs, Cisco Switches"),
                Lab(name="Cyber Security Lab", location="Innovation Block 2nd Floor", capacity="36 Seats", status="Available", equipment="SIEM Workstations, Network Firewalls"),
            ])

        if db.query(Ticket).count() == 0:
            db.add_all([
                Ticket(ticket_id="REQ-1042", category="Wi-Fi & Network issue", location="Girls Hostel Block A", description="Slow Wi-Fi speed during evening hours.", status="Resolved", date="Sep 20, 2026"),
                Ticket(ticket_id="REQ-1045", category="Classroom issue", location="Room 304", description="HDMI Projector display flickers continuously.", status="In Progress", date="Sep 21, 2026"),
                Ticket(ticket_id="REQ-1048", category="Electrical issue", location="Lab 101", description="AC unit in back row making noise.", status="Submitted", date="Sep 22, 2026"),
            ])

        if db.query(Book).count() == 0:
            db.add_all([
                Book(title="Clean Code", author="Robert C. Martin", status="Available", tag="CS-603"),
                Book(title="Computer Networking: A Top-Down Approach", author="Kurose & Ross", status="Borrowed (Due Sep 28)", tag="CS-604"),
                Book(title="Introduction to Algorithms (CLRS)", author="Cormen, Leiserson, Rivest", status="Available", tag="Reference"),
                Book(title="Operating System Concepts", author="Abraham Silberschatz", status="Available", tag="CS-502"),
            ])

        db.commit()
    finally:
        db.close()


@app.get("/", include_in_schema=False)
def serve_frontend():
    candidates = [
        BASE_DIR / "index.html",
        BASE_DIR / "Campus_Copilot_Integrated.html",
    ]
    frontend = next((path for path in candidates if path.exists()), None)
    if frontend is None:
        raise HTTPException(
            status_code=404,
            detail="No frontend HTML file found beside the backend.",
        )
    return FileResponse(frontend)


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "Campus Copilot API",
        "openai_enabled": bool(openai_client),
        "frontend_available": (BASE_DIR / "index.html").exists(),
    }


@app.get("/api/timetable/{day}")
def get_timetable(day: str, db: Session = Depends(get_db)):
    normalized_day = day.strip().title()[:3]
    return (
        db.query(TimetableItem)
        .filter(TimetableItem.day == normalized_day)
        .order_by(TimetableItem.id.asc())
        .all()
    )


@app.get("/api/tickets", response_model=List[TicketResponse])
def get_tickets(db: Session = Depends(get_db)):
    return db.query(Ticket).order_by(Ticket.id.desc()).all()


@app.post("/api/tickets", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
def create_ticket(payload: TicketCreate, db: Session = Depends(get_db)):
    category = payload.category.strip()
    location = payload.location.strip()
    description = payload.description.strip()

    if not category or not location or not description:
        raise HTTPException(status_code=400, detail="Category, location and description are required.")

    for _ in range(20):
        ticket_id = f"REQ-{random.randint(1000, 9999)}"
        if not db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first():
            break
    else:
        raise HTTPException(status_code=500, detail="Could not allocate a ticket ID.")

    new_ticket = Ticket(
        ticket_id=ticket_id,
        category=category,
        location=location,
        description=description,
        status="Submitted",
        date=datetime.now().strftime("%b %d, %Y"),
    )
    db.add(new_ticket)
    db.commit()
    db.refresh(new_ticket)
    return new_ticket


@app.get("/api/labs")
def get_labs(db: Session = Depends(get_db)):
    return db.query(Lab).order_by(Lab.id.asc()).all()


@app.post("/api/labs/book", status_code=status.HTTP_201_CREATED)
def book_lab(payload: BookingRequest, db: Session = Depends(get_db)):
    lab = db.query(Lab).filter(Lab.id == payload.lab_id).first()
    if not lab:
        raise HTTPException(status_code=404, detail="Selected lab was not found.")

    requester = payload.requester.strip().lower()
    if not requester:
        raise HTTPException(status_code=400, detail="Requester is required.")

    booking = Booking(
        lab_id=lab.id,
        requester=requester,
        status="pending",
        created_at=datetime.now(timezone.utc),
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    return {
        "message": "Booking created successfully.",
        "booking_id": booking.id,
        "lab_id": booking.lab_id,
        "status": booking.status,
        "created_at": booking.created_at.isoformat(),
    }


@app.get("/api/bookings")
def get_bookings(db: Session = Depends(get_db)):
    rows = db.query(Booking).order_by(Booking.id.desc()).all()
    return [
        {
            "id": row.id,
            "lab_id": row.lab_id,
            "requester": row.requester,
            "status": row.status,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


@app.get("/api/books")
def get_books(db: Session = Depends(get_db)):
    return db.query(Book).order_by(Book.id.asc()).all()


def local_chat_reply(message: str, db: Session) -> str:
    query = message.lower().strip()

    if "lab" in query and ("where" in query or "location" in query):
        labs = db.query(Lab).all()
        return "Campus labs: " + "; ".join(
            f"{lab.name} — {lab.location}" for lab in labs
        ) + "."

    if any(word in query for word in ("next class", "schedule", "timetable")):
        items = (
            db.query(TimetableItem)
            .filter(TimetableItem.day == "Tue")
            .order_by(TimetableItem.id.asc())
            .all()
        )
        if items:
            first = items[0]
            return f"Today's first scheduled class is {first.subject} at {first.time} in {first.room}."
        return "No timetable entries are currently available."

    if any(word in query for word in ("ticket", "issue", "complaint")):
        count = db.query(Ticket).filter(Ticket.status != "Resolved").count()
        return f"There are currently {count} active service requests in the system."

    return (
        "I can help with campus labs, timetable, service requests, and facilities. "
        "For live AI answers, add OPENAI_API_KEY to the .env file."
    )


@app.post("/api/chat", response_model=ChatResponse)
def ai_chat(payload: ChatRequest, db: Session = Depends(get_db)):
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    labs = db.query(Lab).all()
    timetable = db.query(TimetableItem).all()

    context_str = (
        f"Campus Labs Data: "
        f"{[{'name': l.name, 'location': l.location, 'status': l.status} for l in labs]}\n"
        f"Campus Timetable Data: "
        f"{[{'day': t.day, 'time': t.time, 'subject': t.subject, 'room': t.room} for t in timetable]}"
    )

    if openai_client:
        system_prompt = (
            "You are Campus Copilot AI, an intelligent and helpful campus assistant. "
            "Use only the supplied campus database context for campus facts. "
            "Do not invent campus data. Keep responses concise and friendly. "
            "Basic HTML tags are allowed.\n\n"
            + context_str
        )
        try:
            response = openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message},
                ],
            )
            text = response.choices[0].message.content or ""
            if text.strip():
                return ChatResponse(reply=text.strip())
        except Exception:
            pass

    return ChatResponse(reply=local_chat_reply(message, db))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)