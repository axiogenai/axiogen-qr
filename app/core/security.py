import secrets
import base64
import hashlib
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Any
from jose import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHash
from .config import settings

# Argon2id Hasher for Production API Key Hashing
ph = PasswordHasher(
    time_cost=3,        # 3 iterations
    memory_cost=65536,  # 64 MB memory
    parallelism=4,      # 4 parallel threads
    hash_len=32,
    salt_len=16
)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain user password against a bcrypt hash."""
    plain_bytes = plain_password.encode('utf-8')[:72]
    hashed_bytes = hashed_password.encode('utf-8')
    try:
        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    """Hash user account password using bcrypt."""
    plain_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain_bytes, salt).decode('utf-8')

def create_access_token(subject: str | Any, expires_delta: Optional[timedelta] = None) -> str:
    """Generate signed JWT access token."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def generate_api_key() -> tuple[str, str, str]:
    """
    Generate secure 256-bit CSPRNG developer API key.
    Returns: (raw_key, key_prefix, key_hash)
    Format: aq_live_<32_random_bytes_base64>
    Hash: Argon2id with salt and memory-hard work factor.
    """
    random_bytes = secrets.token_bytes(32)
    raw_token = base64.urlsafe_b64encode(random_bytes).decode('utf-8').rstrip('=')
    raw_key = f"aq_live_{raw_token}"
    key_prefix = raw_key[:20]  # e.g. "aq_live_8f9d2e1c7b4a" for O(1) prefix lookup
    key_hash = hash_api_key(raw_key)
    return raw_key, key_prefix, key_hash

def hash_api_key(raw_key: str) -> str:
    """Hash API key with Argon2id and unique salt."""
    return ph.hash(raw_key)

def verify_api_key_hash(raw_key: str, stored_hash: str) -> bool:
    """Constant-time Argon2id verification with fallback."""
    try:
        ph.verify(stored_hash, raw_key)
        return True
    except (VerifyMismatchError, VerificationError, InvalidHash):
        return False
