from datetime import datetime, timezone
import motor.motor_asyncio

from app.config import MONGO_URI

# Motor = MongoDB ka async driver (FastAPI async hai, isliye normal
# pymongo se calls block ho jate, motor non-blocking hai).
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)

# "linkedin_agent" database ke andar collections (SQL ka "table" jaisa)
db = client["linkedin_agent"]
posts_collection = db["posts"]
users_collection = db["users"]


# ---------- USERS (signup/login ke liye) ----------
async def get_user_by_email(email: str) -> dict | None:
    """Login ke waqt aur signup me duplicate check karne ke liye"""
    return await users_collection.find_one({"email": email})


async def create_user(email: str, hashed_password: str) -> str:
    """Signup ke waqt naya user save karta hai (password already hashed hokar aata hai)"""
    doc = {
        "email": email,
        "hashed_password": hashed_password,
        "created_at": datetime.now(timezone.utc),
    }
    result = await users_collection.insert_one(doc)
    return str(result.inserted_id)


async def save_post(topic: str, draft: str, attempts: int, thread_id: str, user_email: str) -> str:
    """Jab human_review me user approve karta hai, /api/review isko call karega
    taaki final post permanently save ho jaye (history/reuse ke liye).
    user_email save karte hain taaki baad me sirf isi user ke posts filter ho sakein."""
    doc = {
        "topic": topic,
        "draft": draft,
        "attempts": attempts,
        "thread_id": thread_id,
        "user_email": user_email,
        "created_at": datetime.now(timezone.utc),
    }
    result = await posts_collection.insert_one(doc)
    return str(result.inserted_id)


async def get_all_posts(user_email: str) -> list[dict]:
    """GET /api/posts isko call karega — sirf USI user ke posts wapas milte hain,
    dusre users ke posts kabhi mix nahi honge (user_email se filter kiya)."""
    posts = []
    cursor = posts_collection.find({"user_email": user_email}).sort("created_at", -1)
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])  # ObjectId JSON me nahi jaata, string banao
        posts.append(doc)
    return posts