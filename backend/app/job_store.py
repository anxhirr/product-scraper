"""
Job storage system for async scraping jobs.
Thread-safe in-memory storage for job state and results.
"""
import threading
import time
from typing import Dict, Optional, List, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from app.routes import BatchSearchResponse


class JobStatus:
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Job:
    """Represents a scraping job with status and results."""
    
    def __init__(self, job_id: str, total_products: int, original_products: Optional[List[dict]] = None):
        self.job_id = job_id
        self.status = JobStatus.PENDING
        self.results: List[Optional["BatchSearchResponse"]] = []
        self.error: Optional[str] = None
        self.created_at = time.time()
        self.updated_at = time.time()
        self.total_products = total_products
        self.original_products = original_products or []
    
    def update_status(self, status: str, error: Optional[str] = None):
        """Update job status and timestamp."""
        self.status = status
        self.updated_at = time.time()
        if error:
            self.error = error
    
    def add_result(self, index: int, result: "BatchSearchResponse"):
        """Add or update a result at a specific index."""
        # Ensure results list is large enough
        while len(self.results) <= index:
            self.results.append(None)
        self.results[index] = result
        self.updated_at = time.time()
    
    def get_progress(self) -> int:
        """Calculate progress percentage based on completed results."""
        if self.total_products == 0:
            return 100
        
        completed = sum(1 for r in self.results if r is not None)
        return int((completed / self.total_products) * 100)
    
    def to_dict(self) -> dict:
        """Convert job to dictionary for API response."""
        return {
            "job_id": self.job_id,
            "status": self.status,
            "results": [r.dict() if r else None for r in self.results],
            "progress": self.get_progress(),
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "total_products": self.total_products,
            "original_products": self.original_products,
        }


class JobStore:
    """Thread-safe job storage."""
    
    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()
    
    def create_job(self, job_id: str, total_products: int, original_products: Optional[List[dict]] = None) -> Job:
        """Create a new job and return it."""
        with self._lock:
            job = Job(job_id, total_products, original_products)
            self._jobs[job_id] = job
            return job
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID."""
        with self._lock:
            return self._jobs.get(job_id)
    
    def delete_job(self, job_id: str) -> bool:
        """Delete a job by ID. Returns True if deleted, False if not found."""
        with self._lock:
            if job_id in self._jobs:
                del self._jobs[job_id]
                return True
            return False
    
    def cleanup_old_jobs(self, max_age_seconds: int = 3600):
        """Remove jobs older than max_age_seconds (default 1 hour)."""
        current_time = time.time()
        with self._lock:
            jobs_to_delete = [
                job_id for job_id, job in self._jobs.items()
                if current_time - job.updated_at > max_age_seconds
            ]
            for job_id in jobs_to_delete:
                del self._jobs[job_id]
            return len(jobs_to_delete)


# Global job store instance
job_store = JobStore()
