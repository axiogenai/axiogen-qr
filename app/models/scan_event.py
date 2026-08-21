import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from ..core.database import Base

class ScanEvent(Base):
    __tablename__ = "scan_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    qr_id = Column(String(36), ForeignKey("qr_codes.id", ondelete="CASCADE"), nullable=False, index=True)
    scanned_at = Column(DateTime, default=datetime.utcnow, index=True)
    ip_hash = Column(String(64), nullable=True)
    country_code = Column(String(8), nullable=True)
    country_name = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    device_type = Column(String(32), nullable=True)   # 'mobile', 'desktop', 'tablet'
    os_family = Column(String(64), nullable=True)     # 'iOS', 'Android', 'macOS', 'Windows'
    browser_family = Column(String(64), nullable=True)# 'Safari', 'Chrome', 'Firefox'
    referrer = Column(Text, nullable=True)
    user_agent = Column(Text, nullable=True)

    # Relationships
    qr_code = relationship("QRCode", back_populates="scan_events")
