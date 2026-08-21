from typing import List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.config import settings
from ....models.user import User
from ....models.api_key import ApiKey
from ....schemas.qr import (
    QRCreateRequest,
    QRUpdateRequest,
    QRRenderRequest,
    QRResponse,
    QRPublicRenderResponse
)
from ....services.qr_service import QRService
from ....engine import QRCodeEngine, export_png_base64
from ...deps import get_current_auth_context, get_current_user

router = APIRouter(prefix="/qr", tags=["QR Codes"])

def get_user_id_from_auth(auth_obj: Union[User, ApiKey]) -> str:
    return auth_obj.id if isinstance(auth_obj, User) else auth_obj.user_id

@router.post("/create", response_model=QRResponse)
async def create_qr_code(
    payload: QRCreateRequest,
    db: AsyncSession = Depends(get_db),
    auth: Union[User, ApiKey] = Depends(get_current_auth_context)
):
    """
    Create a new branded static or dynamic QR code.
    Accessible via JWT or Developer API Key.
    """
    user_id = get_user_id_from_auth(auth)
    qr_entry = await QRService.create_qr(db, user_id=user_id, payload=payload)

    redirect_url = f"{settings.REDIRECT_BASE_URL}/{qr_entry.slug}" if qr_entry.is_dynamic else None
    return QRResponse(
        id=qr_entry.id,
        title=qr_entry.title,
        slug=qr_entry.slug,
        type=qr_entry.type,
        target_url=qr_entry.target_url,
        redirect_url=redirect_url,
        is_dynamic=qr_entry.is_dynamic,
        is_active=qr_entry.is_active,
        scan_count=qr_entry.scan_count,
        style_config=qr_entry.style_config,
        logo_url=qr_entry.logo_url,
        created_at=qr_entry.created_at,
        updated_at=qr_entry.updated_at
    )

@router.post("/styled", response_model=QRPublicRenderResponse)
async def render_styled_qr_on_the_fly(payload: QRRenderRequest):
    """
    Instantly render a styled QR code on-the-fly without saving to database.
    Useful for live real-time studio preview in the dashboard.
    Supports optional inline base64 logo embedding.
    """
    import base64, io
    from PIL import Image as PILImage

    styles = payload.style_config.dict() if payload.style_config else {}

    # Decode logo if provided
    logo_image = None
    if payload.logo_base64:
        try:
            # Strip data URI prefix if present
            logo_data = payload.logo_base64
            if "," in logo_data:
                logo_data = logo_data.split(",", 1)[1]
            raw_bytes = base64.b64decode(logo_data)
            logo_image = PILImage.open(io.BytesIO(raw_bytes)).convert("RGBA")
        except Exception:
            logo_image = None

    if payload.format == "svg":
        svg_xml = QRCodeEngine.render_svg(
            data=payload.content,
            module_shape=styles.get("module_shape", "square"),
            eye_shape=styles.get("eye_shape", "square"),
            foreground_color=styles.get("foreground_color", "#000000"),
            background_color=styles.get("background_color", "#FFFFFF"),
            gradient_stops=styles.get("gradient_stops"),
            gradient_type=styles.get("gradient_type", "linear"),
            gradient_angle=styles.get("gradient_angle", 45.0),
            module_size=payload.module_size,
            quiet_zone=payload.quiet_zone,
            error_correction=styles.get("error_correction", "H")
        )
        return QRPublicRenderResponse(format="svg", svg=svg_xml)
    else:
        img = QRCodeEngine.render_qr(
            data=payload.content,
            module_shape=styles.get("module_shape", "square"),
            eye_shape=styles.get("eye_shape", "square"),
            foreground_color=styles.get("foreground_color", "#000000"),
            background_color=styles.get("background_color", "#FFFFFF"),
            eye_color=styles.get("eye_color"),
            eye_inner_color=styles.get("eye_inner_color"),
            gradient_stops=styles.get("gradient_stops"),
            gradient_type=styles.get("gradient_type", "linear"),
            gradient_angle=styles.get("gradient_angle", 45.0),
            logo_image=logo_image,
            logo_size_ratio=styles.get("logo_size_ratio", 0.22),
            logo_position=styles.get("logo_position", "center"),
            module_size=payload.module_size,
            quiet_zone=payload.quiet_zone,
            error_correction=styles.get("error_correction", "H")
        )
        data_uri = export_png_base64(img)
        return QRPublicRenderResponse(format="png", data_uri=data_uri)

@router.get("/list", response_model=List[QRResponse])
async def list_qr_codes(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    auth: Union[User, ApiKey] = Depends(get_current_auth_context)
):
    """List all QR codes for the authenticated user/app."""
    user_id = get_user_id_from_auth(auth)
    qrs = await QRService.list_user_qrs(db, user_id=user_id, limit=limit, offset=offset)
    
    return [
        QRResponse(
            id=q.id,
            title=q.title,
            slug=q.slug,
            type=q.type,
            target_url=q.target_url,
            redirect_url=f"{settings.REDIRECT_BASE_URL}/{q.slug}" if q.is_dynamic else None,
            is_dynamic=q.is_dynamic,
            is_active=q.is_active,
            scan_count=q.scan_count,
            style_config=q.style_config,
            logo_url=q.logo_url,
            created_at=q.created_at,
            updated_at=q.updated_at
        )
        for q in qrs
    ]

@router.get("/{qr_id}", response_model=QRResponse)
async def get_qr_code(
    qr_id: str,
    db: AsyncSession = Depends(get_db),
    auth: Union[User, ApiKey] = Depends(get_current_auth_context)
):
    """Get metadata for a specific QR code."""
    user_id = get_user_id_from_auth(auth)
    qr_entry = await QRService.get_by_id(db, qr_id=qr_id, user_id=user_id)
    if not qr_entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QR code not found")

    return QRResponse(
        id=qr_entry.id,
        title=qr_entry.title,
        slug=qr_entry.slug,
        type=qr_entry.type,
        target_url=qr_entry.target_url,
        redirect_url=f"{settings.REDIRECT_BASE_URL}/{qr_entry.slug}" if qr_entry.is_dynamic else None,
        is_dynamic=qr_entry.is_dynamic,
        is_active=qr_entry.is_active,
        scan_count=qr_entry.scan_count,
        style_config=qr_entry.style_config,
        logo_url=qr_entry.logo_url,
        created_at=qr_entry.created_at,
        updated_at=qr_entry.updated_at
    )

@router.put("/{qr_id}", response_model=QRResponse)
async def update_qr_code(
    qr_id: str,
    payload: QRUpdateRequest,
    db: AsyncSession = Depends(get_db),
    auth: Union[User, ApiKey] = Depends(get_current_auth_context)
):
    """
    Update target URL or style config of a QR code.
    For dynamic QR codes, this instantly changes destination with NO re-printing needed.
    """
    user_id = get_user_id_from_auth(auth)
    updated = await QRService.update_qr(db, qr_id=qr_id, user_id=user_id, payload=payload)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QR code not found")

    return QRResponse(
        id=updated.id,
        title=updated.title,
        slug=updated.slug,
        type=updated.type,
        target_url=updated.target_url,
        redirect_url=f"{settings.REDIRECT_BASE_URL}/{updated.slug}" if updated.is_dynamic else None,
        is_dynamic=updated.is_dynamic,
        is_active=updated.is_active,
        scan_count=updated.scan_count,
        style_config=updated.style_config,
        logo_url=updated.logo_url,
        created_at=updated.created_at,
        updated_at=updated.updated_at
    )

@router.delete("/{qr_id}")
async def delete_qr_code(
    qr_id: str,
    db: AsyncSession = Depends(get_db),
    auth: Union[User, ApiKey] = Depends(get_current_auth_context)
):
    """Delete a QR code."""
    user_id = get_user_id_from_auth(auth)
    success = await QRService.delete_qr(db, qr_id=qr_id, user_id=user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QR code not found")
    return {"message": "QR code deleted successfully", "id": qr_id}

@router.get("/{qr_id}/download")
async def download_qr_image(
    qr_id: str,
    format: str = Query("png", pattern="^(png|svg)$"),
    size: int = Query(12, ge=4, le=64),
    db: AsyncSession = Depends(get_db)
):
    """Download ready-to-use PNG or SVG file for a QR code."""
    qr_entry = await QRService.get_by_id(db, qr_id=qr_id)
    if not qr_entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QR code not found")

    data, media_type = QRService.render_qr_image(qr_entry, format=format, module_size=size)
    filename = f"{qr_entry.slug or qr_entry.id}.{format}"
    
    return Response(
        content=data if isinstance(data, bytes) else data.encode('utf-8'),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
