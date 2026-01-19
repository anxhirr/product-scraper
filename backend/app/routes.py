from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from scraper.registry import get_scraper, get_available_sites, get_sites_for_brand, get_available_brands
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


@router.get("/brands", response_model=list[str])
def list_brands():
    """Returns a list of available brand identifiers."""
    return get_available_brands()


class BatchSearchRequest(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    site: Optional[str] = None  # Made optional, brand takes priority
    brand: Optional[str] = None
    category: Optional[str] = None
    barcode: Optional[str] = None
    price: Optional[str] = None


class BatchSearchRequestBody(BaseModel):
    products: List[BatchSearchRequest]
    batch_size: int = 3
    batch_delay: int = 1000  # milliseconds


class BatchSearchResponse(BaseModel):
    product: Optional[Product] = None
    error: Optional[str] = None
    status: str  # "success" or "error"
    category: Optional[str] = None
    barcode: Optional[str] = None
    price: Optional[str] = None


def scrape_single_product(request: BatchSearchRequest) -> BatchSearchResponse:
    """
    Helper function to scrape a single product, used in thread pool.
    Supports brand-based scraping with fallback to multiple sites.
    Preserves Excel values for category, barcode, and price.
    """
    # Determine which sites to try
    sites_to_try: list[str] = []
    
    if request.brand:
        # Brand takes priority - get ordered list of sites for this brand
        try:
            sites_to_try = get_sites_for_brand(request.brand)
        except ValueError as e:
            return BatchSearchResponse(
                error=str(e),
                status="error",
                category=request.category,
                barcode=request.barcode,
                price=request.price,
            )
    elif request.site:
        # Fallback to direct site specification (backward compatibility)
        sites_to_try = [request.site]
    else:
        return BatchSearchResponse(
            error="Either brand or site must be provided",
            status="error",
            category=request.category,
            barcode=request.barcode,
            price=request.price,
        )
    
    # Use code if provided, otherwise use name
    query = request.code if request.code else (request.name or "")
    if not query:
        return BatchSearchResponse(
            error="Either name or code must be provided",
            status="error",
            category=request.category,
            barcode=request.barcode,
            price=request.price,
        )
    
    # Try each site in order until one succeeds
    last_error: Optional[str] = None
    for site in sites_to_try:
        try:
            scraper = get_scraper(site)
            product = scraper.scrape_product(query)
            return BatchSearchResponse(
                product=product,
                status="success",
                category=request.category,
                barcode=request.barcode,
                price=request.price,
            )
        except ValueError as e:
            # ValueError means site not found, but we should continue to next site
            last_error = str(e)
            continue
        except Exception as e:
            # Other exceptions - try next site
            last_error = f"Scraping failed on {site}: {str(e)}"
            continue
    
    # All sites failed
    error_msg = last_error or f"All sites failed for brand/site: {request.brand or request.site}"
    return BatchSearchResponse(
        error=error_msg,
        status="error",
        category=request.category,
        barcode=request.barcode,
        price=request.price,
    )


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
        if not req.brand and not req.site:
            raise HTTPException(
                status_code=400,
                detail=f"Product {i + 1}: either brand or site must be provided",
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
