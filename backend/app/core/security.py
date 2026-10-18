import os
from datetime import datetime, timedelta
from typing import Optional, Any, Union
import bcrypt
import jwt
from pydantic import BaseModel

# Secret key for JWT signing - in production can be overridden via ENV
SECRET_KEY = os.environ.get("SECRET_KEY", "cachemind-enterprise-secret-key-2026-supersecure")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 hours

class TokenData(BaseModel):
    user_id: Optional[str] = None
    username: Optional[str] = None
    role: Optional[str] = None

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[TokenData]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        username: str = payload.get("username")
        role: str = payload.get("role")
        if user_id is None:
            return None
        return TokenData(user_id=user_id, username=username, role=role)
    except jwt.PyJWTError:
        return None
