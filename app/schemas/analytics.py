from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel

class TimeSeriesPoint(BaseModel):
    date: str
    scans: int
    unique_scans: int

class DeviceBreakdown(BaseModel):
    device: str
    count: int
    percentage: float

class CountryBreakdown(BaseModel):
    country_code: str
    country_name: str
    count: int
    percentage: float

class OSBreakdown(BaseModel):
    os: str
    count: int
    percentage: float

class BrowserBreakdown(BaseModel):
    browser: str
    count: int
    percentage: float

class QRAnalyticsResponse(BaseModel):
    qr_id: str
    title: str
    total_scans: int
    unique_scans: int
    time_range: str # '7d', '30d', 'all'
    time_series: List[TimeSeriesPoint]
    devices: List[DeviceBreakdown]
    countries: List[CountryBreakdown]
    operating_systems: List[OSBreakdown]
    browsers: List[BrowserBreakdown]
    recent_scans: List[Dict[str, Any]]
