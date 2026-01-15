from fastapi import APIRouter
from scraper.hape_browser import scrape_hape_product
from scraper.models import Product

router = APIRouter()

@router.get("/search/{query}", response_model=Product)
def search(query: str):
    return scrape_hape_product(query)
