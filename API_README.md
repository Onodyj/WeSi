# WeSi API Server

API server for asynchronous website analysis with API key authentication.

## Features

- **API Key Authentication**: Secure access with API keys
- **Asynchronous Job Processing**: Submit analysis jobs and check status later
- **SQLite Persistence**: Jobs, API keys, and audit logs stored in SQLite database
- **Background Worker**: Automatic processing of pending jobs
- **RESTful API**: Clean, documented endpoints

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Initialize and Create an API Key

```bash
# Create an API key
python scripts/add_api_key.py --key "my-secret-key-123" --owner "Your Name"

# List all API keys
python scripts/add_api_key.py --list
```

### 3. Start the API Server

```bash
# Start the server
python api/server.py

# Or specify host and port
python api/server.py --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000` with interactive documentation at `http://localhost:8000/docs`.

## API Endpoints

### POST /analyze

Submit a website for analysis.

**Headers:**
- `X-API-Key`: Your API key

**Request Body:**
```json
{
  "url": "https://example.com",
  "max_pages": 50,
  "delay": 0.5
}
```

**Response:**
```json
{
  "job_id": "uuid-here",
  "status": "pending",
  "message": "Analysis job submitted successfully"
}
```

### GET /jobs/{job_id}

Get the status of a specific job.

**Headers:**
- `X-API-Key`: Your API key

**Response:**
```json
{
  "job_id": "uuid-here",
  "api_key": "your-key",
  "url": "https://example.com",
  "max_pages": 50,
  "delay": 0.5,
  "status": "completed",
  "created_at": "2024-01-01T12:00:00",
  "finished_at": "2024-01-01T12:05:00",
  "report_path": "/path/to/report.json",
  "error": null
}
```

### GET /jobs

List all jobs for your API key.

**Headers:**
- `X-API-Key`: Your API key

**Query Parameters:**
- `limit` (optional): Maximum number of jobs to return (default: 100, max: 500)
- `offset` (optional): Number of jobs to skip (default: 0)

**Response:**
```json
[
  {
    "job_id": "uuid-1",
    "status": "completed",
    ...
  },
  {
    "job_id": "uuid-2",
    "status": "running",
    ...
  }
]
```

## Job Statuses

- **pending**: Job is waiting to be processed
- **running**: Job is currently being processed
- **completed**: Job finished successfully, report is available
- **failed**: Job failed, check the error field

## Example Usage

### Using curl

```bash
# Submit a job
curl -X POST "http://localhost:8000/analyze" \
  -H "X-API-Key: my-secret-key-123" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "max_pages": 10}'

# Check job status
curl -X GET "http://localhost:8000/jobs/{job_id}" \
  -H "X-API-Key: my-secret-key-123"

# List all jobs
curl -X GET "http://localhost:8000/jobs" \
  -H "X-API-Key: my-secret-key-123"
```

### Using Python

```python
import requests
import time

API_KEY = "my-secret-key-123"
BASE_URL = "http://localhost:8000"

# Submit analysis job
response = requests.post(
    f"{BASE_URL}/analyze",
    headers={"X-API-Key": API_KEY},
    json={
        "url": "https://example.com",
        "max_pages": 10,
        "delay": 0.5
    }
)
job = response.json()
job_id = job["job_id"]
print(f"Job submitted: {job_id}")

# Poll for completion
while True:
    response = requests.get(
        f"{BASE_URL}/jobs/{job_id}",
        headers={"X-API-Key": API_KEY}
    )
    job_status = response.json()
    
    print(f"Status: {job_status['status']}")
    
    if job_status["status"] in ["completed", "failed"]:
        break
    
    time.sleep(5)

# Get report if completed
if job_status["status"] == "completed":
    print(f"Report saved to: {job_status['report_path']}")
else:
    print(f"Job failed: {job_status['error']}")
```

## Database

The API uses SQLite for persistence with the following tables:

- **api_keys**: Stores API keys and owner information
- **jobs**: Stores analysis jobs and their status
- **audit_logs**: Logs all API actions for auditing

Database location can be configured with the `WESI_DB_PATH` environment variable (defaults to `data/wesi.db`).

## Configuration

Set environment variables in a `.env` file or export them:

```bash
# Database path
export WESI_DB_PATH=/path/to/custom/wesi.db

# Server settings (used by server.py arguments)
export WESI_HOST=0.0.0.0
export WESI_PORT=8000
```

## Security Notes

- API keys are stored in plain text in the database
- Use HTTPS in production to protect API keys in transit
- Regularly rotate API keys
- Monitor audit logs for suspicious activity
- Consider rate limiting for production use

## Development

### Running in Development Mode

```bash
# Install development dependencies
pip install -r requirements.txt

# Run with auto-reload
uvicorn api.server:app --reload --host 0.0.0.0 --port 8000
```

### API Documentation

Interactive API documentation is automatically generated and available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
