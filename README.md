# FastAPI service

Run:
- cd /c/Users/Andhias/services/api
- python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

Health:
- http://127.0.0.1:8000/api/v1/health

Current endpoints:
- GET /api/v1/health
- POST /api/v1/auth/login
- GET /api/v1/search
- POST /api/v1/chat/sessions
- GET /api/v1/chat/sessions/{session_id}
- POST /api/v1/chat/sessions/{session_id}/messages
- GET /api/v1/avatars/config
- POST /api/v1/voice/tts

Persistence:
- chat sessions and chat messages now persist via database tables
- API creates tables at startup from SQLAlchemy models
- current session user defaults to demo-user

Notes:
- CORS enabled for development
- current responses are stub/demo payloads for UI integration
