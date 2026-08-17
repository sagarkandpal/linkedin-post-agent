import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

# Fail fast agar zaroori keys missing hain — baad mein cryptic
# connection errors se acha hai ki startup pe hi pata chal jaye.
REQUIRED_KEYS = {
    "GROQ_API_KEY": GROQ_API_KEY,
    "TAVILY_API_KEY": TAVILY_API_KEY,
    "JWT_SECRET_KEY": JWT_SECRET_KEY,
}

missing = [name for name, value in REQUIRED_KEYS.items() if not value]
if missing:
    raise RuntimeError(
        f"Missing required env vars: {', '.join(missing)}. Check your .env file."
    )