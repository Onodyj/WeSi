#!/usr/bin/env python3
"""
SQLite database layer for WeSi API server.
Provides persistent storage for API keys, jobs, and audit logs.
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager


# Database configuration - can be overridden via environment variable
DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'wesi.db')
DB_PATH = os.environ.get('WESI_DB_PATH', DEFAULT_DB_PATH)


@contextmanager
def get_connection():
    """
    Context manager for database connections.
    Provides thread-safe connection handling with automatic commit/rollback.
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
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
    Creates tables for:
    - api_keys: Store API key credentials
    - jobs: Store analysis job records
    - audit_logs: Store audit trail of API operations
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        # API keys table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_keys (
                key TEXT PRIMARY KEY,
                owner TEXT NOT NULL,
                created_at TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            )
        ''')

        # Jobs table
        cursor.execute('''
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
        ''')

        # Audit logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_key TEXT NOT NULL,
                action TEXT NOT NULL,
                url TEXT,
                status TEXT,
                message TEXT,
                timestamp TEXT NOT NULL
            )
        ''')

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
                'INSERT INTO api_keys (key, owner, created_at, active) VALUES (?, ?, ?, 1)',
                (key, owner, created_at)
            )
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
            'SELECT key, owner, created_at, active FROM api_keys WHERE key = ?',
            (key,)
        )
        row = cursor.fetchone()
        if row and row['active']:
            return dict(row)
        return None


def deactivate_api_key(key: str) -> bool:
    """
    Deactivate an API key (soft delete).

    Args:
        key: The API key to deactivate

    Returns:
        True if successful, False if key not found
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE api_keys SET active = 0 WHERE key = ?', (key,))
        return cursor.rowcount > 0


def list_api_keys() -> List[Dict[str, Any]]:
    """
    List all active API keys in the database.

    Returns:
        List of dictionaries containing API key information
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT key, owner, created_at, active FROM api_keys WHERE active = 1 ORDER BY created_at DESC'
        )
        return [dict(row) for row in cursor.fetchall()]


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
        True if successful, False if job_id already exists
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            created_at = datetime.utcnow().isoformat()
            cursor.execute(
                '''INSERT INTO jobs
                   (job_id, api_key, url, max_pages, delay, status, created_at)
                   VALUES (?, ?, ?, ?, ?, 'pending', ?)''',
                (job_id, api_key, url, max_pages, delay, created_at)
            )
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
        status: New status ('pending', 'running', 'completed', 'failed')
        report_path: Path to the generated report (for completed jobs)
        error: Error message (for failed jobs)

    Returns:
        True if successful, False if job not found
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        finished_at = datetime.utcnow().isoformat() if status in ('completed', 'failed') else None
        cursor.execute(
            '''UPDATE jobs
               SET status = ?, finished_at = ?, report_path = ?, error = ?
               WHERE job_id = ?''',
            (status, finished_at, report_path, error, job_id)
        )
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
        cursor.execute(
            '''SELECT job_id, api_key, url, max_pages, delay, status,
                      created_at, finished_at, report_path, error
               FROM jobs WHERE job_id = ?''',
            (job_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def list_jobs(
    api_key: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    List jobs with optional filtering and pagination.

    Args:
        api_key: Filter by API key (optional)
        limit: Maximum number of jobs to return
        offset: Number of jobs to skip

    Returns:
        List of job dictionaries
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        if api_key:
            cursor.execute(
                '''SELECT job_id, api_key, url, max_pages, delay, status,
                          created_at, finished_at, report_path, error
                   FROM jobs WHERE api_key = ?
                   ORDER BY created_at DESC LIMIT ? OFFSET ?''',
                (api_key, limit, offset)
            )
        else:
            cursor.execute(
                '''SELECT job_id, api_key, url, max_pages, delay, status,
                          created_at, finished_at, report_path, error
                   FROM jobs
                   ORDER BY created_at DESC LIMIT ? OFFSET ?''',
                (limit, offset)
            )
        return [dict(row) for row in cursor.fetchall()]


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
            '''INSERT INTO audit_logs
               (api_key, action, url, status, message, timestamp)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (api_key, action, url, status, message, timestamp)
        )


# Initialize database on module import
try:
    init_db()
except Exception as e:
    import sys
    print(f"Warning: Failed to initialize database: {e}", file=sys.stderr)
    print(f"Database path: {DB_PATH}", file=sys.stderr)
