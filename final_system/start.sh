#!/bin/bash
# Medical PDF OCR to CCD/CCDA - Startup Script (Linux/Mac)

echo "🏥 Medical PDF → CCD/CCDA Converter"
echo "===================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "   Creating from .env.example..."
    cp .env.example .env
    echo "   ✅ Please edit .env and add your GEMINI_API_KEY"
    echo ""
    read -p "Press Enter to continue or Ctrl+C to exit..."
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies if needed
if [ ! -f "venv/installed" ]; then
    echo "📥 Installing dependencies..."
    pip install -r requirements.txt
    touch venv/installed
fi

# Create necessary directories
mkdir -p uploads outputs

# Start the application
echo ""
echo "🚀 Starting Medical PDF Converter..."
echo "   URL: http://localhost:8501"
echo ""
echo "   Press Ctrl+C to stop"
echo ""

streamlit run app.py
