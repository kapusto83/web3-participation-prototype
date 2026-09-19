@echo off
setlocal

cd /d "%~dp0"

echo ========================================
echo Web3 Participation Prototype
echo ========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed.
    echo Please install Python 3.14 or newer.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
)

echo Checking dependencies...
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt

if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo Starting application...
echo.

".venv\Scripts\python.exe" -m streamlit run src\app.py

pause