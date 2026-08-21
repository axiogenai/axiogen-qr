from typing import Optional, Union
from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..core.config import settings
from ..core.database import get_db
from ..models.user import User
from ..models.api_key import ApiKey
from ..services.api_key_service import ApiKeyService
from ..core.security import get_password_hash

bearer_scheme = HTTPBearer(auto_error=False)

async def get_or_create_default_user(db: AsyncSession) -> User:
    """Get or create the default browser/dashboard user account."""
    res = await db.execute(select(User).where(User.email == "default_admin@axiogen.in"))
    user = res.scalar_one_or_none()
    if not user:
        user = User(
            id="default-master-user-001",
            email="default_admin@axiogen.in",
            password_hash=get_password_hash("AxiogenDefault2026!"),
            name="Axiogen Admin"
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    cred: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> User:
    """
    Authenticate request using JWT token.
    If no token is supplied (e.g. initial web dashboard visit), fallbacks seamlessly to the default user.
    """
    if not cred or not cred.credentials:
        return await get_or_create_default_user(db)
    
    token = cred.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id:
            res = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
            user = res.scalar_one_or_none()
            if user:
                return user
    except (JWTError, Exception):
        pass

    return await get_or_create_default_user(db)

async def get_current_auth_context(
    db: AsyncSession = Depends(get_db),
    cred: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> Union[User, ApiKey]:
    """
    Flexible authentication: Accepts either JWT Bearer token OR Developer API Key (aq_live_...).
    Falls back to default dashboard user if no credentials supplied.
    """
    token_or_key = None
    if cred and cred.credentials:
        token_or_key = cred.credentials
    elif x_api_key:
        token_or_key = x_api_key

    if not token_or_key:
        return await get_or_create_default_user(db)

    # 1. Check if it's an API Key (starts with aq_live_)
    if token_or_key.startswith("aq_live_"):
        api_key = await ApiKeyService.verify_key(db, token_or_key)
        if api_key:
            return api_key
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or deactivated API Key")

    # 2. Otherwise treat as JWT
    try:
        payload = jwt.decode(token_or_key, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id:
            res = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
            user = res.scalar_one_or_none()
            if user:
                return user
    except (JWTError, Exception):
        pass

    return await get_or_create_default_user(db)
