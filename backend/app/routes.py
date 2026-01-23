from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import time
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    brand: Optional[str] = None
    category: Optional[str] = None
    barcode: Optional[str] = None
    price: Optional[str] = None
    quantity: Optional[str] = None


class BatchSearchRequestBody(BaseModel):
    products: List[BatchSearchRequest]  # All products are processed (no limit)
    max_workers: Optional[int] = 10  # Number of parallel workers (default: 10)


class BatchSearchResponse(BaseModel):
    product: Optional[Product] = None
    error: Optional[str] = None
    status: str  # "success" or "error"
    category: Optional[str] = None
    barcode: Optional[str] = None
    price: Optional[str] = None
    quantity: Optional[str] = None


def scrape_single_product(request: BatchSearchRequest) -> BatchSearchResponse:
    """
    Helper function to scrape a single product.
    Supports brand-based scraping with multiple sites.
    Preserves Excel values for category, barcode, price, and quantity.
    """
    # Determine which sites to try
    sites_to_try: list[str] = []
    
    if request.brand:
        # Get ordered list of sites for this brand
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
    else:
        return BatchSearchResponse(
            error="Brand must be provided",
            status="error",
            category=request.category,
            barcode=request.barcode,
            price=request.price,
            quantity=request.quantity,
        )
    
    # Determine query based on brand requirements
    # Liewood only searches by name, not by code
    is_liewood = (
        (request.brand and request.brand.lower() == "liewood") or
        (sites_to_try and sites_to_try[0].lower() == "liewood")
    )
    
    # Bambino/Widdop requires barcode for search
    is_bambino = (
        (request.brand and request.brand.lower() == "bambino") or
        (sites_to_try and sites_to_try[0].lower() == "widdop")
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
    elif is_bambino:
        # Bambino/Widdop requires barcode for search
        query = request.barcode or ""
        if not query:
            return BatchSearchResponse(
                error="Barcode must be provided for bambino brand",
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
            product = scraper.scrape_product(query, 0)
            
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
    error_msg = last_error or f"All sites failed for brand: {request.brand}"
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
    Search for multiple products in parallel.
    
    Args:
        body: Request body containing products list and configuration
    
    Returns:
        List of search results with status for each product
    """
    products = body.products
    if not products:
        raise HTTPException(status_code=400, detail="No products provided")

    # Validate all requests
    for i, req in enumerate(products):
        if not req.brand:
            raise HTTPException(
                status_code=400,
                detail=f"Product {i + 1}: brand must be provided",
            )
        # Check if this is liewood - requires name only
        is_liewood = req.brand and req.brand.lower() == "liewood"
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
    max_workers = body.max_workers if body.max_workers is not None else 10

    # Initialize results list with None values to maintain order
    results: List[Optional[BatchSearchResponse]] = [None] * len(products)

    # Process products in parallel
    def process_product(index: int, product: BatchSearchRequest) -> tuple[int, BatchSearchResponse]:
        """Process a single product and return its index and result."""
        try:
            result = scrape_single_product(product)
            return (index, result)
        except Exception as e:
            error_result = BatchSearchResponse(
                error=f"Unexpected error: {str(e)}", status="error"
            )
            return (index, error_result)

    # Use ThreadPoolExecutor to process products in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_index = {
            executor.submit(process_product, index, product): index
            for index, product in enumerate(products)
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_index):
            index, result = future.result()
            results[index] = result

    # Convert None values to error responses (shouldn't happen, but safety check)
    final_results: List[BatchSearchResponse] = []
    for result in results:
        if result is None:
            final_results.append(BatchSearchResponse(
                error="Processing failed", status="error"
            ))
        else:
            final_results.append(result)

    return final_results


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
    Processes products in parallel and updates job status incrementally.
    """
    job = job_store.get_job(job_id)
    if not job:
        return
    
    products = body.products
    max_workers = body.max_workers if body.max_workers is not None else 10
    
    job.update_status(JobStatus.IN_PROGRESS)
    
    try:
        def process_product(index: int, product: BatchSearchRequest):
            """Process a single product and add result to job store."""
            try:
                result = scrape_single_product(product)
                job.add_result(index, result)
            except Exception as e:
                error_result = BatchSearchResponse(
                    error=f"Unexpected error: {str(e)}", status="error"
                )
                job.add_result(index, error_result)
        
        # Use ThreadPoolExecutor to process products in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            futures = [
                executor.submit(process_product, index, product)
                for index, product in enumerate(products)
            ]
            
            # Wait for all tasks to complete
            for future in as_completed(futures):
                try:
                    future.result()  # This will raise any exceptions that occurred
                except Exception as e:
                    # Individual task exceptions are already handled in process_product
                    # This catch is for executor-level issues
                    pass
        
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
        if not req.brand:
            raise HTTPException(
                status_code=400,
                detail=f"Product {i + 1}: brand must be provided",
            )
        # Check if this is liewood - requires name only
        is_liewood = req.brand and req.brand.lower() == "liewood"
        # Check if this is bambino - requires barcode
        is_bambino = req.brand and req.brand.lower() == "bambino"
        
        if is_liewood:
            if not req.name:
                raise HTTPException(
                    status_code=400,
                    detail=f"Product {i + 1}: name must be provided for liewood brand",
                )
        elif is_bambino:
            if not req.barcode:
                raise HTTPException(
                    status_code=400,
                    detail=f"Product {i + 1}: barcode must be provided for bambino brand",
                )
        else:
            if not req.name and not req.code:
                raise HTTPException(
                    status_code=400,
                    detail=f"Product {i + 1}: either name or code must be provided",
                )
    
    # All products are processed in parallel using max_workers (no limit on number of products)
    
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
