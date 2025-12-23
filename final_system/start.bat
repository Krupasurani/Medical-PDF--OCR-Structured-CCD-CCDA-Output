@echo off
REM Medical PDF OCR to CCD/CCDA - Startup Script (Windows)

echo.
echo =======================================
echo Medical PDF to CCD/CCDA Converter
echo =======================================
echo.

REM Check if .env exists
if not exist .env (
    echo Warning: .env file not found!
    echo Creating from .env.example...
    copy .env.example .env
    echo.
    echo Please edit .env and add your GEMINI_API_KEY
    echo.
    pause
)

REM Check if virtual environment exists
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies if needed
if not exist venv\installed (
    echo Installing dependencies...
    pip install -r requirements.txt
    echo. > venv\installed
)

REM Create necessary directories
if not exist uploads mkdir uploads
if not exist outputs mkdir outputs

REM Start the application
echo.
echo Starting Medical PDF Converter...
echo URL: http://localhost:8501
echo.
echo Press Ctrl+C to stop
echo.

streamlit run app.py

pause
