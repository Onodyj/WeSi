#!/usr/bin/env python3
"""
SQLite database layer for WeSi API server.
Provides persistence for API keys, jobs, and audit logs.
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager


# Database configuration
DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "wesi.db")
DB_PATH = os.environ.get("WEBSI_DB_PATH", DEFAULT_DB_PATH)


@contextmanager
def get_connection():
    """
    Context manager for database connections.
    Provides thread-safe connection handling with automatic commit/rollback.
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """
    Initialize the database with required tables.
    Creates api_keys, jobs, and audit_logs tables if they don't exist.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # API keys table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                key TEXT PRIMARY KEY,
                owner TEXT NOT NULL,
                created_at TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            )
        """)
        
        # Jobs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                api_key TEXT NOT NULL,
                url TEXT NOT NULL,
                max_pages INTEGER NOT NULL,
                delay REAL NOT NULL DEFAULT 0.5,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                finished_at TEXT,
                report_path TEXT,
                error TEXT,
                FOREIGN KEY (api_key) REFERENCES api_keys(key)
            )
        """)
        
        # Audit logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_key TEXT NOT NULL,
                action TEXT NOT NULL,
                url TEXT,
                status TEXT,
                message TEXT,
                timestamp TEXT NOT NULL
            )
        """)
        
        conn.commit()


def add_api_key(key: str, owner: str) -> bool:
    """
    Add a new API key to the database.
    
    Args:
        key: The API key string
        owner: Owner/name of the API key holder
        
    Returns:
        True if successful, False if key already exists
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            created_at = datetime.utcnow().isoformat()
            cursor.execute(
                "INSERT INTO api_keys (key, owner, created_at, active) VALUES (?, ?, ?, 1)",
                (key, owner, created_at)
            )
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        return False


def get_api_key(key: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve an API key from the database.
    
    Args:
        key: The API key to look up
        
    Returns:
        Dictionary with key info if found and active, None otherwise
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM api_keys WHERE key = ? AND active = 1",
            (key,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def list_api_keys() -> List[Dict[str, Any]]:
    """
    List all API keys in the database.
    
    Returns:
        List of dictionaries containing API key information
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM api_keys ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def create_job(
    job_id: str,
    api_key: str,
    url: str,
    max_pages: int,
    delay: float = 0.5
) -> bool:
    """
    Create a new job in the database.
    
    Args:
        job_id: Unique job identifier
        api_key: API key of the job creator
        url: URL to analyze
        max_pages: Maximum pages to crawl
        delay: Delay between requests in seconds
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            created_at = datetime.utcnow().isoformat()
            cursor.execute(
                """INSERT INTO jobs 
                   (job_id, api_key, url, max_pages, delay, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (job_id, api_key, url, max_pages, delay, "pending", created_at)
            )
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        return False


def update_job_status(
    job_id: str,
    status: str,
    report_path: Optional[str] = None,
    error: Optional[str] = None
) -> bool:
    """
    Update the status of a job.
    
    Args:
        job_id: Job identifier
        status: New status (pending, running, completed, failed)
        report_path: Path to the generated report (for completed jobs)
        error: Error message (for failed jobs)
        
    Returns:
        True if successful, False if job not found
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        finished_at = datetime.utcnow().isoformat() if status in ("completed", "failed") else None
        
        cursor.execute(
            """UPDATE jobs 
               SET status = ?, finished_at = ?, report_path = ?, error = ?
               WHERE job_id = ?""",
            (status, finished_at, report_path, error, job_id)
        )
        conn.commit()
        return cursor.rowcount > 0


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get job information by ID.
    
    Args:
        job_id: Job identifier
        
    Returns:
        Dictionary with job info if found, None otherwise
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def list_jobs(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """
    List jobs with pagination.
    
    Args:
        limit: Maximum number of jobs to return
        offset: Number of jobs to skip
        
    Returns:
        List of job dictionaries
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def log_audit(
    api_key: str,
    action: str,
    url: Optional[str] = None,
    status: Optional[str] = None,
    message: Optional[str] = None
) -> None:
    """
    Log an audit event.
    
    Args:
        api_key: API key that performed the action
        action: Action type (e.g., 'analyze', 'check_status')
        url: URL being analyzed (if applicable)
        status: Status of the action
        message: Additional message
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        timestamp = datetime.utcnow().isoformat()
        cursor.execute(
            """INSERT INTO audit_logs 
               (api_key, action, url, status, message, timestamp)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (api_key, action, url, status, message, timestamp)
        )
        conn.commit()
