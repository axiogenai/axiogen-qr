import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .core.config import settings
from .core.database import engine, Base
from .api.v1.router import api_v1_router
from .api.redirect import redirect_router
from .api.media_viewer import media_viewer_router

# Rate Limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure database schema is created safely
    try:
        async with engine.begin() as conn:
            await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, checkfirst=True))
    except Exception as e:
        print(f"[DB Init] Notice: {e}")
    yield
    # Shutdown: Dispose engine
    await engine.dispose()

app = FastAPI(
    title="Axiogen QR API",
    description="Production-grade Branded QR Platform & Developer API. Custom module styling, linear/radial gradients, dynamic redirects, and real-time scan analytics.",
    version="1.0.0",
    docs_url="/docs" if settings.ENABLE_DOCS else None,
    redoc_url="/redoc" if settings.ENABLE_DOCS else None,
    openapi_url="/openapi.json" if settings.ENABLE_DOCS else None,
    lifespan=lifespan
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Robust CORS Configuration supporting Vercel and production domains
ALLOWED_ORIGINS = [
    "https://axiogen-qr.vercel.app",
    "https://voice.axiogen.in",
    "https://api.axiogen.in",
    "https://qr.axiogen.in",
    "http://localhost:3000",
    "http://127.0.0.1:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*axiogen.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time-Ms", "X-Total-Count"],
    max_age=600,
)

# Production Security Headers & Response Timing Middleware
@app.middleware("http")
async def security_and_timing_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = (time.perf_counter() - start_time) * 1000.0

    # Timing Header
    response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"

    # Standard OWASP Production Security Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

    return response

# Mount Endpoints
app.include_router(api_v1_router, prefix="/v1")
app.include_router(redirect_router)
app.include_router(media_viewer_router)

@app.get("/health", tags=["System"])
async def health():
    return {
        "status": "healthy",
        "service": "Axiogen QR Engine",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }

@app.get("/", tags=["System"])
async def root():
    return {
        "service": "Axiogen QR API",
        "documentation": "/docs" if settings.ENABLE_DOCS else "Disabled in production",
        "version": "1.0.0"
    }
