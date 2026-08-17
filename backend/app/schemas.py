from pydantic import BaseModel


# ---------- AUTH SCHEMAS ----------
class SignupRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


# ---------- REQUEST SCHEMAS ----------
# Jab frontend "/api/generate" call karega, body me sirf topic aayega.
# Baaki (thread_id, draft, attempt, etc.) backend khud generate/track karta hai.
class GenerateRequest(BaseModel):
    topic: str
    use_emojis: bool = False


# Jab user human_review step pe approve karta hai ya feedback deta hai,
# frontend "/api/review" ko ye bhejega — kis thread ko resume karna hai,
# aur user ka response kya tha ("approved" ya feedback text).
class ReviewRequest(BaseModel):
    thread_id: str
    response: str  # "approved" / "accept" / ya rejection feedback text


# ---------- RESPONSE SCHEMAS (documentation ke liye, actual response SSE stream hai) ----------
# /api/generate aur /api/review dono StreamingResponse (SSE) return karte hain,
# isliye inka exact Pydantic response_model use nahi hoga — lekin ye shape
# batati hai ki frontend ko har event me kya milega, taaki React side pe
# parsing likhते waqt confusion na ho.

class StatusEvent(BaseModel):
    """type: 'status' — draft ban raha hai, isse pehle 'Writer likh raha hai...' dikhao"""
    type: str = "status"
    message: str
    node: str  # "writer" ya "tools"


class DraftReadyEvent(BaseModel):
    """type: 'draft_ready' — pehli complete draft mil gayi (review se pehle)"""
    type: str = "draft_ready"
    draft: str


class AwaitingReviewEvent(BaseModel):
    """type: 'awaiting_review' — graph pause ho gaya hai, user ka input chahiye.
    is thread_id ko /api/review call me wapas bhejna hoga."""
    type: str = "awaiting_review"
    thread_id: str
    draft: str
    attempt: int


class DoneEvent(BaseModel):
    """type: 'done' — final result: ya to approve ho gaya, ya max attempts (5) khatam"""
    type: str = "done"
    draft: str
    approved: bool
    attempt: int


# ---------- GET /api/posts RESPONSE SHAPE ----------
class PostRecord(BaseModel):
    """MongoDB me saved approved post ka shape"""
    id: str
    topic: str
    draft: str
    attempts: int
    thread_id: str