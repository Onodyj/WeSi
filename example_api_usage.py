#!/usr/bin/env python3
"""
Example script demonstrating the WeSi API usage.
This script shows how to:
1. Submit an analysis job
2. Poll for job completion
3. Retrieve the results
"""

import requests
import time
import sys

# Configuration
API_KEY = "test-key-123"  # Replace with your API key
BASE_URL = "http://localhost:8000"


def submit_analysis(url: str, max_pages: int = 10):
    """Submit a website for analysis."""
    print(f"\n{'='*60}")
    print(f"Submitting analysis job for: {url}")
    print(f"{'='*60}")
    
    response = requests.post(
        f"{BASE_URL}/analyze",
        headers={"X-API-Key": API_KEY},
        json={
            "url": url,
            "max_pages": max_pages,
            "delay": 0.5
        }
    )
    
    if response.status_code != 200:
        print(f"Error: {response.json()}")
        sys.exit(1)
    
    job = response.json()
    print(f"✅ Job submitted successfully!")
    print(f"   Job ID: {job['job_id']}")
    print(f"   Status: {job['status']}")
    
    return job['job_id']


def check_job_status(job_id: str):
    """Check the status of a job."""
    response = requests.get(
        f"{BASE_URL}/jobs/{job_id}",
        headers={"X-API-Key": API_KEY}
    )
    
    if response.status_code != 200:
        print(f"Error: {response.json()}")
        sys.exit(1)
    
    return response.json()


def wait_for_completion(job_id: str, poll_interval: int = 3):
    """Wait for a job to complete."""
    print(f"\n{'='*60}")
    print(f"Waiting for job completion...")
    print(f"{'='*60}")
    
    while True:
        job_status = check_job_status(job_id)
        status = job_status['status']
        
        print(f"Status: {status}", end="\r")
        
        if status == "completed":
            print(f"\n✅ Job completed successfully!")
            print(f"   Report path: {job_status['report_path']}")
            return job_status
        elif status == "failed":
            print(f"\n❌ Job failed!")
            print(f"   Error: {job_status['error']}")
            sys.exit(1)
        
        time.sleep(poll_interval)


def list_jobs():
    """List all jobs for the current API key."""
    print(f"\n{'='*60}")
    print(f"Listing all jobs")
    print(f"{'='*60}")
    
    response = requests.get(
        f"{BASE_URL}/jobs",
        headers={"X-API-Key": API_KEY}
    )
    
    if response.status_code != 200:
        print(f"Error: {response.json()}")
        sys.exit(1)
    
    jobs = response.json()
    print(f"Found {len(jobs)} job(s):\n")
    
    for job in jobs:
        print(f"Job ID: {job['job_id']}")
        print(f"  URL: {job['url']}")
        print(f"  Status: {job['status']}")
        print(f"  Created: {job['created_at']}")
        if job['finished_at']:
            print(f"  Finished: {job['finished_at']}")
        if job['report_path']:
            print(f"  Report: {job['report_path']}")
        print()


def main():
    """Main function."""
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Connected to {response.json()['name']} v{response.json()['version']}")
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to API server at {BASE_URL}")
        print("Please start the server first:")
        print("  python api/server.py")
        sys.exit(1)
    
    # Submit analysis job
    url = "https://example.com"
    if len(sys.argv) > 1:
        url = sys.argv[1]
    
    max_pages = 5
    if len(sys.argv) > 2:
        max_pages = int(sys.argv[2])
    
    job_id = submit_analysis(url, max_pages)
    
    # Wait for completion
    result = wait_for_completion(job_id)
    
    # List all jobs
    list_jobs()
    
    print(f"\n{'='*60}")
    print(f"Example completed successfully!")
    print(f"{'='*60}")
    print(f"\nYou can now view the report at:")
    print(f"  {result['report_path']}")


if __name__ == "__main__":
    main()
