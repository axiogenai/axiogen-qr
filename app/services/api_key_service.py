import uuid
from datetime import datetime
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete

from ..models.api_key import ApiKey
from ..models.user import User
from ..core.security import generate_api_key, hash_api_key

class ApiKeyService:
    @staticmethod
    async def create_key(db: AsyncSession, user_id: str, name: str, scopes: str = "qr:read,qr:write") -> Tuple[ApiKey, str]:
        """
        Create a new API key.
        Returns: (ApiKey database model, raw_key_string_to_show_once)
        """
        raw_key, key_prefix, key_hash = generate_api_key()

        api_key_entry = ApiKey(
            id=str(uuid.uuid4()),
            user_id=user_id,
            key_prefix=key_prefix,
            key_hash=key_hash,
            name=name,
            scopes=scopes,
            requests_count=0,
            is_active=True
        )
        db.add(api_key_entry)
        await db.commit()
        await db.refresh(api_key_entry)
        return api_key_entry, raw_key

    @staticmethod
    async def verify_key(db: AsyncSession, raw_key: str) -> Optional[ApiKey]:
        """
        Verify raw API key token with fast O(1) prefix lookup + Argon2id verification.
        Increments usage counter and updates last_used_at timestamp.
        """
        if not raw_key.startswith("aq_live_") or len(raw_key) < 20:
            return None

        prefix = raw_key[:20]
        res = await db.execute(
            select(ApiKey).where(ApiKey.key_prefix == prefix, ApiKey.is_active == True)
        )
        api_key = res.scalar_one_or_none()
        
        if not api_key:
            return None

        from ..core.security import verify_api_key_hash
        if not verify_api_key_hash(raw_key, api_key.key_hash):
            return None

        # Update last used and increment requests
        await db.execute(
            update(ApiKey)
            .where(ApiKey.id == api_key.id)
            .values(
                requests_count=ApiKey.requests_count + 1,
                last_used_at=datetime.utcnow()
            )
        )
        await db.commit()
        return api_key

    @staticmethod
    async def list_user_keys(db: AsyncSession, user_id: str) -> List[ApiKey]:
        res = await db.execute(
            select(ApiKey)
            .where(ApiKey.user_id == user_id)
            .order_by(ApiKey.created_at.desc())
        )
        return res.scalars().all()

    @staticmethod
    async def revoke_key(db: AsyncSession, user_id: str, key_id: str) -> bool:
        res = await db.execute(
            select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user_id)
        )
        key_entry = res.scalar_one_or_none()
        if not key_entry:
            return False
        await db.delete(key_entry)
        await db.commit()
        return True
