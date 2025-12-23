# Setup Guide

Detailed installation and configuration instructions for the Medical PDF → CCD/CCDA Converter.

## Table of Contents

- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

## System Requirements

### Operating System

- **Linux**: Ubuntu 20.04+, Debian 11+, or equivalent
- **macOS**: 10.15 (Catalina) or newer
- **Windows**: Windows 10 or Windows 11 (with WSL recommended)

### Software Prerequisites

1. **Python 3.9+**
   - Download from: https://www.python.org/downloads/
   - Verify installation: `python3 --version`

2. **pip** (Python package manager)
   - Usually included with Python
   - Verify: `pip3 --version`

3. **Internet Connection**
   - Required for API access during processing
   - Recommended: High-speed broadband

### Hardware Requirements

**Minimum:**
- CPU: Dual-core processor
- RAM: 4 GB
- Disk: 2 GB free space

**Recommended:**
- CPU: Quad-core or better
- RAM: 8 GB or more
- Disk: 5 GB free space

## Installation

### Step 1: Download & Extract

Extract the application files to your desired location:

\`\`\`bash
cd /path/to/desired/location
# Files should be in a directory called "final_system"
\`\`\`

### Step 2: Run Automated Setup

The setup script handles all installation steps automatically.

**Linux/macOS:**
\`\`\`bash
cd final_system
chmod +x setup.sh  # Make executable (if needed)
./setup.sh
\`\`\`

**Windows (using Git Bash or WSL):**
\`\`\`bash
cd final_system
bash setup.sh
\`\`\`

The script will:
1. ✅ Check Python installation
2. ✅ Verify pip is available
3. ✅ Create isolated virtual environment
4. ✅ Install all dependencies
5. ✅ Create configuration template

### Step 3: Manual Installation (Alternative)

If the automated script fails, follow these manual steps:

**Create Virtual Environment:**
\`\`\`bash
python3 -m venv venv
\`\`\`

**Activate Virtual Environment:**

Linux/macOS:
\`\`\`bash
source venv/bin/activate
\`\`\`

Windows:
\`\`\`bash
venv\Scripts\activate
\`\`\`

**Install Dependencies:**
\`\`\`bash
pip install --upgrade pip
pip install -r requirements.txt
\`\`\`

## Configuration

### Step 1: Obtain Gemini API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the generated API key

### Step 2: Configure Environment

**Option A: Using Automated Setup**

If you ran \`./setup.sh\`, a \`.env\` file was created automatically.

Edit \`.env\`:
\`\`\`bash
nano .env  # or use any text editor
\`\`\`

**Option B: Manual Setup**

Copy the example file:
\`\`\`bash
cp .env.example .env
\`\`\`

Edit \`.env\`:
\`\`\`bash
nano .env
\`\`\`

### Step 3: Add API Key

Edit the \`.env\` file and add your Gemini API key:

\`\`\`env
# Required: Google Gemini API Key
GEMINI_API_KEY=your-actual-api-key-here

# Optional: Model Configuration (defaults shown)
OCR_MODEL_NAME=gemini-3-pro-preview
STRUCTURING_MODEL_NAME=gemini-2.5-flash

# Optional: Processing Configuration
PDF_DPI=300
MAX_IMAGE_DIMENSION=4096
\`\`\`

**Save and close the file** (Ctrl+X, then Y, then Enter in nano)

## Verification

### Step 1: Test Installation

Activate the virtual environment (if not already active):

\`\`\`bash
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows
\`\`\`

Verify dependencies:
\`\`\`bash
pip list
\`\`\`

You should see packages including:
- streamlit
- google-generativeai
- Pillow
- pypdf
- python-docx
- reportlab

### Step 2: Test Configuration

Check if your API key is configured:

\`\`\`bash
cat .env | grep GEMINI_API_KEY
\`\`\`

Should show:
\`\`\`
GEMINI_API_KEY=AIza...
\`\`\`

### Step 3: Run Application

Start the application:

\`\`\`bash
./run.sh
\`\`\`

Or manually:
\`\`\`bash
streamlit run app.py
\`\`\`

The web interface should open at \`http://localhost:8501\`

If you see the upload interface, installation was successful!

## Troubleshooting

### Python Not Found

**Error:** \`python3: command not found\`

**Solution:**
1. Install Python 3.9+ from https://www.python.org/downloads/
2. On Windows, ensure "Add Python to PATH" was checked during installation
3. Restart your terminal/command prompt

### Virtual Environment Activation Fails

**Error:** \`venv/bin/activate: No such file or directory\`

**Solution:**
\`\`\`bash
# Re-create virtual environment
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
\`\`\`

### Dependency Installation Fails

**Error:** \`ERROR: Could not install packages...\`

**Solution:**
\`\`\`bash
# Upgrade pip first
pip install --upgrade pip setuptools wheel

# Try installing again
pip install -r requirements.txt
\`\`\`

### Permission Denied on Scripts

**Error:** \`Permission denied: ./setup.sh\`

**Solution:**
\`\`\`bash
chmod +x setup.sh run.sh
\`\`\`

### Application Won't Start

**Error:** \`ModuleNotFoundError: No module named 'streamlit'\`

**Solution:**
1. Ensure virtual environment is activated:
   \`\`\`bash
   source venv/bin/activate
   \`\`\`
2. Reinstall dependencies:
   \`\`\`bash
   pip install -r requirements.txt
   \`\`\`

### API Key Not Working

**Error:** \`API key not configured\` or \`Authentication failed\`

**Solution:**
1. Verify \`.env\` file exists in the \`final_system\` directory
2. Check API key format: Should start with \`AIza\`
3. Ensure no extra quotes or spaces:
   \`\`\`env
   GEMINI_API_KEY=AIzaSyD...
   \`\`\`
   NOT:
   \`\`\`env
   GEMINI_API_KEY="AIzaSyD..."  # Wrong - no quotes
   GEMINI_API_KEY= AIzaSyD...   # Wrong - no space
   \`\`\`
4. Generate a new API key if needed

### Port 8501 Already in Use

**Error:** \`Port 8501 is already in use\`

**Solution:**
\`\`\`bash
# Find and kill the process
lsof -ti:8501 | xargs kill -9  # Linux/macOS

# Or use a different port
streamlit run app.py --server.port=8502
\`\`\`

### PDF Processing Fails

**Error:** PDF uploads but processing fails

**Solution:**
1. Check PDF file size (must be under 200MB)
2. Ensure PDF is not password-protected
3. Try a different PDF file to isolate the issue
4. Check internet connection
5. Verify API key has sufficient quota

## Advanced Configuration

### Changing Models

Edit \`.env\` to use different Gemini models:

\`\`\`env
# Use different OCR model
OCR_MODEL_NAME=gemini-1.5-pro

# Use different structuring model
STRUCTURING_MODEL_NAME=gemini-1.5-flash
\`\`\`

### Adjusting PDF Processing

\`\`\`env
# Higher DPI for better quality (slower processing)
PDF_DPI=400

# Lower DPI for faster processing (lower quality)
PDF_DPI=200
\`\`\`

### Custom Output Directory

Outputs are automatically saved to timestamped folders in \`outputs/\`.

To change this, modify \`app.py\` (advanced users only).

## Next Steps

After successful setup:

1. **Test with Sample PDF**: Process a small medical document
2. **Review Outputs**: Check all generated files (XML, PDF, DOCX, JSON)
3. **Integrate with Workflow**: Connect outputs to your EHR or document management system

## Support

For additional help:
- Review [README.md](README.md) for usage instructions
- Check [ARCHITECTURE.md](ARCHITECTURE.md) for system design details
- Verify all prerequisites are installed correctly
