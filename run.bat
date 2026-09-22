@echo off
setlocal

echo ========================================
echo Web3 Participation Prototype
echo ========================================
echo.

echo Installing dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo Dependency installation failed.
    pause
    exit /b 1
)

echo.
echo Generating 100 synthetic participants...
python src\seed_synthetic.py 100
if errorlevel 1 (
    echo.
    echo Synthetic data generation failed.
    pause
    exit /b 1
)

echo.
echo Starting Streamlit app...
start "Participation App" cmd /k "python -m streamlit run src\app.py"

echo Starting dashboard...
start "Participation Dashboard" cmd /k "python -m streamlit run src\dashboard.py"

echo.
echo Done.
pause
