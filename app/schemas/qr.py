from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl

class GradientStop(BaseModel):
    offset: float = Field(ge=0.0, le=1.0)
    color: str

class StyleConfig(BaseModel):
    module_shape: str = Field(default="square", description="square, rounded, dots, circle, diamond")
    eye_shape: str = Field(default="square", description="square, rounded, circle")
    foreground_color: str = Field(default="#000000")
    background_color: str = Field(default="#FFFFFF")
    eye_color: Optional[str] = None
    eye_inner_color: Optional[str] = None
    gradient_stops: Optional[List[Tuple[float, str]]] = None
    gradient_type: str = Field(default="linear", description="linear or radial")
    gradient_angle: float = Field(default=45.0)
    logo_size_ratio: float = Field(default=0.22, ge=0.1, le=0.35)
    logo_position: str = Field(default="center", description="center, top, bottom")
    error_correction: str = Field(default="H", description="L, M, Q, H")

class QRCreateRequest(BaseModel):
    title: str = Field(..., max_length=255)
    target_url: str = Field(..., description="Target destination URL or plain content")
    type: str = Field(default="url", description="url, text, vcard, wifi, email, sms")
    is_dynamic: bool = Field(default=True, description="True for trackable editable URL, False for direct static encoding")
    style_config: Optional[StyleConfig] = None
    custom_slug: Optional[str] = Field(default=None, max_length=64)

class QRUpdateRequest(BaseModel):
    title: Optional[str] = None
    target_url: Optional[str] = None
    is_active: Optional[bool] = None
    style_config: Optional[StyleConfig] = None

class QRRenderRequest(BaseModel):
    content: str
    style_config: Optional[StyleConfig] = None
    format: str = Field(default="png", description="png or svg")
    module_size: int = Field(default=12, ge=4, le=64)
    quiet_zone: int = Field(default=4, ge=0, le=16)
    logo_base64: Optional[str] = Field(default=None, description="Base64-encoded logo image (PNG/JPG). Omit the data:image prefix.")

class QRResponse(BaseModel):
    id: str
    title: str
    slug: Optional[str] = None
    type: str
    target_url: str
    redirect_url: Optional[str] = None
    is_dynamic: bool
    is_active: bool
    scan_count: int
    style_config: Dict[str, Any]
    logo_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class QRPublicRenderResponse(BaseModel):
    format: str
    data_uri: Optional[str] = None
    svg: Optional[str] = None
