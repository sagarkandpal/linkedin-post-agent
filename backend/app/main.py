import json
import uuid

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from langgraph.types import Command

from app.agent import compiled_graph
from app.database import save_post, get_all_posts, get_user_by_email, create_user
from app.schemas import GenerateRequest, ReviewRequest, SignupRequest, LoginRequest
from app.auth import hash_password, verify_password, create_access_token, get_current_user

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIASGIMiddleware
from slowapi.errors import RateLimitExceeded
from app.auth import decode_access_token


app = FastAPI(title="LinkedIn Post Agent API")

def get_user_email(request):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return "anonymous"
    token = auth_header.replace("Bearer ", "")
    payload = decode_access_token(token)
    if payload:
        return payload.get("sub", "anonymous")
    return "anonymous"


limiter = Limiter(key_func = get_user_email)

app.state.limiter = limiter

app.add_exception_handler(
    RateLimitExceeded, 
    lambda request, exc: JSONResponse(
        status_code=429,
        content={"detail": "Daily limit khatam ho gayi hai, kal try karo"},
   )
)

app.add_middleware(SlowAPIASGIMiddleware)


# React dev server (Vite) yahin se requests karega — CORS allow karna zaroori hai
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Kaunse graph node pe kaunsa "status" message frontend ko dikhana hai
STATUS_MESSAGES = {
    "writer": "Writer draft likh raha hai...",
}


def sse(event_type: str, data: dict) -> str:
    """Ek Server-Sent-Event line banata hai. React fetch stream se ye
    'data: {...}' format parse karega."""
    return f"data: {json.dumps({'type': event_type, **data})}\n\n"


async def run_graph_stream(graph_input, config: dict, user_email: str):
    """/api/generate aur /api/review dono isi function ko use karte hain —
    graph_input pehli baar initial_state hota hai, resume ke waqt Command(resume=...).
    user_email save karne ke liye chahiye jab post approve ho."""
    thread_id = config["configurable"]["thread_id"]

    # stream_mode="updates" -> har node ke complete hote hi uska output milta hai
    for event in compiled_graph.stream(graph_input, config=config, stream_mode="updates"):
        for node_name, node_output in event.items():

            if node_name in STATUS_MESSAGES:
                yield sse("status", {"message": STATUS_MESSAGES[node_name], "node": node_name})

            elif node_name == "writer":
                # draft ban chuki hai, review se pehle bhi dikha do
                yield sse("draft_ready", {"draft": node_output.get("draft", "")})

            elif node_name == "__interrupt__":
                # graph human_review pe pause ho gaya — user ka input chahiye
                payload = node_output[0].value
                yield sse("awaiting_review", {
                    "thread_id": thread_id,
                    "draft": payload["draft"],
                    "attempt": payload["attempt"],
                })
                return  # yahin ruk jao, /api/review ka wait karo

    # Loop yahan tak pahuncha matlab graph END tak chala gaya (approved ya max attempts)
    state = compiled_graph.get_state(config)
    values = state.values

    if values.get("is_approved"):
        await save_post(
            topic=values["topic"],
            draft=values["draft"],
            attempts=values["attempt"],
            thread_id=thread_id,
            user_email=user_email,
        )

    yield sse("done", {
        "draft": values.get("draft", ""),
        "approved": values.get("is_approved", False),
        "attempt": values.get("attempt", 0),
    })


@app.post("/api/signup")
async def signup(req: SignupRequest):
    existing = await get_user_by_email(req.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed = hash_password(req.password)
    await create_user(req.email, hashed)
    return {"message": "Account created. Please log in."}


@app.post("/api/login")
async def login(req: LoginRequest):
    user = await get_user_by_email(req.email)
    if not user or not verify_password(req.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": user["email"]})
    return {"access_token": token, "token_type": "bearer"}


@app.post("/api/generate")
@limiter.limit("5/day")
async def generate_post(request: Request, req: GenerateRequest, current_user: dict = Depends(get_current_user)):
    """Naya topic -> naya thread_id -> graph pehli baar start hota hai"""
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    initial_state = {
        "topic": req.topic,
        "draft": "",
        "review_feedback": "",
        "is_approved": False,
        "attempt": 0,
        "use_emojis": req.use_emojis,
    }
    return StreamingResponse(
        run_graph_stream(initial_state, config, current_user["sub"]),
        media_type="text/event-stream",
    )


@app.post("/api/review")
@limiter.limit("5/day")
async def review_post(request: Request, req: ReviewRequest, current_user: dict = Depends(get_current_user)):
    """User ka approve/feedback -> same thread_id pe graph resume hota hai"""
    config = {"configurable": {"thread_id": req.thread_id}}
    return StreamingResponse(
        run_graph_stream(Command(resume=req.response), config, current_user["sub"]),
        media_type="text/event-stream",
    )


@app.get("/api/posts")
async def list_posts(current_user: dict = Depends(get_current_user)):
    """History page ke liye — sirf isi user ke approved posts (current_user['sub'] = email)"""
    return await get_all_posts(current_user["sub"])


@app.get("/api/health")
async def health():
    return {"status": "ok"}