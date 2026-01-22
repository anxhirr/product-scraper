from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import threading
import uuid
from scraper.registry import get_scraper, get_available_sites, get_sites_for_brand, get_available_brands
from scraper.models import Product
from app.job_store import job_store, JobStatus

router = APIRouter()


@router.get("/search/{site}/{query}", response_model=Product)
def search(site: str, query: str):
    """
    Search for a product on the specified website.
    
    Args:
        site: Website identifier (e.g., "hape", "liewood")
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
    quantity: Optional[str] = None


class BatchSearchRequestBody(BaseModel):
    products: List[BatchSearchRequest]
    batch_size: int = 200
    batch_delay: int = 1000  # milliseconds
    navigation_delay: int = 500  # milliseconds


class BatchSearchResponse(BaseModel):
    product: Optional[Product] = None
    error: Optional[str] = None
    status: str  # "success" or "error"
    category: Optional[str] = None
    barcode: Optional[str] = None
    price: Optional[str] = None
    quantity: Optional[str] = None


def scrape_single_product(request: BatchSearchRequest, navigation_delay: float = 0) -> BatchSearchResponse:
    """
    Helper function to scrape a single product, used in thread pool.
    Supports brand-based scraping with fallback to multiple sites.
    Preserves Excel values for category, barcode, price, and quantity.
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
                quantity=request.quantity,
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
            quantity=request.quantity,
        )
    
    # Determine query based on brand/site requirements
    # Liewood only searches by name, not by code
    is_liewood = (
        (request.brand and request.brand.lower() == "liewood") or
        (request.site and request.site.lower() == "liewood") or
        (sites_to_try and sites_to_try[0].lower() == "liewood")
    )
    
    if is_liewood:
        query = request.name or ""
        if not query:
            return BatchSearchResponse(
                error="Name must be provided for liewood brand",
                status="error",
                category=request.category,
                barcode=request.barcode,
                price=request.price,
                quantity=request.quantity,
            )
    else:
        # Use code if provided, otherwise use name
        query = request.code if request.code else (request.name or "")
        if not query:
            return BatchSearchResponse(
                error="Either name or code must be provided",
                status="error",
                category=request.category,
                barcode=request.barcode,
                price=request.price,
                quantity=request.quantity,
            )
    
    # Try each site in order until one succeeds
    last_error: Optional[str] = None
    for site in sites_to_try:
        try:
            scraper = get_scraper(site)
            product = scraper.scrape_product(query, navigation_delay)
            
            # SKU validation for LieWood brand
            if is_liewood and request.code:
                excel_sku = request.code.strip()
                extracted_sku = product.sku.strip() if product.sku else ""
                
                if not excel_sku or not extracted_sku:
                    return BatchSearchResponse(
                        error=f"SKU validation failed: missing SKU data (Excel: '{excel_sku}', Extracted: '{extracted_sku}')",
                        status="error",
                        category=request.category,
                        barcode=request.barcode,
                        price=request.price,
                        quantity=request.quantity,
                    )
                
                # Case-insensitive check: extracted SKU should contain Excel SKU
                if excel_sku.lower() not in extracted_sku.lower():
                    return BatchSearchResponse(
                        error=f"SKU validation failed: extracted SKU '{extracted_sku}' does not contain Excel SKU '{excel_sku}'",
                        status="error",
                        category=request.category,
                        barcode=request.barcode,
                        price=request.price,
                        quantity=request.quantity,
                    )
            
            return BatchSearchResponse(
                product=product,
                status="success",
                category=request.category,
                barcode=request.barcode,
                price=request.price,
                quantity=request.quantity,
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
        quantity=request.quantity,
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
        # Check if this is liewood - requires name only
        is_liewood = (
            (req.brand and req.brand.lower() == "liewood") or
            (req.site and req.site.lower() == "liewood")
        )
        if is_liewood:
            if not req.name:
                raise HTTPException(
                    status_code=400,
                    detail=f"Product {i + 1}: name must be provided for liewood brand",
                )
        else:
            if not req.name and not req.code:
                raise HTTPException(
                    status_code=400,
                    detail=f"Product {i + 1}: either name or code must be provided",
                )

    # Use provided config or defaults
    batch_size = body.batch_size
    batch_delay = body.batch_delay / 1000.0  # Convert to seconds
    navigation_delay = body.navigation_delay / 1000.0  # Convert to seconds

    # Validate batch size
    if batch_size < 1 or batch_size > 500:
        raise HTTPException(
            status_code=400, detail="Batch size must be between 1 and 500"
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
                executor.submit(scrape_single_product, product, navigation_delay): i
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


class JobResponse(BaseModel):
    job_id: str


class JobStatusResponse(BaseModel):
    status: str
    results: List[Optional[BatchSearchResponse]]
    progress: int
    error: Optional[str] = None
    total_products: int
    original_products: Optional[List[dict]] = None


def process_job_async(job_id: str, body: BatchSearchRequestBody):
    """
    Process a scraping job asynchronously in a background thread.
    Updates job status and results incrementally.
    """
    job = job_store.get_job(job_id)
    if not job:
        return
    
    products = body.products
    batch_size = body.batch_size
    batch_delay = body.batch_delay / 1000.0  # Convert to seconds
    navigation_delay = body.navigation_delay / 1000.0  # Convert to seconds
    
    job.update_status(JobStatus.IN_PROGRESS)
    
    try:
        # Process products in batches
        for batch_start in range(0, len(products), batch_size):
            batch_end = min(batch_start + batch_size, len(products))
            batch = products[batch_start:batch_end]
            
            # Process batch in parallel using ThreadPoolExecutor
            batch_results: List[BatchSearchResponse] = [None] * len(batch)  # type: ignore
            
            with ThreadPoolExecutor(max_workers=batch_size) as executor:
                # Submit all tasks in the batch
                future_to_index = {
                    executor.submit(scrape_single_product, product, navigation_delay): i
                    for i, product in enumerate(batch)
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_index):
                    index = future_to_index[future]
                    global_index = batch_start + index
                    try:
                        result = future.result()
                        batch_results[index] = result
                        # Update job with result as it completes
                        job.add_result(global_index, result)
                    except Exception as e:
                        error_result = BatchSearchResponse(
                            error=f"Unexpected error: {str(e)}", status="error"
                        )
                        batch_results[index] = error_result
                        job.add_result(global_index, error_result)
            
            # Add delay between batches (except after the last batch)
            if batch_end < len(products):
                time.sleep(batch_delay)
        
        # Mark job as completed
        job.update_status(JobStatus.COMPLETED)
    except Exception as e:
        # Mark job as failed
        job.update_status(JobStatus.FAILED, error=str(e))


@router.post("/jobs", response_model=JobResponse)
def create_job(body: BatchSearchRequestBody):
    """
    Create an async scraping job.
    
    Args:
        body: Request body containing products list and batch configuration
    
    Returns:
        Job ID for polling status
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
        # Check if this is liewood - requires name only
        is_liewood = (
            (req.brand and req.brand.lower() == "liewood") or
            (req.site and req.site.lower() == "liewood")
        )
        if is_liewood:
            if not req.name:
                raise HTTPException(
                    status_code=400,
                    detail=f"Product {i + 1}: name must be provided for liewood brand",
                )
        else:
            if not req.name and not req.code:
                raise HTTPException(
                    status_code=400,
                    detail=f"Product {i + 1}: either name or code must be provided",
                )
    
    # Validate batch size
    if body.batch_size < 1 or body.batch_size > 500:
        raise HTTPException(
            status_code=400, detail="Batch size must be between 1 and 500"
        )
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Store original products for reference
    original_products = [p.dict() for p in products]
    
    # Create job
    job = job_store.create_job(job_id, len(products), original_products)
    
    # Start background thread to process job
    thread = threading.Thread(target=process_job_async, args=(job_id, body))
    thread.daemon = True
    thread.start()
    
    return JobResponse(job_id=job_id)


@router.get("/jobs/{job_id}/status", response_model=JobStatusResponse)
def get_job_status(job_id: str):
    """
    Get the status and results of a scraping job.
    
    Args:
        job_id: The job ID returned from POST /jobs
    
    Returns:
        Job status, results (partial or complete), and progress
    """
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatusResponse(
        status=job.status,
        results=job.results,
        progress=job.get_progress(),
        error=job.error,
        total_products=job.total_products,
        original_products=job.original_products,
    )
