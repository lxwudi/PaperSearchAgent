from fastapi import APIRouter

from app.api.routers import auth, teams, search, ws, library

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(teams.router)
api_router.include_router(search.router)
api_router.include_router(library.router)
api_router.include_router(ws.router)
