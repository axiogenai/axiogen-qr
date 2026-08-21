import os
import json
import time
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.database import get_db
from ..services.analytics_service import AnalyticsService

media_viewer_router = APIRouter(tags=["Media Viewer"])

def get_upload_dir() -> str:
    upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir

def format_file_size(bytes_num: int) -> str:
    if bytes_num < 1024:
        return f"{bytes_num} B"
    elif bytes_num < 1024 * 1024:
        return f"{bytes_num / 1024:.1f} KB"
    else:
        return f"{bytes_num / (1024 * 1024):.1f} MB"

@media_viewer_router.get("/m/{media_id}", response_class=HTMLResponse)
async def view_hosted_media(
    media_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Renders a mobile-optimized, dark-mode multimedia viewer for scanned QR codes.
    Tracks the scan event in telemetry database before serving.
    """
    upload_dir = get_upload_dir()
    meta_path = os.path.join(upload_dir, f"{media_id}.json")

    if not os.path.exists(meta_path):
        return HTMLResponse(
            status_code=404,
            content="""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Media Not Found | Axiogen QR</title>
                <style>
                    body { background: #09090b; color: #f4f4f5; font-family: -apple-system, BlinkMacSystemFont, sans-serif; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 20px; text-align: center; }
                    .card { background: #18181b; border: 1px solid #27272a; padding: 32px; border-radius: 16px; max-width: 400px; }
                    h1 { font-size: 20px; margin-bottom: 8px; color: #fff; }
                    p { font-size: 13px; color: #a1a1aa; line-height: 1.5; }
                </style>
            </head>
            <body>
                <div class="card">
                    <h1>Media Not Found</h1>
                    <p>This media asset may have been removed or the link is invalid.</p>
                </div>
            </body>
            </html>
            """
        )

    with open(meta_path, "r", encoding="utf-8") as mf:
        meta = json.load(mf)

    # Telemetry logging: extract IP & User-Agent
    ip_addr = request.headers.get("x-forwarded-for")
    if ip_addr:
        ip_addr = ip_addr.split(",")[0].strip()
    else:
        ip_addr = request.client.host if request.client else "127.0.0.1"

    user_agent = request.headers.get("user-agent", "")

    # Log scan telemetry in background
    try:
        await AnalyticsService.record_scan(
            db=db,
            qr_id=media_id,
            ip_address=ip_addr,
            user_agent=user_agent
        )
    except Exception as e:
        print(f"[Media Scan Telemetry] Notice: {e}")

    # Build player markup based on category
    category = meta.get("category", "doc")
    filename = meta.get("original_filename", "Media Asset")
    size_str = format_file_size(meta.get("size_bytes", 0))
    file_stream_url = f"{settings.PUBLIC_URL}/v1/media/file/{media_id}"
    download_url = f"{settings.PUBLIC_URL}/v1/media/file/{media_id}?download=true"
    content_type = meta.get("content_type", "")

    media_player_html = ""
    if category == "video":
        media_player_html = f"""
        <div class="player-container">
            <video controls playsinline preload="metadata" class="media-video" poster="">
                <source src="{file_stream_url}" type="{content_type}">
                Your browser does not support HTML5 video streaming.
            </video>
        </div>
        """
    elif category == "audio":
        media_player_html = f"""
        <div class="audio-container">
            <div class="audio-icon">🎵</div>
            <div class="audio-meta">
                <div class="audio-title">{filename}</div>
                <div class="audio-size">{size_str} • Audio Stream</div>
            </div>
            <audio controls class="media-audio" preload="metadata">
                <source src="{file_stream_url}" type="{content_type}">
                Your browser does not support audio playback.
            </audio>
        </div>
        """
    elif category == "image":
        media_player_html = f"""
        <div class="image-container">
            <img src="{file_stream_url}" alt="{filename}" class="media-image" loading="lazy" />
        </div>
        """
    elif category == "pdf":
        media_player_html = f"""
        <div class="pdf-container">
            <div class="pdf-icon">📄</div>
            <div class="pdf-info">
                <h3>{filename}</h3>
                <p>PDF Document • {size_str}</p>
            </div>
            <div class="pdf-actions">
                <a href="{file_stream_url}" target="_blank" class="btn btn-primary">Open PDF Reader</a>
            </div>
        </div>
        """
    else:
        media_player_html = f"""
        <div class="doc-container">
            <div class="doc-icon">📁</div>
            <div class="doc-info">
                <h3>{filename}</h3>
                <p>{size_str} • {content_type}</p>
            </div>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>{filename} | Axiogen Media</title>
    <meta name="theme-color" content="#09090b">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: #09090b;
            color: #f4f4f5;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            padding: 16px;
        }}
        .header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 16px;
            background: #18181b;
            border: 1px solid #27272a;
            border-radius: 12px;
            margin-bottom: 20px;
        }}
        .brand {{
            font-weight: 700;
            font-size: 14px;
            color: #ffffff;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .brand span {{ color: #71717a; }}
        .badge {{
            font-size: 10px;
            font-family: monospace;
            padding: 3px 8px;
            border-radius: 6px;
            background: #27272a;
            color: #a1a1aa;
            text-transform: uppercase;
        }}
        .main-card {{
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            background: #121215;
            border: 1px solid #27272a;
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 20px;
            overflow: hidden;
        }}
        .player-container, .image-container {{
            width: 100%;
            max-width: 680px;
            border-radius: 12px;
            overflow: hidden;
            background: #000;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }}
        .media-video {{
            width: 100%;
            height: auto;
            max-height: 70vh;
            display: block;
            outline: none;
        }}
        .media-image {{
            width: 100%;
            height: auto;
            max-height: 70vh;
            object-fit: contain;
            display: block;
        }}
        .audio-container, .pdf-container, .doc-container {{
            width: 100%;
            max-width: 440px;
            background: #18181b;
            border: 1px solid #27272a;
            border-radius: 16px;
            padding: 24px;
            text-align: center;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 12px;
        }}
        .audio-icon, .pdf-icon, .doc-icon {{
            font-size: 36px;
            background: #27272a;
            height: 64px;
            width: 64px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 16px;
            margin-bottom: 4px;
        }}
        .audio-title, .pdf-info h3, .doc-info h3 {{
            font-size: 15px;
            font-weight: 600;
            color: #ffffff;
            word-break: break-all;
        }}
        .audio-size, .pdf-info p, .doc-info p {{
            font-size: 12px;
            color: #71717a;
            margin-top: 4px;
        }}
        .media-audio {{
            width: 100%;
            margin-top: 8px;
            outline: none;
        }}
        .actions-bar {{
            display: flex;
            gap: 10px;
            width: 100%;
            max-width: 440px;
            margin: 0 auto;
        }}
        .btn {{
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 12px 16px;
            border-radius: 10px;
            font-size: 13px;
            font-weight: 600;
            text-decoration: none;
            cursor: pointer;
            transition: all 0.15s ease;
        }}
        .btn-primary {{
            background: #ffffff;
            color: #09090b;
            border: 1px solid #ffffff;
        }}
        .btn-primary:hover {{
            background: #e4e4e7;
        }}
        .btn-secondary {{
            background: #18181b;
            color: #d4d4d8;
            border: 1px solid #27272a;
        }}
        .btn-secondary:hover {{
            background: #27272a;
            color: #ffffff;
        }}
        .footer {{
            text-align: center;
            font-size: 11px;
            color: #52525b;
            padding: 12px;
        }}
    </style>
</head>
<body>
    <header class="header">
        <div class="brand">Axiogen <span>QR</span></div>
        <div class="badge">{category.upper()} ASSET</div>
    </header>

    <main class="main-card">
        {media_player_html}
    </main>

    <div class="actions-bar">
        <a href="{download_url}" class="btn btn-primary">
            <span>⬇ Download File</span>
        </a>
        <button onclick="shareLink()" class="btn btn-secondary" id="shareBtn">
            <span>🔗 Share</span>
        </button>
    </div>

    <footer class="footer">
        Powered by Axiogen QR • High-Speed Developer Infrastructure
    </footer>

    <script>
        function shareLink() {{
            if (navigator.share) {{
                navigator.share({{
                    title: '{filename}',
                    url: window.location.href
                }}).catch(console.error);
            }} else {{
                navigator.clipboard.writeText(window.location.href);
                const btn = document.getElementById('shareBtn');
                btn.innerHTML = '<span>✓ Copied!</span>';
                setTimeout(() => {{
                    btn.innerHTML = '<span>🔗 Share</span>';
                }}, 2000);
            }}
        }}
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)
