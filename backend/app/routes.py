from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from scraper.registry import get_scraper, get_available_sites
from scraper.models import Product

router = APIRouter()


@router.get("/search/{site}/{query}", response_model=Product)
def search(site: str, query: str):
    """
    Search for a product on the specified website.
    
    Args:
        site: Website identifier (e.g., "hape", "elrincondelosgenios")
        query: Search query text
    
    Returns:
        Product data from the first search result
    """
    try:
        scraper = get_scraper(site)
        return scraper.scrape_product(query)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")


@router.get("/sites", response_model=list[str])
def list_sites():
    """Returns a list of available website identifiers."""
    return get_available_sites()


class BatchSearchRequest(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    site: str
    brand: Optional[str] = None


class BatchSearchRequestBody(BaseModel):
    products: List[BatchSearchRequest]
    batch_size: int = 3
    batch_delay: int = 1000  # milliseconds


class BatchSearchResponse(BaseModel):
    product: Optional[Product] = None
    error: Optional[str] = None
    status: str  # "success" or "error"


def scrape_single_product(request: BatchSearchRequest) -> BatchSearchResponse:
    """Helper function to scrape a single product, used in thread pool."""
    try:
        scraper = get_scraper(request.site)
        # Use code if provided, otherwise use name
        query = request.code if request.code else (request.name or "")
        product = scraper.scrape_product(query)
        return BatchSearchResponse(product=product, status="success")
    except ValueError as e:
        return BatchSearchResponse(error=str(e), status="error")
    except Exception as e:
        return BatchSearchResponse(error=f"Scraping failed: {str(e)}", status="error")


@router.post("/search/batch", response_model=List[BatchSearchResponse])
def batch_search(body: BatchSearchRequestBody):
    """
    Search for multiple products in batches.
    
    Args:
        body: Request body containing products list and batch configuration
    
    Returns:
        List of search results with status for each product
    """
    products = body.products
    if not products:
        raise HTTPException(status_code=400, detail="No products provided")

    # Validate all requests
    for i, req in enumerate(products):
        if not req.site:
            raise HTTPException(
                status_code=400, detail=f"Product {i + 1}: site is required"
            )
        if not req.name and not req.code:
            raise HTTPException(
                status_code=400,
                detail=f"Product {i + 1}: either name or code must be provided",
            )

    # Use provided config or defaults
    batch_size = body.batch_size
    batch_delay = body.batch_delay / 1000.0  # Convert to seconds

    # Validate batch size
    if batch_size < 1 or batch_size > 50:
        raise HTTPException(
            status_code=400, detail="Batch size must be between 1 and 50"
        )

    results: List[BatchSearchResponse] = []

    # Process products in batches
    for batch_start in range(0, len(products), batch_size):
        batch_end = min(batch_start + batch_size, len(products))
        batch = products[batch_start:batch_end]

        # Process batch in parallel using ThreadPoolExecutor
        batch_results: List[BatchSearchResponse] = [None] * len(batch)  # type: ignore

        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            # Submit all tasks in the batch
            future_to_index = {
                executor.submit(scrape_single_product, product): i
                for i, product in enumerate(batch)
            }

            # Collect results as they complete
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    batch_results[index] = future.result()
                except Exception as e:
                    batch_results[index] = BatchSearchResponse(
                        error=f"Unexpected error: {str(e)}", status="error"
                    )

        # Add batch results to overall results
        results.extend(batch_results)

        # Add delay between batches (except after the last batch)
        if batch_end < len(products):
            time.sleep(batch_delay)

    return results
