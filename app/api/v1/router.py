from fastapi import APIRouter

from app.api.v1.routes.sprints import router as sprints_router
from app.api.v1.routes.boards import router as boards_router

api_router = APIRouter(prefix="/v1")
api_router.include_router(sprints_router, tags=["sprints"])
api_router.include_router(boards_router, tags=["boards"])
