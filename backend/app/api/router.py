from fastapi import APIRouter
from app.api.routes import auth, health, papers, questions

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(papers.router, tags=["papers"])
api_router.include_router(questions.router, tags=["questions"])
