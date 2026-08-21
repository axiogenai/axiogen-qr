from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..core.database import get_db, AsyncSessionLocal
from ..models.qr_code import QRCode
from ..services.analytics_service import AnalyticsService

redirect_router = APIRouter(tags=["Dynamic QR Redirects"])

async def record_scan_background(qr_id: str, user_agent: str, client_ip: str, referrer: str):
    """Background task to record scan without blocking the 302 redirect."""
    async with AsyncSessionLocal() as db:
        try:
            await AnalyticsService.record_scan(
                db=db,
                qr_id=qr_id,
                user_agent=user_agent,
                ip_address=client_ip,
                referrer=referrer
            )
        except Exception as e:
            print(f"[Analytics Ingest Warning]: {e}")

@redirect_router.api_route("/r/{slug}", methods=["GET", "HEAD"])
async def dynamic_qr_redirect(
    slug: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Sub-20ms dynamic QR redirect.
    Instantly returns HTTP 302 to destination while recording scan telemetry in background.
    """
    res = await db.execute(
        select(QRCode).where(QRCode.slug == slug, QRCode.is_active == True)
    )
    qr_entry = res.scalar_one_or_none()
    if not qr_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="QR code not found or has been deactivated."
        )

    # Extract client headers
    user_agent = request.headers.get("user-agent", "")
    client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "")
    if "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()
    referrer = request.headers.get("referer", "")

    # Queue background scan telemetry
    background_tasks.add_task(
        record_scan_background,
        qr_id=qr_entry.id,
        user_agent=user_agent,
        client_ip=client_ip,
        referrer=referrer
    )

    # Instant Redirect (302 Found)
    target = qr_entry.target_url
    if not (target.startswith("http://") or target.startswith("https://")):
        target = f"https://{target}"

    return RedirectResponse(url=target, status_code=status.HTTP_302_FOUND)
