from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.db.database import connect_db, close_db
from app.api.api_v1 import api_router

app = FastAPI(
    title="Socialice Backend",
    version="1.0.0",
    description="Backend API for mobile app (FastAPI + MongoDB)",
)

# CORS middleware - allow React Native or other frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change to specific domain in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB connection on startup
@app.on_event("startup")
async def startup_db():
    await connect_db()

# DB disconnection on shutdown
@app.on_event("shutdown")
async def shutdown_db():
    await close_db()

# Include all versioned routes
app.include_router(api_router, prefix="/socialice")

