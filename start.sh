#!/bin/bash

# Render.com Run Script for CI/CD Fixer Agent
# This script starts the production server

echo "🌟 Starting CI/CD Fixer Agent production server..."

# Set production environment
export ENVIRONMENT=production

# Start the FastAPI server with Uvicorn
echo "🚀 Launching FastAPI server..."
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
