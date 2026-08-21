import uuid
import secrets
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete

from ..models.qr_code import QRCode
from ..schemas.qr import QRCreateRequest, QRUpdateRequest, StyleConfig
from ..engine import QRCodeEngine, export_png_bytes, export_png_base64, export_svg_string
from ..core.config import settings

def generate_unique_slug(length: int = 6) -> str:
    """Generate URL-safe short slug for dynamic redirects."""
    return secrets.token_urlsafe(length)[:length].replace('-', 'a').replace('_', 'b')

class QRService:
    @staticmethod
    async def create_qr(db: AsyncSession, user_id: str, payload: QRCreateRequest) -> QRCode:
        slug = None
        if payload.is_dynamic:
            slug = payload.custom_slug if payload.custom_slug else generate_unique_slug()
            # Ensure unique slug
            while True:
                existing = await db.execute(select(QRCode).where(QRCode.slug == slug))
                if not existing.scalar_one_or_none():
                    break
                slug = generate_unique_slug()

        style_dict = payload.style_config.dict() if payload.style_config else StyleConfig().dict()

        qr_entry = QRCode(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=payload.title,
            slug=slug,
            type=payload.type,
            target_url=payload.target_url,
            style_config=style_dict,
            is_dynamic=payload.is_dynamic,
            is_active=True,
            scan_count=0
        )
        db.add(qr_entry)
        await db.commit()
        await db.refresh(qr_entry)
        return qr_entry

    @staticmethod
    async def get_by_id(db: AsyncSession, qr_id: str, user_id: Optional[str] = None) -> Optional[QRCode]:
        query = select(QRCode).where(QRCode.id == qr_id)
        if user_id:
            query = query.where(QRCode.user_id == user_id)
        res = await db.execute(query)
        return res.scalar_one_or_none()

    @staticmethod
    async def get_by_slug(db: AsyncSession, slug: str) -> Optional[QRCode]:
        res = await db.execute(select(QRCode).where(QRCode.slug == slug, QRCode.is_active == True))
        return res.scalar_one_or_none()

    @staticmethod
    async def list_user_qrs(db: AsyncSession, user_id: str, limit: int = 100, offset: int = 0) -> List[QRCode]:
        res = await db.execute(
            select(QRCode)
            .where(QRCode.user_id == user_id)
            .order_by(QRCode.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return res.scalars().all()

    @staticmethod
    async def update_qr(db: AsyncSession, qr_id: str, user_id: str, payload: QRUpdateRequest) -> Optional[QRCode]:
        qr_entry = await QRService.get_by_id(db, qr_id, user_id=user_id)
        if not qr_entry:
            return None

        if payload.title is not None:
            qr_entry.title = payload.title
        if payload.target_url is not None:
            qr_entry.target_url = payload.target_url
        if payload.is_active is not None:
            qr_entry.is_active = payload.is_active
        if payload.style_config is not None:
            qr_entry.style_config = payload.style_config.dict()

        await db.commit()
        await db.refresh(qr_entry)
        return qr_entry

    @staticmethod
    async def delete_qr(db: AsyncSession, qr_id: str, user_id: str) -> bool:
        qr_entry = await QRService.get_by_id(db, qr_id, user_id=user_id)
        if not qr_entry:
            return False
        await db.delete(qr_entry)
        await db.commit()
        return True

    @staticmethod
    def render_qr_image(qr_entry: QRCode, format: str = "png", module_size: int = 12) -> tuple[bytes | str, str]:
        """
        Renders QR code using its saved style_config and target or dynamic URL.
        """
        content = f"{settings.REDIRECT_BASE_URL}/{qr_entry.slug}" if qr_entry.is_dynamic else qr_entry.target_url
        styles = qr_entry.style_config or {}

        if format == "svg":
            svg_data = QRCodeEngine.render_svg(
                data=content,
                module_shape=styles.get("module_shape", "square"),
                eye_shape=styles.get("eye_shape", "square"),
                foreground_color=styles.get("foreground_color", "#000000"),
                background_color=styles.get("background_color", "#FFFFFF"),
                gradient_stops=styles.get("gradient_stops"),
                gradient_type=styles.get("gradient_type", "linear"),
                gradient_angle=styles.get("gradient_angle", 45.0),
                module_size=module_size,
                error_correction=styles.get("error_correction", "H")
            )
            return svg_data, "image/svg+xml"
        else:
            img = QRCodeEngine.render_qr(
                data=content,
                module_shape=styles.get("module_shape", "square"),
                eye_shape=styles.get("eye_shape", "square"),
                foreground_color=styles.get("foreground_color", "#000000"),
                background_color=styles.get("background_color", "#FFFFFF"),
                eye_color=styles.get("eye_color"),
                eye_inner_color=styles.get("eye_inner_color"),
                gradient_stops=styles.get("gradient_stops"),
                gradient_type=styles.get("gradient_type", "linear"),
                gradient_angle=styles.get("gradient_angle", 45.0),
                module_size=module_size,
                error_correction=styles.get("error_correction", "H")
            )
            png_bytes = export_png_bytes(img)
            return png_bytes, "image/png"
