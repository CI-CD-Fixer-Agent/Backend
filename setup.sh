#!/bin/bash

# CI/CD Fixer Agent - Development Setup Script

echo "🚀 Setting up CI/CD Fixer Agent Backend..."

# Check if we're in the backend directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: Please run this script from the backend directory"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📥 Installing Python packages..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️ Please edit .env file with your API keys and configuration"
fi

# Initialize database
echo "🗃️ Initializing SQLite database..."
python3 -c "
from database import CICDFixerDB
db = CICDFixerDB()
print('✅ Database initialized successfully')
"

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Edit the .env file with your API keys:"
echo "   - GITHUB_TOKEN (for GitHub API access)"
echo "   - GOOGLE_API_KEY (for Gemini AI)"
echo "   - GITHUB_WEBHOOK_SECRET (optional, for webhook security)"
echo ""
echo "2. Start the development server:"
echo "   ./run.sh"
echo ""
echo "3. Test the API:"
echo "   curl http://localhost:8000/health"
echo ""
