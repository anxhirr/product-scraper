from fastapi import APIRouter
from scraper.hape_browser import scrape_hape_product
from pydantic import BaseModel
from typing import List

router = APIRouter()

class ProductResponse(BaseModel):
    title: str
    sku: str
    price: str
    vendor: str
    images: List[str]
    variants: List[str]

@router.get("/search/{query}", response_model=ProductResponse)
def search(query: str):
    return scrape_hape_product(query)
