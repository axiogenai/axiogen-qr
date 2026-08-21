import os
import json
import uuid
import time
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import FileResponse
from ....core.config import settings

router = APIRouter(prefix="/media", tags=["Multimedia Hosting"])

# Allowed extensions and categories
MIME_CATEGORIES = {
    # PDFs & Documents
    "application/pdf": "pdf",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "doc",
    "text/plain": "doc",
    
    # Images
    "image/png": "image",
    "image/jpeg": "image",
    "image/jpg": "image",
    "image/webp": "image",
    "image/gif": "image",
    "image/svg+xml": "image",
    
    # Videos
    "video/mp4": "video",
    "video/webm": "video",
    "video/quicktime": "video",
    "video/x-msvideo": "video",
    
    # Audio
    "audio/mpeg": "audio",
    "audio/mp3": "audio",
    "audio/wav": "audio",
    "audio/ogg": "audio",
    "audio/aac": "audio",
    "audio/m4a": "audio",
    "audio/x-m4a": "audio",
}

EXTENSION_FALLBACK = {
    ".pdf": "pdf",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".webp": "image",
    ".gif": "image",
    ".svg": "image",
    ".mp4": "video",
    ".webm": "video",
    ".mov": "video",
    ".mp3": "audio",
    ".wav": "audio",
    ".ogg": "audio",
    ".m4a": "audio",
}

def get_upload_dir() -> str:
    upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir

@router.post("/upload")
async def upload_media_file(file: UploadFile = File(...)):
    """
    Upload a multimedia file (PDF, Image, Video, Audio) up to 25MB.
    Returns the hosted mobile viewer URL and media metadata.
    """
    upload_dir = get_upload_dir()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    # Extract extension
    original_filename = file.filename or "media_file"
    _, ext = os.path.splitext(original_filename.lower())
    
    # Detect category
    content_type = file.content_type or "application/octet-stream"
    category = MIME_CATEGORIES.get(content_type) or EXTENSION_FALLBACK.get(ext) or "doc"

    # Read and validate size in chunks
    media_id = f"m_{uuid.uuid4().hex[:12]}"
    saved_filename = f"{media_id}{ext}"
    saved_path = os.path.join(upload_dir, saved_filename)
    meta_path = os.path.join(upload_dir, f"{media_id}.json")

    total_bytes = 0
    with open(saved_path, "wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)  # 1MB chunks
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > max_bytes:
                # Cleanup and abort
                f.close()
                if os.path.exists(saved_path):
                    os.remove(saved_path)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB"
                )
            f.write(chunk)

    if total_bytes == 0:
        if os.path.exists(saved_path):
            os.remove(saved_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty."
        )

    # Save metadata
    meta = {
        "media_id": media_id,
        "original_filename": original_filename,
        "content_type": content_type,
        "category": category,
        "size_bytes": total_bytes,
        "saved_filename": saved_filename,
        "uploaded_at": time.time()
    }
    with open(meta_path, "w", encoding="utf-8") as mf:
        json.dump(meta, mf)

    viewer_url = f"{settings.MEDIA_BASE_URL}/{media_id}"
    download_url = f"{settings.PUBLIC_URL}/v1/media/file/{media_id}"

    return {
        "media_id": media_id,
        "viewer_url": viewer_url,
        "download_url": download_url,
        "filename": original_filename,
        "category": category,
        "size_bytes": total_bytes,
        "size_formatted": format_file_size(total_bytes),
        "content_type": content_type
    }

@router.get("/file/{media_id}")
async def get_raw_media_file(media_id: str, download: bool = False):
    """Serve the raw file binary with proper MIME headers and range requests."""
    upload_dir = get_upload_dir()
    meta_path = os.path.join(upload_dir, f"{media_id}.json")

    if not os.path.exists(meta_path):
        raise HTTPException(status_code=404, detail="Media file not found")

    with open(meta_path, "r", encoding="utf-8") as mf:
        meta = json.load(mf)

    file_path = os.path.join(upload_dir, meta["saved_filename"])
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Media file content missing")

    filename = meta.get("original_filename", f"{media_id}")
    content_type = meta.get("content_type", "application/octet-stream")

    disposition = f'attachment; filename="{filename}"' if download else f'inline; filename="{filename}"'

    return FileResponse(
        path=file_path,
        media_type=content_type,
        headers={"Content-Disposition": disposition}
    )

def format_file_size(bytes_num: int) -> str:
    if bytes_num < 1024:
        return f"{bytes_num} B"
    elif bytes_num < 1024 * 1024:
        return f"{bytes_num / 1024:.1f} KB"
    else:
        return f"{bytes_num / (1024 * 1024):.1f} MB"
