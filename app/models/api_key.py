import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship
from ..core.database import Base

class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    key_prefix = Column(String(24), index=True, nullable=False)  # "aq_live_8f9d2e1c7b4a" for O(1) lookup
    key_hash = Column(String(255), nullable=False)               # Argon2id salted hash
    name = Column(String(100), nullable=False)
    scopes = Column(String(255), default="qr:read,qr:write")
    rate_limit_rpm = Column(Integer, default=60)
    requests_count = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="api_keys")
