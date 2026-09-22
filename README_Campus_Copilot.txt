Campus Copilot — Integrated Frontend + Backend

FILES
- index.html — frontend
- main.py / Campus_Copilot_Backend.py — FastAPI backend
- requirements.txt — dependencies
- .env.example — optional OpenAI settings

RUN
1. Put index.html and main.py in the same folder.
2. Run: pip install -r requirements.txt
3. Optional: copy .env.example to .env and add OPENAI_API_KEY.
4. Run: python main.py
5. Open: http://127.0.0.1:8000

The backend serves the frontend directly. No separate frontend server is required.

CONNECTED FLOWS
- Labs: GET /api/labs
- Lab booking: POST /api/labs/book
- Timetable: GET /api/timetable/{day}
- Service requests: GET /api/tickets and POST /api/tickets
- AI assistant: POST /api/chat
- Library books: GET /api/books
- Bookings: GET /api/bookings
- Health: GET /api/health

DATABASE
A local SQLite database named campus_copilot.db is created automatically.

AI
OPENAI_API_KEY is optional. Without it, /api/chat uses a database-aware fallback instead of failing.
