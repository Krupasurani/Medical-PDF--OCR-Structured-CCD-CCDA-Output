#!/bin/bash

# Medical PDF to CCD/CCDA Converter - Run Script
# Easy execution script for the Streamlit application

set -e  # Exit on error

echo "=================================================="
echo "Medical PDF → CCD/CCDA Converter"
echo "=================================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found"
    echo "Please run ./setup.sh first"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null || . venv/bin/activate

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found"
    echo "Please copy .env.example to .env and add your Gemini API key"
    exit 1
fi

# Check if API key is configured
if ! grep -q "GEMINI_API_KEY=AIza" .env 2>/dev/null && ! grep -q "GEMINI_API_KEY=\"AIza" .env 2>/dev/null; then
    echo "⚠️  Warning: Gemini API key may not be configured in .env"
    echo "Make sure to add: GEMINI_API_KEY=your-api-key-here"
    echo ""
fi

# Run the application
echo "Starting application..."
echo "The web interface will open in your browser"
echo "Press Ctrl+C to stop the application"
echo ""
echo "=================================================="
echo ""

streamlit run app.py
