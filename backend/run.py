#!/usr/bin/env python3
"""
Startup script for the FastAPI backend server.
Uses environment variables for configuration.
"""
import os
from pathlib import Path
import uvicorn

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    # Load .env file from the backend directory
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded environment variables from {env_path}")
except ImportError:
    # python-dotenv not installed, skip loading .env file
    pass

if __name__ == "__main__":
    # Get port from environment variable, default to 8000
    port = int(os.getenv("BACKEND_PORT", "8000"))
    host = os.getenv("BACKEND_HOST", "0.0.0.0")
    
    print(f"Starting backend server on {host}:{port}")
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True,  # Enable auto-reload for development
    )
