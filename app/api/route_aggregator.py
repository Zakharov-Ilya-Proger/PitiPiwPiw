from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.requests import router as requests_router

router = APIRouter(prefix='/api/v1')
router.include_router(auth_router)
router.include_router(requests_router)
