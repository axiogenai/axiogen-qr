from typing import Optional, Union
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.user import User
from ....models.api_key import ApiKey
from ....schemas.analytics import QRAnalyticsResponse
from ....services.analytics_service import AnalyticsService
from ...deps import get_current_auth_context

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/{qr_id}", response_model=QRAnalyticsResponse)
async def get_qr_analytics(
    qr_id: str,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    auth: Union[User, ApiKey] = Depends(get_current_auth_context)
):
    """Retrieve detailed scan telemetry and breakdown for a QR code."""
    user_id = auth.id if isinstance(auth, User) else auth.user_id
    analytics = await AnalyticsService.get_qr_analytics(db, qr_id=qr_id, user_id=user_id, days=days)
    if not analytics:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QR code not found or access denied")
    return analytics

@router.delete("/{qr_id}/delete-all-scans")
async def gdpr_delete_all_scans(
    qr_id: str,
    db: AsyncSession = Depends(get_db),
    auth: Union[User, ApiKey] = Depends(get_current_auth_context)
):
    """
    GDPR Right to Erasure / Compliance: Permanently delete all recorded scan telemetry
    and events associated with this QR code.
    """
    from sqlalchemy import delete
    from ....models.qr_code import QRCode
    from ....models.scan_event import ScanEvent
    from sqlalchemy.future import select

    user_id = auth.id if isinstance(auth, User) else auth.user_id
    
    # Verify ownership
    qr_res = await db.execute(select(QRCode).where(QRCode.id == qr_id, QRCode.user_id == user_id))
    qr_entry = qr_res.scalar_one_or_none()
    if not qr_entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QR code not found or access denied")

    await db.execute(delete(ScanEvent).where(ScanEvent.qr_id == qr_id))
    qr_entry.scan_count = 0
    await db.commit()

    return {"message": "All scan telemetry successfully deleted under GDPR right to erasure", "qr_id": qr_id}
