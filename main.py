import os
import random
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# --- DATABASE SETUP (SQLite) ---
DATABASE_URL = "sqlite:///./campus_copilot.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- SQLALCHEMY MODELS ---
class TimetableItem(Base):
    __tablename__ = "timetable"
    id = Column(Integer, primary_key=True, index=True)
    day = Column(String, index=True)  # Mon, Tue, Wed, Thu, Fri
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
    description = Column(String)
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

Base.metadata.create_all(bind=engine)

# --- PYDANTIC SCHEMAS ---
class TicketCreate(BaseModel):
    category: str
    location: str
    description: str

class TicketResponse(BaseModel):
    id: int
    ticket_id: str
    category: str
    location: str
    description: str
    status: str
    date: str

    class Config:
        from_attributes = True

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str

# --- FASTAPI APP SETUP ---
app = FastAPI(title="Campus Copilot API")

# Enable CORS for Frontend Communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# OpenAI Client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "your-key-here"))

# --- INITIAL SEED DATA ---
@app.on_event("startup")
def seed_database():
    db = SessionLocal()
    if db.query(TimetableItem).count() == 0:
        db.add_all([
            TimetableItem(day="Tue", time="09:00 - 10:30 AM", subject="Artificial Intelligence & NN", faculty="Prof. Alan Turing", room="Lab 304", type="Lecture"),
            TimetableItem(day="Tue", time="11:00 - 12:30 PM", subject="Database Management Systems", faculty="Dr. Sarah Jenkins", room="Room 201", type="Lecture"),
            TimetableItem(day="Tue", time="02:00 - 03:30 PM", subject="Software Engineering", faculty="Prof. Robert Martin", room="Hall B", type="Lecture"),
            TimetableItem(day="Mon", time="09:00 - 10:30 AM", subject="Computer Networks", faculty="Prof. Vint Cerf", room="Room 204", type="Lecture"),
        ])
    if db.query(Lab).count() == 0:
        db.add_all([
            Lab(name="AI & Machine Learning Research Lab", location="Tech Block 3rd Floor", capacity="40 Seats", status="Available", equipment="NVIDIA RTX 4090 Workstations"),
            Lab(name="Computer Lab 101", location="Academic Wing A", capacity="60 Seats", status="In Use (Class)", equipment="Intel i7 PCs, Cisco Switches")
        ])
    if db.query(Ticket).count() == 0:
        db.add_all([
            Ticket(ticket_id="REQ-1042", category="Wi-Fi & Network issue", location="Girls Hostel Block A", description="Slow Wi-Fi speed during evening hours.", status="Resolved", date="Sep 20, 2026"),
            Ticket(ticket_id="REQ-1045", category="Classroom issue", location="Room 304", description="HDMI Projector display flickers continuously.", status="In Progress", date="Sep 21, 2026")
        ])
    db.commit()
    db.close()

# --- API ROUTES ---

# 1. GET Timetable by Day
@app.get("/api/timetable/{day}")
def get_timetable(day: str, db: Session = Depends(get_db)):
    items = db.query(TimetableItem).filter(TimetableItem.day == day).all()
    return items

# 2. GET All Tickets
@app.get("/api/tickets", response_model=List[TicketResponse])
def get_tickets(db: Session = Depends(get_db)):
    return db.query(Ticket).order_by(Ticket.id.desc()).all()

# 3. POST Create Ticket
@app.post("/api/tickets", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
def create_ticket(payload: TicketCreate, db: Session = Depends(get_db)):
    req_id = f"REQ-{random.randint(1000, 9999)}"
    today_str = datetime.now().strftime("%b %d, %Y")
    
    new_ticket = Ticket(
        ticket_id=req_id,
        category=payload.category,
        location=payload.location,
        description=payload.description,
        status="Submitted",
        date=today_str
    )
    db.add(new_ticket)
    db.commit()
    db.refresh(new_ticket)
    return new_ticket

# 4. GET Labs
@app.get("/api/labs")
def get_labs(db: Session = Depends(get_db)):
    return db.query(Lab).all()

# 5. POST AI Chat Assistant Endpoint (RAG-Enabled)
@app.post("/api/chat", response_model=ChatResponse)
def ai_chat(payload: ChatRequest, db: Session = Depends(get_db)):
    user_query = payload.message.lower()

    # Pull Contextual Knowledge from Database for RAG
    labs = db.query(Lab).all()
    timetable = db.query(TimetableItem).all()
    
    context_str = f"""
    Campus Labs Data: {[{'name': l.name, 'location': l.location, 'status': l.status} for l in labs]}
    Campus Timetable Data: {[{'day': t.day, 'time': t.time, 'subject': t.subject, 'room': t.room} for t.time in timetable]}
    """

    system_prompt = f"""
    You are Campus Copilot AI, an intelligent, helpful campus assistant.
    Use the following real-time database context to answer the student's question accurately:
    {context_str}
    Keep responses friendly, helpful, and concise. Format using basic HTML tags if needed.
    """

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": payload.message}
            ]
        )
        reply_text = response.choices[0].message.content
    except Exception as e:
        reply_text = "I am having trouble connecting to my AI brain. Please make sure your OpenAI API key is set correctly."

    return ChatResponse(reply=reply_text)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)