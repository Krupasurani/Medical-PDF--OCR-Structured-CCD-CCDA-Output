#!/bin/bash

# Medical PDF to CCD/CCDA Converter - Setup Script
# Automated installation for any system (Linux/macOS/Windows WSL)

set -e  # Exit on error

echo "=================================================="
echo "Medical PDF → CCD/CCDA Converter Setup"
echo "=================================================="
echo ""

# Detect OS
OS="$(uname -s)"
case "${OS}" in
    Linux*)     MACHINE=Linux;;
    Darwin*)    MACHINE=Mac;;
    MINGW*|MSYS*|CYGWIN*)     MACHINE=Windows;;
    *)          MACHINE="UNKNOWN"
esac

echo "Detected OS: ${MACHINE}"
echo ""

# Check Python installation
echo "[1/6] Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    echo "Please install Python 3.9 or higher from https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d ' ' -f 2)
echo "✅ Found Python ${PYTHON_VERSION}"
echo ""

# Check pip
echo "[2/6] Checking pip installation..."
if ! command -v pip3 &> /dev/null; then
    echo "Installing pip..."
    python3 -m ensurepip --upgrade
fi
echo "✅ pip is available"
echo ""

# Create virtual environment
echo "[3/6] Creating virtual environment..."
if [ -d "venv" ]; then
    echo "⚠️  Virtual environment already exists, removing..."
    rm -rf venv
fi
python3 -m venv venv
echo "✅ Virtual environment created"
echo ""

# Activate virtual environment
echo "[4/6] Activating virtual environment..."
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null || . venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Install dependencies
echo "[5/6] Installing dependencies..."
echo "This may take a few minutes..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ All dependencies installed"
echo ""

# Create .env file if it doesn't exist
echo "[6/6] Configuring environment..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ Created .env file from template"
        echo ""
        echo "⚠️  IMPORTANT: Edit .env and add your Gemini API key:"
        echo "    GEMINI_API_KEY=your-api-key-here"
        echo ""
        echo "Get your API key from: https://makersuite.google.com/app/apikey"
    else
        echo "❌ .env.example not found"
        exit 1
    fi
else
    echo "✅ .env file already exists"
fi
echo ""

echo "=================================================="
echo "✅ Setup completed successfully!"
echo "=================================================="
echo ""
echo "Next steps:"
echo "1. Edit .env and add your Gemini API key"
echo "2. Run the application with: ./run.sh"
echo ""
