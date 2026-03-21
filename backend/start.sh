#!/bin/bash

# Default to 8000 if PORT is not set by the hosting provider
APP_PORT=${PORT:-8000}

echo "🚀 Starting FastAPI on port $APP_PORT"

# Run uvicorn
# --host 0.0.0.0 is CRITICAL for Docker/Cloud access
# --workers 2 helps handle multiple image processing requests
exec uvicorn main:app --host 0.0.0.0 --port "$APP_PORT" --workers 2