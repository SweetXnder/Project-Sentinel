import os
import json
import glob
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from google.genai import types

# ---------------------------------------------------------------------------
# SETUP
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env", override=True)

gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

app = FastAPI(
    title="CodingCuties · Sustainability Consultant API",
    description="Stateful AI chat grounded in the latest satellite assessment report.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# IN-MEMORY SESSION STORE
# { session_id: google.genai Chat object }
# ---------------------------------------------------------------------------

_sessions: dict[str, object] = {}

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _get_latest_report() -> dict:
    """Return the most-recently created Analytic_Report_*.json as a dict."""
    files = glob.glob(str(BASE_DIR / "Analytic_Report_*.json"))
    if not files:
        raise HTTPException(
            status_code=404,
            detail="No assessment report found. Run /analyze first to generate one.",
        )
    latest = max(files, key=os.path.getctime)
    with open(latest, "r", encoding="utf-8") as f:
        return {"filename": os.path.basename(latest), "data": json.load(f)}


def _build_system_instruction(report: dict) -> str:
    return f"""
You are the 'CodingCuties Sustainability Consultant'.
You are an expert in Southeast Asian Urban Planning and Sponge City frameworks.

KNOWLEDGE BASE FOR THIS SESSION:
{json.dumps(report['data'], indent=2)}

YOUR MISSION:
1. Explain the satellite indices (NDVI, NDWI, NDBI, NDMI) in plain language
   relevant to the user's project and the scanned location.
2. When asked about Sponge Cities, ground your answer in the NDWI and NDBI
   values from THIS report — explain why those specific numbers justify (or
   argue against) sponge-city interventions.
3. Reference the feasibility findings and recommendations already in the report
   when they are relevant.
4. Be concise, technically accurate, and always tie advice back to the data.
""".strip()


def _create_chat(report: dict) -> object:
    return gemini.chats.create(
        model="models/gemini-2.0-flash",
        config=types.GenerateContentConfig(
            system_instruction=_build_system_instruction(report)
        ),
    )


def _send_with_retry(chat, message: str, retries: int = 3) -> str:
    """Send a message with automatic back-off on 429/503 errors."""
    last_error = None
    for attempt in range(retries):
        try:
            return chat.send_message(message).text
        except Exception as e:
            err = str(e)
            if "429" in err or "503" in err:
                wait = 5 * (attempt + 1)
                time.sleep(wait)
                last_error = e
                continue
            raise HTTPException(status_code=502, detail=f"Gemini error: {e}")
    raise HTTPException(status_code=503, detail=f"Gemini unavailable after {retries} retries: {last_error}")

# ---------------------------------------------------------------------------
# SCHEMAS
# ---------------------------------------------------------------------------

class SessionResponse(BaseModel):
    session_id: str
    report_loaded: str
    message: str


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str

# ---------------------------------------------------------------------------
# ROUTES
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Meta"])
def health():
    return {"status": "ok", "service": "Sustainability Consultant API", "version": "1.0.0"}


@app.post("/chat/session", response_model=SessionResponse, tags=["Chat"])
def create_session():
    """
    Start a new consultant session grounded in the latest assessment report.
    Returns a `session_id` — pass it with every `/chat/message` call.
    """
    import uuid
    report   = _get_latest_report()
    sid      = str(uuid.uuid4())
    _sessions[sid] = _create_chat(report)

    return SessionResponse(
        session_id    = sid,
        report_loaded = report["filename"],
        message       = "Session ready. Ask me anything about the satellite assessment.",
    )


@app.post("/chat/message", response_model=ChatResponse, tags=["Chat"])
def send_message(req: ChatRequest):
    """
    Send a message to an existing consultant session.
    The AI's context is the full satellite report loaded at session creation.
    """
    chat = _sessions.get(req.session_id)
    if not chat:
        raise HTTPException(
            status_code=404,
            detail="Session not found. Create one via POST /chat/session first.",
        )

    reply = _send_with_retry(chat, req.message)
    return ChatResponse(session_id=req.session_id, reply=reply)


@app.delete("/chat/session/{session_id}", tags=["Chat"])
def end_session(session_id: str):
    """Explicitly close and discard a chat session."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found.")
    del _sessions[session_id]
    return {"message": f"Session {session_id} closed."}