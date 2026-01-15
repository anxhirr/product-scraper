# app/main.py
from fastapi import FastAPI
from app.routes import router

app = FastAPI(title="Multi-Website Product Scraper API")

app.include_router(router)
