import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from user_agents import parse as parse_user_agent
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, update

from ..models.qr_code import QRCode
from ..models.scan_event import ScanEvent
from ..schemas.analytics import (
    QRAnalyticsResponse,
    TimeSeriesPoint,
    DeviceBreakdown,
    CountryBreakdown,
    OSBreakdown,
    BrowserBreakdown
)

class AnalyticsService:
    @staticmethod
    def parse_client_metadata(user_agent_str: Optional[str], ip_address: Optional[str]) -> Dict[str, Any]:
        """
        Parse device, OS, browser and apply GDPR-compliant IP anonymization.
        IPs are masked (IPv4 /24 subnet or salted with daily rotating salt)
        so they cannot be reversed via rainbow tables.
        """
        device_type = "desktop"
        os_family = "Unknown"
        browser_family = "Unknown"

        if user_agent_str:
            ua = parse_user_agent(user_agent_str)
            if ua.is_mobile:
                device_type = "mobile"
            elif ua.is_tablet:
                device_type = "tablet"
            else:
                device_type = "desktop"

            os_family = ua.os.family or "Unknown"
            browser_family = ua.browser.family or "Unknown"

        ip_hash = None
        if ip_address:
            # Mask the last octet (GDPR compliant IP anonymization standard)
            # e.g., 192.168.1.123 -> 192.168.1.0
            parts = ip_address.split('.')
            if len(parts) == 4:
                masked_ip = f"{parts[0]}.{parts[1]}.{parts[2]}.0"
            else:
                masked_ip = ip_address.rsplit(':', 1)[0] + ":0000" if ':' in ip_address else ip_address
            
            # Hash with salt
            today = datetime.utcnow().strftime('%Y-%m-%d')
            salt = f"axiogen_qr_salt_{today}"
            ip_hash = hashlib.sha256(f"{masked_ip}_{salt}".encode('utf-8')).hexdigest()

        return {
            "device_type": device_type,
            "os_family": os_family,
            "browser_family": browser_family,
            "ip_hash": ip_hash,
            "country_code": "IN",
            "country_name": "India",
            "city": "Mumbai"
        }

    @staticmethod
    async def record_scan(
        db: AsyncSession,
        qr_id: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        referrer: Optional[str] = None
    ) -> None:
        """Asynchronously record a scan event and increment counter."""
        meta = AnalyticsService.parse_client_metadata(user_agent, ip_address)

        event = ScanEvent(
            qr_id=qr_id,
            scanned_at=datetime.utcnow(),
            ip_hash=meta["ip_hash"],
            country_code=meta["country_code"],
            country_name=meta["country_name"],
            city=meta["city"],
            device_type=meta["device_type"],
            os_family=meta["os_family"],
            browser_family=meta["browser_family"],
            referrer=referrer,
            user_agent=user_agent
        )
        db.add(event)

        # Increment scan_count on QRCode
        await db.execute(
            update(QRCode)
            .where(QRCode.id == qr_id)
            .values(scan_count=QRCode.scan_count + 1)
        )
        await db.commit()

    @staticmethod
    async def get_qr_analytics(
        db: AsyncSession,
        qr_id: str,
        user_id: str,
        days: int = 30
    ) -> Optional[QRAnalyticsResponse]:
        """Fetch aggregated analytics for a specific QR code."""
        # Verify ownership
        qr_res = await db.execute(select(QRCode).where(QRCode.id == qr_id, QRCode.user_id == user_id))
        qr_entry = qr_res.scalar_one_or_none()
        if not qr_entry:
            return None

        since_date = datetime.utcnow() - timedelta(days=days)

        # 1. Total and Unique Scans
        total_res = await db.execute(
            select(func.count(ScanEvent.id))
            .where(ScanEvent.qr_id == qr_id, ScanEvent.scanned_at >= since_date)
        )
        total_scans = total_res.scalar() or 0

        unique_res = await db.execute(
            select(func.count(func.distinct(ScanEvent.ip_hash)))
            .where(ScanEvent.qr_id == qr_id, ScanEvent.scanned_at >= since_date)
        )
        unique_scans = unique_res.scalar() or 0

        # 2. Time Series (Daily counts)
        # For cross-DB compatibility (SQLite + PostgreSQL)
        daily_scans = await db.execute(
            select(
                func.date(ScanEvent.scanned_at).label("day"),
                func.count(ScanEvent.id).label("count"),
                func.count(func.distinct(ScanEvent.ip_hash)).label("unique_count")
            )
            .where(ScanEvent.qr_id == qr_id, ScanEvent.scanned_at >= since_date)
            .group_by(func.date(ScanEvent.scanned_at))
            .order_by(func.date(ScanEvent.scanned_at))
        )
        time_series = [
            TimeSeriesPoint(
                date=str(row.day),
                scans=row.count,
                unique_scans=row.unique_count
            )
            for row in daily_scans.all()
        ]

        # 3. Device Breakdown
        dev_res = await db.execute(
            select(ScanEvent.device_type, func.count(ScanEvent.id))
            .where(ScanEvent.qr_id == qr_id, ScanEvent.scanned_at >= since_date)
            .group_by(ScanEvent.device_type)
        )
        devices = []
        for dev, cnt in dev_res.all():
            pct = round((cnt / total_scans * 100), 1) if total_scans > 0 else 0
            devices.append(DeviceBreakdown(device=dev or "Other", count=cnt, percentage=pct))

        # 4. OS Breakdown
        os_res = await db.execute(
            select(ScanEvent.os_family, func.count(ScanEvent.id))
            .where(ScanEvent.qr_id == qr_id, ScanEvent.scanned_at >= since_date)
            .group_by(ScanEvent.os_family)
        )
        os_list = []
        for os_name, cnt in os_res.all():
            pct = round((cnt / total_scans * 100), 1) if total_scans > 0 else 0
            os_list.append(OSBreakdown(os=os_name or "Other", count=cnt, percentage=pct))

        # 5. Browser Breakdown
        browser_res = await db.execute(
            select(ScanEvent.browser_family, func.count(ScanEvent.id))
            .where(ScanEvent.qr_id == qr_id, ScanEvent.scanned_at >= since_date)
            .group_by(ScanEvent.browser_family)
        )
        browsers = []
        for b_name, cnt in browser_res.all():
            pct = round((cnt / total_scans * 100), 1) if total_scans > 0 else 0
            browsers.append(BrowserBreakdown(browser=b_name or "Other", count=cnt, percentage=pct))

        # 6. Country Breakdown
        country_res = await db.execute(
            select(ScanEvent.country_code, ScanEvent.country_name, func.count(ScanEvent.id))
            .where(ScanEvent.qr_id == qr_id, ScanEvent.scanned_at >= since_date)
            .group_by(ScanEvent.country_code, ScanEvent.country_name)
        )
        countries = []
        for cc, cn, cnt in country_res.all():
            pct = round((cnt / total_scans * 100), 1) if total_scans > 0 else 0
            countries.append(CountryBreakdown(
                country_code=cc or "XX",
                country_name=cn or "Unknown",
                count=cnt,
                percentage=pct
            ))

        # 7. Recent Scans
        recent_res = await db.execute(
            select(ScanEvent)
            .where(ScanEvent.qr_id == qr_id)
            .order_by(ScanEvent.scanned_at.desc())
            .limit(15)
        )
        recent_scans = [
            {
                "scanned_at": ev.scanned_at.isoformat(),
                "device_type": ev.device_type,
                "os": ev.os_family,
                "browser": ev.browser_family,
                "country": ev.country_name,
                "city": ev.city
            }
            for ev in recent_res.scalars().all()
        ]

        return QRAnalyticsResponse(
            qr_id=qr_id,
            title=qr_entry.title,
            total_scans=total_scans,
            unique_scans=unique_scans,
            time_range=f"{days}d",
            time_series=time_series,
            devices=devices,
            countries=countries,
            operating_systems=os_list,
            browsers=browsers,
            recent_scans=recent_scans
        )
