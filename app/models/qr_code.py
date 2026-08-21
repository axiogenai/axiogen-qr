import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from ..core.database import Base

class QRCode(Base):
    __tablename__ = "qr_codes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(64), unique=True, index=True, nullable=True) # e.g. 'abc123' for dynamic redirect
    type = Column(String(32), default="url") # 'url', 'text', 'vcard', 'wifi', 'email'
    target_url = Column(Text, nullable=False)
    style_config = Column(JSON, nullable=False, default=dict)
    logo_url = Column(Text, nullable=True)
    error_correction = Column(String(2), default="H")
    is_dynamic = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    scan_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="qr_codes")
    scan_events = relationship("ScanEvent", back_populates="qr_code", cascade="all, delete-orphan")
