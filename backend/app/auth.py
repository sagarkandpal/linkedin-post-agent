from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from jose import jwt, JWTError

from app.config import JWT_SECRET_KEY

# bcrypt = industry-standard password hashing algorithm (slow on purpose,
# taaki brute-force guessing mushkil ho)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 din valid rahega token


# ---------- PASSWORD HASHING ----------
def hash_password(plain_password: str) -> str:
    """Signup ke waqt: raw password ko kabhi DB me save nahi karte,
    hash karke save karte hain."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Login ke waqt: user ne jo password diya, use DB wale hash se match karo."""
    return pwd_context.verify(plain_password, hashed_password)


# ---------- JWT TOKEN ----------
def create_access_token(data: dict) -> str:
    """Login successful hone pe ye call hota hai — token banata hai
    jisme user ki info (e.g. email) aur expiry time embedded hota hai."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """Protected route pe har request ke token ko verify karta hai.
    Invalid/expired token → None return karta hai."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


# ---------- ROUTE PROTECTION ----------
# HTTPBearer -> FastAPI ko batata hai "ye route Bearer token maangta hai",
# isi se Swagger UI me "Authorize" lock button apne aap dikhta hai.
security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Protected routes me Depends(get_current_user) lagega.
    Token missing/invalid/expired ho to request yahin reject ho jayegi (401)."""
    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return payload  # isme {"sub": email, "exp": ...} hoga