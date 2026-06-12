#!/bin/bash
# WeSi 2.0 Startup Script
# This script helps start all required services for WeSi

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}======================================"
echo "WeSi 2.0 Startup Script"
echo -e "======================================${NC}\n"

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found${NC}"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo -e "${RED}Please edit .env with your configuration before continuing!${NC}"
    exit 1
fi

# Check if Redis is installed
if ! command -v redis-server &> /dev/null; then
    echo -e "${RED}Error: Redis is not installed${NC}"
    echo "Install Redis with: sudo apt-get install redis-server (Ubuntu/Debian)"
    echo "Or: brew install redis (macOS)"
    exit 1
fi

# Check if Redis is running
if ! redis-cli ping &> /dev/null; then
    echo -e "${YELLOW}Redis is not running. Starting Redis...${NC}"
    redis-server --daemonize yes
    sleep 2
    if redis-cli ping &> /dev/null; then
        echo -e "${GREEN}✓ Redis started${NC}"
    else
        echo -e "${RED}Failed to start Redis${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ Redis is running${NC}"
fi

# Load environment variables
source .env

# Check required environment variables
if [ -z "$WESI_ENCRYPTION_KEY" ]; then
    echo -e "${RED}Error: WESI_ENCRYPTION_KEY not set in .env${NC}"
    echo "Generate a key with:"
    echo "  python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
    exit 1
fi

echo -e "${GREEN}✓ Environment configured${NC}"

# Initialize database if it doesn't exist
if [ ! -f wesi.db ]; then
    echo -e "${YELLOW}Initializing database...${NC}"
    python -c "from we_si.models import init_db; init_db()"
    echo -e "${GREEN}✓ Database initialized${NC}"
else
    echo -e "${GREEN}✓ Database exists${NC}"
fi

# Start services
echo -e "\n${GREEN}Starting WeSi services...${NC}\n"

# Start Celery worker in background
echo "Starting Celery worker..."
celery -A we_si.tasks worker --loglevel=info &
CELERY_PID=$!
echo -e "${GREEN}✓ Celery worker started (PID: $CELERY_PID)${NC}"

# Give Celery time to start
sleep 3

# Start Flask API
echo "Starting Flask API..."
echo -e "${GREEN}✓ Starting Flask on http://localhost:5000${NC}\n"

# Trap to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    kill $CELERY_PID 2>/dev/null || true
    echo -e "${GREEN}✓ Services stopped${NC}"
    exit 0
}
trap cleanup INT TERM

# Start Flask (foreground)
python we_si/api.py

# If Flask exits, cleanup
cleanup
