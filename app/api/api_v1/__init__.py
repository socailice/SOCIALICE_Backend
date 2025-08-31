from fastapi import APIRouter
from app.api.api_v1.endpoints import auth,  post, chat,profile, cubes

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(post.router, prefix="/posts", tags=["Posts"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(profile.router, prefix="/profile", tags=["Profile"])
api_router.include_router(cubes.router, prefix="/cubes", tags=["Cubes"])
