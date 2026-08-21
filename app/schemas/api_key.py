from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

class ApiKeyCreate(BaseModel):
    name: str = Field(..., max_length=100, description="Friendly label for the API key")
    scopes: Optional[str] = "qr:read,qr:write"

class ApiKeyRead(BaseModel):
    id: str
    key_prefix: str
    name: str
    scopes: str
    requests_count: int
    last_used_at: Optional[datetime] = None
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True

class ApiKeyCreatedResponse(ApiKeyRead):
    raw_key: str = Field(..., description="Full secret token (only shown once at creation time)")
