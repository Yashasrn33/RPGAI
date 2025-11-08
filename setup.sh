#!/bin/bash

# ============================================================================
# RPGAI Setup Script
# Quick setup for the backend server
# ============================================================================

set -e  # Exit on error

echo "🚀 RPGAI Backend Setup"
echo "====================="
echo ""

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "   Found Python $python_version"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo ""
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "   ✓ Virtual environment created"
else
    echo ""
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo ""
echo "📚 Installing dependencies..."
pip install --upgrade pip
pip install -r server/requirements.txt
echo "   ✓ Dependencies installed"

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo ""
    echo "⚙️  Creating .env file..."
    cat > .env << 'EOF'
# Gemini API Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Google Cloud TTS Configuration
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/gcp-credentials.json

# Server Configuration
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# Database
DB_PATH=npc_memory.db

# Media Storage
MEDIA_DIR=./media
MEDIA_BASE_URL=http://localhost:8000/media

# Model Parameters
TEMPERATURE=0.7
TOP_P=0.9
MAX_OUTPUT_TOKENS=220
EOF
    echo "   ✓ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your API keys:"
    echo "   - GEMINI_API_KEY (get from https://ai.google.dev/)"
    echo "   - GOOGLE_APPLICATION_CREDENTIALS (path to GCP JSON key)"
else
    echo ""
    echo "✓ .env file already exists"
fi

# Create media directory
echo ""
echo "📁 Creating media directory..."
mkdir -p media
echo "   ✓ Media directory created"

# Run tests
echo ""
echo "🧪 Running tests..."
pytest tests/ -v --tb=short || echo "⚠️  Some tests may fail without API keys configured"

echo ""
echo "============================================"
echo "✅ Setup complete!"
echo "============================================"
echo ""
echo "Next steps:"
echo "1. Edit .env and add your API keys"
echo "2. Run the server:"
echo "   $ source venv/bin/activate"
echo "   $ uvicorn server.main:app --reload --port 8000"
echo ""
echo "3. Test the server:"
echo "   $ curl http://localhost:8000/healthz"
echo ""
echo "📖 Full documentation: ./README.md"
echo ""

