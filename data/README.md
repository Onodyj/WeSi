# WeSi Database and API Key Management

This directory contains the SQLite-backed persistence layer for WeSi's API key and job management system.

## Overview

The database layer provides:
- **API Key Management**: Store and manage API keys for authentication
- **Job Tracking**: Track website analysis jobs with status and results
- **Audit Logging**: Maintain audit trail of all API operations

## Database Schema

### Tables

#### `api_keys`
Stores API key credentials for authentication.

| Column      | Type    | Description                          |
|-------------|---------|--------------------------------------|
| key         | TEXT    | API key (primary key)                |
| owner       | TEXT    | Owner/description of the key         |
| created_at  | TEXT    | ISO 8601 timestamp of creation       |
| active      | INTEGER | 1 if active, 0 if deactivated        |

#### `jobs`
Tracks website analysis jobs.

| Column       | Type    | Description                          |
|--------------|---------|--------------------------------------|
| job_id       | TEXT    | Unique job identifier (primary key)  |
| api_key      | TEXT    | API key that created the job         |
| url          | TEXT    | URL being analyzed                   |
| max_pages    | INTEGER | Maximum pages to crawl               |
| delay        | REAL    | Delay between requests (seconds)     |
| status       | TEXT    | Job status (pending/running/completed/failed) |
| created_at   | TEXT    | ISO 8601 timestamp of creation       |
| finished_at  | TEXT    | ISO 8601 timestamp of completion     |
| report_path  | TEXT    | Path to generated report (if completed) |
| error        | TEXT    | Error message (if failed)            |

#### `audit_logs`
Maintains audit trail of API operations.

| Column     | Type    | Description                          |
|------------|---------|--------------------------------------|
| id         | INTEGER | Auto-incrementing primary key        |
| api_key    | TEXT    | API key performing the action        |
| action     | TEXT    | Action type (e.g., 'create_job')     |
| url        | TEXT    | URL involved (if applicable)         |
| status     | TEXT    | Operation status                     |
| message    | TEXT    | Additional details                   |
| timestamp  | TEXT    | ISO 8601 timestamp                   |

## Database Functions

### API Key Management

```python
from data.db import add_api_key, get_api_key, deactivate_api_key, list_api_keys

# Add a new API key
add_api_key('my-secret-key', 'John Doe')

# Retrieve an API key
key_data = get_api_key('my-secret-key')
# Returns: {'key': '...', 'owner': 'John Doe', 'created_at': '...', 'active': 1}

# List all active API keys
keys = list_api_keys()

# Deactivate an API key (soft delete)
deactivate_api_key('my-secret-key')
```

### Job Management

```python
from data.db import create_job, get_job, update_job_status, list_jobs
import uuid

# Create a new job
job_id = str(uuid.uuid4())
create_job(job_id, 'my-secret-key', 'https://example.com', max_pages=10, delay=0.5)

# Retrieve a job
job = get_job(job_id)

# Update job status
update_job_status(job_id, 'running')
update_job_status(job_id, 'completed', report_path='/path/to/report.json')
update_job_status(job_id, 'failed', error='Connection timeout')

# List jobs for an API key
jobs = list_jobs(api_key='my-secret-key', limit=100)

# List all jobs
all_jobs = list_jobs(limit=100)
```

### Audit Logging

```python
from data.db import log_audit

# Log an API operation
log_audit(
    api_key='my-secret-key',
    action='create_job',
    url='https://example.com',
    status='success',
    message='Job created successfully'
)
```

## Database Configuration

The database location can be configured via environment variable:

```bash
# Use custom database path
export WESI_DB_PATH=/path/to/custom/wesi.db

# Use default path (repo_root/wesi.db)
unset WESI_DB_PATH
```

## Thread Safety

All database operations are thread-safe. The module uses:
- `check_same_thread=False` for SQLite connections
- Connection-per-operation pattern with context managers
- Automatic commit/rollback handling

## Error Handling

- Duplicate API keys return `False` instead of raising exceptions
- Duplicate jobs return `False` instead of raising exceptions
- Non-existent records return `None` or `False` as appropriate
- All database errors are properly rolled back

## Database Initialization

The database is automatically initialized when the module is imported. If initialization fails (e.g., permissions issue), a warning is printed to stderr but the module can still be imported.

You can also manually initialize:

```python
from data.db import init_db

init_db()  # Creates tables if they don't exist
```
