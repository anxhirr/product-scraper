# app/main.py
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import router

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    # Load .env file from the backend directory (parent of app directory)
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    # python-dotenv not installed, skip loading .env file
    pass

app = FastAPI(title="Multi-Website Product Scraper API")

# Configure CORS
# Get allowed origins from environment variable, default to Next.js default port
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
allow_origins = [frontend_url]

# Support multiple origins if comma-separated
if "," in frontend_url:
    allow_origins = [origin.strip() for origin in frontend_url.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
