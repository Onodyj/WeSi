#!/usr/bin/env python3
"""
FastAPI server for WeSi website analyzer.
Provides API endpoints for asynchronous website analysis with API key authentication.
"""

import os
import sys
import uuid
import threading
import time
from typing import Optional, List
from datetime import datetime

from fastapi import FastAPI, HTTPException, Security, Depends, Query
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field, HttpUrl
import uvicorn

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.db import (
    init_db, get_api_key, create_job, update_job_status,
    get_job, list_jobs, log_audit
)
from wesi import WebsiteAnalyzer


# Initialize FastAPI app
app = FastAPI(
    title="WeSi API",
    description="API for asynchronous website analysis with API key authentication",
    version="1.0.0"
)


# API Key authentication
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Verify API key and return it if valid.
    
    Args:
        api_key: API key from request header
        
    Returns:
        The API key if valid
        
    Raises:
        HTTPException: If API key is missing or invalid
    """
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")
    
    key_info = get_api_key(api_key)
    if not key_info:
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    return api_key


# Request/Response models
class AnalyzeRequest(BaseModel):
    """Request model for website analysis."""
    url: HttpUrl = Field(..., description="URL of the website to analyze")
    max_pages: int = Field(default=50, ge=1, le=500, description="Maximum pages to crawl")
    delay: float = Field(default=0.5, ge=0.1, le=5.0, description="Delay between requests in seconds")


class JobResponse(BaseModel):
    """Response model for job information."""
    job_id: str
    api_key: str
    url: str
    max_pages: int
    delay: float
    status: str
    created_at: str
    finished_at: Optional[str] = None
    report_path: Optional[str] = None
    error: Optional[str] = None


class AnalyzeResponse(BaseModel):
    """Response model for analysis job submission."""
    job_id: str
    status: str
    message: str


# Background job worker
class JobWorker:
    """Background worker for processing analysis jobs."""
    
    def __init__(self):
        """Initialize the job worker."""
        self.running = False
        self.thread: Optional[threading.Thread] = None
    
    def start(self):
        """Start the background worker thread."""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop the background worker thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
    
    def _worker_loop(self):
        """Main worker loop that processes pending jobs."""
        while self.running:
            # Find pending jobs
            jobs = list_jobs(limit=100)
            pending_jobs = [j for j in jobs if j['status'] == 'pending']
            
            for job in pending_jobs:
                try:
                    self._process_job(job)
                except Exception as e:
                    print(f"Error processing job {job['job_id']}: {e}")
                    update_job_status(job['job_id'], 'failed', error=str(e))
                    log_audit(
                        job['api_key'],
                        'analyze',
                        job['url'],
                        'failed',
                        str(e)
                    )
            
            # Sleep before checking for more jobs
            time.sleep(2)
    
    def _process_job(self, job: dict):
        """
        Process a single job.
        
        Args:
            job: Job dictionary from database
        """
        job_id = job['job_id']
        
        # Update status to running
        update_job_status(job_id, 'running')
        log_audit(job['api_key'], 'analyze', job['url'], 'running', 'Job started')
        
        try:
            # Run the analyzer
            analyzer = WebsiteAnalyzer(
                job['url'],
                max_pages=job['max_pages'],
                timeout=10
            )
            
            # Crawl the website
            analyzer.crawl()
            
            # Generate and save report
            reports_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'reports'
            )
            os.makedirs(reports_dir, exist_ok=True)
            
            report_filename = f"report_{job_id}.json"
            report_path = os.path.join(reports_dir, report_filename)
            analyzer.save_report(report_path)
            
            # Update job status
            update_job_status(job_id, 'completed', report_path=report_path)
            log_audit(
                job['api_key'],
                'analyze',
                job['url'],
                'completed',
                f"Analyzed {len(analyzer.pages_data)} pages"
            )
            
        except Exception as e:
            # Update job status to failed
            error_msg = str(e)
            update_job_status(job_id, 'failed', error=error_msg)
            log_audit(job['api_key'], 'analyze', job['url'], 'failed', error_msg)
            raise


# Initialize worker
worker = JobWorker()


@app.on_event("startup")
async def startup_event():
    """Initialize database and start background worker on startup."""
    init_db()
    worker.start()


@app.on_event("shutdown")
async def shutdown_event():
    """Stop background worker on shutdown."""
    worker.stop()


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "WeSi API",
        "version": "1.0.0",
        "description": "API for asynchronous website analysis",
        "endpoints": {
            "POST /analyze": "Submit a website for analysis",
            "GET /jobs/{job_id}": "Get job status and results",
            "GET /jobs": "List all jobs"
        }
    }


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_website(
    request: AnalyzeRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Submit a website for asynchronous analysis.
    
    Args:
        request: Analysis request parameters
        api_key: Validated API key
        
    Returns:
        Job information including job_id for status tracking
    """
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    
    # Create job in database
    success = create_job(
        job_id=job_id,
        api_key=api_key,
        url=str(request.url),
        max_pages=request.max_pages,
        delay=request.delay
    )
    
    if not success:
        log_audit(api_key, 'analyze', str(request.url), 'failed', 'Failed to create job')
        raise HTTPException(status_code=500, detail="Failed to create job")
    
    log_audit(api_key, 'analyze', str(request.url), 'pending', 'Job created')
    
    return AnalyzeResponse(
        job_id=job_id,
        status="pending",
        message="Analysis job submitted successfully. Use job_id to check status."
    )


@app.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(
    job_id: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Get the status and results of a specific job.
    
    Args:
        job_id: Job identifier
        api_key: Validated API key
        
    Returns:
        Job information including status and report path if completed
    """
    job = get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Verify the job belongs to this API key
    if job['api_key'] != api_key:
        raise HTTPException(status_code=403, detail="Access denied")
    
    log_audit(api_key, 'check_status', job['url'], job['status'], f"Checked job {job_id}")
    
    return JobResponse(**job)


@app.get("/jobs", response_model=List[JobResponse])
async def list_all_jobs(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    api_key: str = Depends(verify_api_key)
):
    """
    List all jobs for the authenticated API key.
    
    Args:
        limit: Maximum number of jobs to return
        offset: Number of jobs to skip
        api_key: Validated API key
        
    Returns:
        List of jobs
    """
    all_jobs = list_jobs(limit=limit, offset=offset)
    
    # Filter jobs by API key
    user_jobs = [job for job in all_jobs if job['api_key'] == api_key]
    
    log_audit(api_key, 'list_jobs', None, 'success', f"Listed {len(user_jobs)} jobs")
    
    return [JobResponse(**job) for job in user_jobs]


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """
    Run the FastAPI server.
    
    Args:
        host: Host to bind to
        port: Port to bind to
    """
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="WeSi API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    
    args = parser.parse_args()
    
    print(f"Starting WeSi API server on {args.host}:{args.port}")
    print("API documentation available at http://localhost:8000/docs")
    
    run_server(host=args.host, port=args.port)
