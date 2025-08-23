#!/bin/bash

# Render.com Build Script for CI/CD Fixer Agent
# This script runs during the build phase on Render

echo "🚀 Building CI/CD Fixer Agent for production deployment..."

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating required directories..."
mkdir -p logs
mkdir -p temp

echo "✅ Build completed successfully!"
echo ""
echo "🔧 Required Environment Variables:"
echo "  - GITHUB_TOKEN"
echo "  - GITHUB_WEBHOOK_SECRET"
echo "  - GOOGLE_GENAI_API_KEY"
echo "  - PORTIA_API_KEY (optional)"
echo "  - PORTIA_PROJECT_ID (optional)"
echo "  - DATABASE_URL (PostgreSQL connection string)"
echo ""
echo "🌐 Your CI/CD Fixer Agent is ready for deployment!"
