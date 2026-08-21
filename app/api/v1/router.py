from fastapi import APIRouter
from .endpoints import auth, qr, analytics, api_keys, media

api_v1_router = APIRouter()

api_v1_router.include_router(auth.router)
api_v1_router.include_router(qr.router)
api_v1_router.include_router(analytics.router)
api_v1_router.include_router(api_keys.router)
api_v1_router.include_router(api_keys.router, prefix="/qr")  # Also accessible via /v1/qr/keys/*
api_v1_router.include_router(media.router)
