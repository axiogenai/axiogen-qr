from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.user import User
from ....schemas.api_key import ApiKeyCreate, ApiKeyRead, ApiKeyCreatedResponse
from ....services.api_key_service import ApiKeyService
from ...deps import get_current_user

router = APIRouter(prefix="/keys", tags=["Developer API Keys"])

@router.post("/create", response_model=ApiKeyCreatedResponse)
async def create_api_key(
    payload: ApiKeyCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Generate a new developer API key (aq_live_...).
    The raw secret key is returned ONLY once upon creation.
    """
    api_key_entry, raw_key = await ApiKeyService.create_key(
        db,
        user_id=user.id,
        name=payload.name,
        scopes=payload.scopes or "qr:read,qr:write"
    )

    return ApiKeyCreatedResponse(
        id=api_key_entry.id,
        key_prefix=api_key_entry.key_prefix,
        name=api_key_entry.name,
        scopes=api_key_entry.scopes,
        requests_count=api_key_entry.requests_count,
        last_used_at=api_key_entry.last_used_at,
        created_at=api_key_entry.created_at,
        is_active=api_key_entry.is_active,
        raw_key=raw_key
    )

@router.get("/list", response_model=List[ApiKeyRead])
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """List all active API keys for the authenticated user."""
    keys = await ApiKeyService.list_user_keys(db, user_id=user.id)
    return keys

@router.delete("/{key_id}")
async def revoke_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Revoke and deactivate an API key."""
    success = await ApiKeyService.revoke_key(db, user_id=user.id, key_id=key_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    return {"message": "API key revoked successfully", "id": key_id}
